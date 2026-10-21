"""Bounded, serial, local-only capability checks for an OpenAI-compatible server.

This module does not convert PDFs and does not certify mathematical fidelity.
It never starts/stops a server, follows redirects, uses proxy environment
variables, retries requests, or invokes model tools. Raw attempt evidence stays
under the supplied output directory; Authorization values are never recorded.
"""

from __future__ import annotations

import base64
import hashlib
import http.client
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import socket
import ssl
import threading
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit
import uuid


MAX_REQUEST_BYTES = 2 * 1024 * 1024
MAX_IMAGE_BYTES = 1024 * 1024
MAX_IMAGE_PIXELS = 2_000_000
PAGE_REASONING_EFFORTS = ("server-default", "low", "medium", "high", "max")
_PNG = b"\x89PNG\r\n\x1a\n"


def validate_page_reasoning_effort(value):
    if not isinstance(value, str) or value not in PAGE_REASONING_EFFORTS:
        raise ValueError("Page reasoning effort must be server-default, low, medium, high or max.")
    return value


class ProbeError(RuntimeError):
    """A failed local request or a malformed model response."""

    def __init__(self, message, *, attempt_dir=None, status=None):
        super().__init__(message)
        self.attempt_dir = str(attempt_dir) if attempt_dir else None
        self.status = status


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json_dump(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("non-finite JSON number")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def parse_json_response(text):
    """Decode assistant JSON without repairing, stripping fences or duplicates.

    Callers must separately validate their operation-specific schema. Parsing
    success is a syntax result, not evidence of source or mathematical fidelity.
    """
    if not isinstance(text, str):
        raise TypeError("Assistant JSON content must be text.")
    return _strict_json(text)


def _allowed_ip(value):
    address = ipaddress.ip_address(value)
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    if address.is_loopback:
        return True
    networks = (
        ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
        if address.version == 4 else ("fc00::/7",)
    )
    return any(address in ipaddress.ip_network(network) for network in networks)


def validate_base_url(base_url):
    """Allow only RFC1918, loopback, IPv6 ULA literals, or localhost.

    Empty paths become /v1. Optional API prefixes use simple path segments.
    Link-local/unspecified/public addresses and hostname aliases are excluded.
    """
    if not isinstance(base_url, str) or not base_url or base_url != base_url.strip():
        raise ValueError("Provide a local HTTP(S) API base URL.")
    if any(ord(character) < 33 for character in base_url) or "\\" in base_url:
        raise ValueError("Whitespace/control characters and backslashes are forbidden in the URL.")
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except ValueError as error:
        raise ValueError("Invalid API base URL or port.") from error
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("The API base URL must use http or https.")
    if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
        raise ValueError("Credentials must not appear in the API URL.")
    if "?" in base_url or "#" in base_url:
        raise ValueError("API URL queries and fragments are forbidden.")
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("API port must be between 1 and 65535.")
    hostname = parsed.hostname
    if hostname != "localhost":
        try:
            allowed = "%" not in hostname and _allowed_ip(hostname)
        except ValueError:
            allowed = False
        if not allowed:
            raise ValueError("Use a private/local IP literal or localhost; public hosts are forbidden.")
    path = parsed.path.rstrip("/") or "/v1"
    if not re.fullmatch(r"(?:/[A-Za-z0-9_-]+)+", path):
        raise ValueError("The API path must contain only simple slash-separated path segments.")
    netloc = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        netloc += f":{port}"
    return urlunsplit((parsed.scheme, netloc, path, "", ""))


class _PinnedHTTPSConnection(http.client.HTTPConnection):
    """Connect to a validated numeric address but verify the original TLS name."""

    def __init__(self, connect_host, port, tls_name, timeout):
        super().__init__(connect_host, port, timeout=timeout)
        self._tls_name = tls_name

    def connect(self):
        super().connect()
        self.sock = ssl.create_default_context().wrap_socket(self.sock, server_hostname=self._tls_name)


class LocalClient:
    """Local-only HTTP client; LOCAL_MODEL_API_KEY is the optional key source.

    A caller may alternatively supply api_key explicitly after reading its own
    environment. Only one request per instance can run at a time. Timeout is a
    per-request wall-clock deadline (including response-body reading); there is
    no automatic retry. Capability/candidate probes cap output at 4096 tokens;
    explicit page_review purpose permits up to 16384 with the same transport limits.
    """

    def __init__(self, base_url, model=None, api_key=None, timeout=120,
                 max_tokens=2048, max_response_bytes=2 * 1024 * 1024, purpose="capability_probe"):
        self.base_url = validate_base_url(base_url)
        if model is not None and (not isinstance(model, str) or not model.strip() or len(model) > 512):
            raise ValueError("model must be a nonempty model ID, at most 512 characters.")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 600:
            raise ValueError("timeout must be between 0 and 600 seconds.")
        if purpose not in ("capability_probe", "page_review"):
            raise ValueError("Unknown local request purpose.")
        token_limit = 16384 if purpose == "page_review" else 4096
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or not 1 <= max_tokens <= token_limit:
            raise ValueError(f"max_tokens must be an integer between 1 and {token_limit}.")
        if isinstance(max_response_bytes, bool) or not isinstance(max_response_bytes, int) or not 1024 <= max_response_bytes <= 8 * 1024 * 1024:
            raise ValueError("max_response_bytes must be between 1024 and 8388608.")
        self.requested_model = model
        self.model = None
        self.timeout = float(timeout)
        self.max_tokens = max_tokens
        self.max_response_bytes = max_response_bytes
        self.purpose = purpose
        self._key = api_key if api_key is not None else os.environ.get("LOCAL_MODEL_API_KEY")
        if self._key is not None and (not isinstance(self._key, str) or any(c in self._key for c in "\r\n")):
            raise ValueError("The API key must be a single-line string.")
        self._lock = threading.Lock()

    def _redact(self, value):
        if self._key:
            if isinstance(value, bytes):
                return value.replace(self._key.encode("utf-8"), b"[REDACTED_API_KEY]")
            return str(value).replace(self._key, "[REDACTED_API_KEY]")
        return value

    def _connection(self):
        parsed = urlsplit(self.base_url)
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        hostname = parsed.hostname
        connect_host = hostname
        if hostname == "localhost":
            # Pin localhost without DNS/NSS resolution. Use [::1] explicitly
            # for an IPv6-only listener; arbitrary hostname aliases are banned.
            connect_host = "127.0.0.1"
        if parsed.scheme == "https":
            connection = _PinnedHTTPSConnection(connect_host, port, hostname, self.timeout)
        else:
            connection = http.client.HTTPConnection(connect_host, port, timeout=self.timeout)
        return connection, parsed

    def _request(self, method, endpoint, payload, output_dir, label):
        if (method, endpoint) not in (("GET", "/models"), ("POST", "/chat/completions")):
            raise ValueError("Only model discovery and chat completion endpoints are allowed.")
        body = None if payload is None else json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if body is not None and len(body) > MAX_REQUEST_BYTES:
            raise ProbeError("Request body exceeds the local probe limit.")
        with self._lock:
            attempts = Path(output_dir) / "attempts"
            attempts.mkdir(parents=True, exist_ok=True)
            safe_label = re.sub(r"[^A-Za-z0-9_-]", "_", label)[:60]
            attempt_dir = attempts / f"{time.time_ns()}_{safe_label}_{uuid.uuid4().hex[:8]}"
            attempt_dir.mkdir()
            headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "pdf2tex-local-probe/0.1"}
            if self._key:
                headers["Authorization"] = f"Bearer {self._key}"
            recorded_headers = {key: ("[REDACTED]" if key == "Authorization" else value) for key, value in headers.items()}
            request_record = {"method": method, "url": self.base_url + endpoint, "headers": recorded_headers, "body": payload}
            # Write before network dispatch, preserving evidence even on failure.
            (attempt_dir / "request.json").write_text(self._redact(json.dumps(request_record, indent=2, ensure_ascii=False)) + "\n", encoding="utf-8")
            record = {"started_at": _now(), "status": "running", "http_status": None, "label": label}
            _json_dump(attempt_dir / "record.json", record)
            start = time.monotonic()
            deadline = start + self.timeout
            connection = None
            deadline_timer = None
            raw = bytearray()
            status = None
            try:
                connection, parsed = self._connection()
                def expire_socket():
                    # A socket timeout alone resets on each received packet;
                    # this also bounds slow/trickled HTTP headers and bodies.
                    current_socket = connection.sock
                    if current_socket is not None:
                        try:
                            current_socket.shutdown(socket.SHUT_RDWR)
                        except OSError:
                            pass
                deadline_timer = threading.Timer(max(0.001, deadline - time.monotonic()), expire_socket)
                deadline_timer.daemon = True
                deadline_timer.start()
                connection.connect()

                def remaining():
                    seconds = deadline - time.monotonic()
                    if seconds <= 0:
                        raise TimeoutError("Local request deadline exceeded.")
                    if connection.sock is not None:
                        connection.sock.settimeout(seconds)

                remaining()
                # An explicit Host header retains localhost for HTTPS/name-based APIs.
                headers["Host"] = parsed.netloc
                connection.request(method, parsed.path + endpoint, body=body, headers=headers)
                remaining()
                response = connection.getresponse()
                status = response.status
                record["http_status"] = status
                record["response_headers"] = {key.lower(): self._redact(value) for key, value in response.getheaders() if key.lower() in ("content-type", "content-length", "x-request-id", "retry-after")}
                content_length = response.getheader("Content-Length")
                if content_length is not None:
                    try:
                        declared_length = int(content_length)
                    except ValueError as error:
                        raise ProbeError("Invalid response Content-Length.", status=status) from error
                    if declared_length < 0 or declared_length > self.max_response_bytes:
                        raise ProbeError("Response exceeds the configured byte limit.", status=status)
                while True:
                    remaining()
                    # read1 allows the deadline to be rechecked between socket reads.
                    part = response.read1(min(65536, self.max_response_bytes + 1 - len(raw)))
                    if not part:
                        break
                    raw.extend(part)
                    if len(raw) > self.max_response_bytes:
                        raise ProbeError("Response exceeds the configured byte limit.", status=status)
                if content_length is not None and len(raw) != int(content_length):
                    raise ProbeError("Incomplete HTTP response body.", status=status)
                if 300 <= status < 400:
                    raise ProbeError("Redirect refused; use the actual local API base URL.", status=status)
                if not 200 <= status < 300:
                    raise ProbeError(f"Local API returned HTTP {status}; see retained raw response.", status=status)
                try:
                    data = _strict_json(self._redact(bytes(raw)).decode("utf-8"))
                except (ValueError, UnicodeDecodeError) as error:
                    raise ProbeError("Local API response is not complete strict JSON.", status=status) from error
                if not isinstance(data, dict):
                    raise ProbeError("Local API response must be a JSON object.", status=status)
                record["status"] = "completed"
                return data, {"attempt_dir": str(attempt_dir), "http_status": status,
                              "started_at": record["started_at"], "latency_seconds": time.monotonic() - start}
            except Exception as error:
                record["status"] = "failed"
                message = self._redact(str(error))
                record["error"] = message
                if isinstance(error, ProbeError):
                    raise ProbeError(message, attempt_dir=attempt_dir, status=error.status or status) from error
                raise ProbeError(f"Local request failed: {message}", attempt_dir=attempt_dir, status=status) from error
            finally:
                if deadline_timer is not None:
                    deadline_timer.cancel()
                if connection is not None:
                    connection.close()
                (attempt_dir / "response.raw").write_bytes(self._redact(bytes(raw)))
                record["finished_at"] = _now()
                record["latency_seconds"] = time.monotonic() - start
                _json_dump(attempt_dir / "record.json", record)

    def discover_model(self, output_dir):
        """Return selected model and evidence; never guess between model IDs."""
        data, evidence = self._request("GET", "/models", None, output_dir, "models")
        entries = data.get("data")
        if not isinstance(entries, list):
            raise ProbeError("The /models response has no data list.", attempt_dir=evidence["attempt_dir"])
        ids = sorted(set(entry["id"] for entry in entries if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"] and len(entry["id"]) <= 512))
        if self.requested_model is not None:
            if self.requested_model not in ids:
                raise ProbeError("Configured model ID is not an exact match in /models.", attempt_dir=evidence["attempt_dir"])
            selected = self.requested_model
        else:
            glm = [model for model in ids if "glm" in model.lower()]
            if len(glm) == 1:
                selected = glm[0]
            else:
                raise ProbeError("GLM model selection is ambiguous or unavailable; confirm GLM 5.3 Flash is served and set its exact model ID explicitly.", attempt_dir=evidence["attempt_dir"])
        self.model = selected
        return {"status": "passed", "selected_model": selected, "available_models": ids, **evidence}

    def chat(self, messages, output_dir, label, response_format=None, *, reasoning_effort="server-default"):
        """Return content and non-reasoning metadata; raw response stays on disk."""
        validate_page_reasoning_effort(reasoning_effort)
        if reasoning_effort != "server-default" and self.purpose != "page_review":
            raise ValueError("Explicit reasoning effort is only supported for page review.")
        if not self.model:
            raise ProbeError("Discover/select the local model before requesting a completion.")
        payload = {"model": self.model, "messages": messages, "max_tokens": self.max_tokens, "stream": False}
        if response_format is not None:
            payload["response_format"] = response_format
        if reasoning_effort != "server-default":
            payload["reasoning_effort"] = reasoning_effort
        data, evidence = self._request("POST", "/chat/completions", payload, output_dir, label)
        attempt_dir = Path(evidence["attempt_dir"])
        try:
            choices = data.get("choices")
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise ValueError("Expected exactly one completion choice.")
            choice = choices[0]
            finish = choice.get("finish_reason")
            message = choice.get("message")
            if not isinstance(message, dict):
                raise ValueError("Missing assistant message.")
            if message.get("tool_calls") or message.get("function_call"):
                raise ValueError("Tool/function calls are not allowed in this probe.")
            if finish != "stop":
                raise ValueError("Completion did not finish normally (empty, truncated, filtered, or tool output).")
            content = message.get("content")
            if isinstance(content, list):
                if any(not isinstance(part, dict) or part.get("type") != "text" or not isinstance(part.get("text"), str) for part in content):
                    raise ValueError("Unsupported non-text assistant content.")
                content = "".join(part["text"] for part in content)
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Assistant content is empty; reasoning-only output does not pass.")
            actual_model = data.get("model")
            if not isinstance(actual_model, str) or not actual_model:
                raise ValueError("Response did not report the actual model ID.")
            usage = _numeric_usage(data.get("usage", {}))
            evidence.update({"actual_model": actual_model, "finish_reason": finish, "usage": usage})
            record = _strict_json((attempt_dir / "record.json").read_text(encoding="utf-8"))
            record.update({"actual_model": actual_model, "finish_reason": finish, "usage": usage, "completion_validation": "passed"})
            _json_dump(attempt_dir / "record.json", record)
            return {"content": content, **evidence}
        except (ValueError, TypeError) as error:
            record = _strict_json((attempt_dir / "record.json").read_text(encoding="utf-8"))
            record.update({"completion_validation": "failed", "validation_error": str(error),
                           "actual_model": data.get("model") if isinstance(data.get("model"), str) else None,
                           "finish_reason": (data.get("choices") or [{}])[0].get("finish_reason") if isinstance(data.get("choices"), list) and data["choices"] and isinstance(data["choices"][0], dict) else None,
                           "usage": _numeric_usage(data.get("usage", {}))})
            _json_dump(attempt_dir / "record.json", record)
            raise ProbeError(str(error), attempt_dir=attempt_dir, status=evidence["http_status"]) from error


def _numeric_usage(value, depth=0):
    if not isinstance(value, dict) or depth > 5:
        return {}
    result = {}
    for key, item in value.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_]{1,80}", key):
            continue
        if isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= 2**63 - 1:
            result[key] = item
        elif isinstance(item, float) and math.isfinite(item):
            result[key] = item
        elif isinstance(item, dict):
            result[key] = _numeric_usage(item, depth + 1)
    return result


def _evidence(result):
    return {key: value for key, value in result.items() if key != "content"}


def _require_model_identity(result, selected_model):
    """Fail this capability without discarding the reported response evidence."""
    if result.get("actual_model") != selected_model:
        result["status"] = "failed"
        result["reason"] = (f"Model identity mismatch: selected {selected_model!r}, "
                            f"response reported {result.get('actual_model')!r}; "
                            "this response cannot qualify the selected model.")
        result.pop("qualification", None)


def _failure(error, *, unsupported=False):
    return {"status": "unsupported" if unsupported and error.status in (400, 404, 415, 422) else "failed",
            "reason": str(error), "attempt_dir": error.attempt_dir, "http_status": error.status}


def _schema(name, field, enumeration=None):
    field_schema = {"type": "string"}
    if enumeration is not None:
        field_schema["enum"] = enumeration
    return {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": {
        "type": "object", "properties": {field: field_schema}, "required": [field], "additionalProperties": False}}}


def _read_vision_case(case):
    if not isinstance(case, dict):
        raise ValueError("Each vision case must be an object.")
    expected = case.get("expected")
    kind = case.get("kind")
    if not isinstance(case.get("case_id"), str) or not case["case_id"]:
        raise ValueError("Vision case needs a nonempty case_id.")
    if kind == "blank":
        if expected != "":
            raise ValueError("The blank control's expected value must be empty.")
    elif kind == "digits":
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9]{1,12}", expected):
            raise ValueError("Digit cases need 1–12 expected ASCII digits.")
    else:
        raise ValueError("Vision case kind must be digits or blank.")
    path = Path(case["image_path"])
    with path.open("rb") as source:
        raw = source.read(MAX_IMAGE_BYTES + 1)
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Vision image exceeds the one-megabyte probe limit.")
    if len(raw) < 33 or raw[:8] != _PNG or raw[12:16] != b"IHDR":
        raise ValueError("Vision cases must use PNG images.")
    width = int.from_bytes(raw[16:20], "big")
    height = int.from_bytes(raw[20:24], "big")
    if not width or not height or width * height > MAX_IMAGE_PIXELS:
        raise ValueError("Vision PNG dimensions exceed the probe limit.")
    return raw, hashlib.sha256(raw).hexdigest()


def probe_model(client, output_dir, vision_cases=None):
    """Run discovery, text, strict-JSON and optional controlled image checks.

    vision_cases is a sequence of dictionaries with case_id, image_path,
    expected, and kind ('digits' or 'blank'). Use generated random digits that
    occur only in the pixels, not in filenames/prompts visible to the model.
    Qualification needs >=2 different digit cases, a blank, distinct image
    hashes and IDs, and every exact response. Each capability also requires an
    exact response model ID match. Failures do not erase unrelated success.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "capabilities.json"
    report = {"schema_version": "0.1", "started_at": _now(), "endpoint": client.base_url,
              "requested_model": client.requested_model, "selected_model": None,
              "scope": "local_endpoint_capability_probe_only", "local_only": True,
              "notice": "These tiny checks do not certify PDF transcription, mathematical fidelity, model weights, context capacity, or server implementation.",
              "model_discovery": {"status": "not_run"}, "text": {"status": "not_run"},
              "strict_json": {"status": "not_run"}, "vision": {"status": "not_tested", "cases": []}}

    def save():
        _json_dump(report_path, report)

    save()
    try:
        report["model_discovery"] = client.discover_model(output)
        report["selected_model"] = client.model
    except ProbeError as error:
        report["model_discovery"] = _failure(error)
        report["finished_at"] = _now()
        save()
        return report
    save()
    try:
        result = client.chat([{"role": "user", "content": "Reply with exactly LOCAL_OK and nothing else."}], output, "text")
        report["text"] = {"status": "passed" if result["content"].strip() == "LOCAL_OK" else "failed", **_evidence(result)}
        if report["text"]["status"] != "passed":
            report["text"]["reason"] = "Assistant content did not exactly match the sentinel."
        _require_model_identity(report["text"], report["selected_model"])
    except ProbeError as error:
        report["text"] = _failure(error)
    save()
    try:
        result = client.chat([{"role": "user", "content": 'Return exactly the JSON object {"probe":"LOCAL_OK"}. No markdown or other text.'}], output, "strict_json", _schema("local_probe", "probe", ["LOCAL_OK"]))
        try:
            passed = _strict_json(result["content"]) == {"probe": "LOCAL_OK"}
        except ValueError:
            passed = False
        report["strict_json"] = {"status": "passed" if passed else "failed", **_evidence(result),
                                 "qualification": "One strict-schema request was accepted and its result validated; schema enforcement on all future outputs is not proven."}
        if not passed:
            report["strict_json"]["reason"] = "Assistant content was not exactly the required JSON object."
        _require_model_identity(report["strict_json"], report["selected_model"])
    except ProbeError as error:
        report["strict_json"] = _failure(error, unsupported=True)
    save()

    cases = list(vision_cases or [])
    if cases:
        prepared = []
        for index, case in enumerate(cases):
            try:
                raw, digest = _read_vision_case(case)
                prepared.append((case, raw, digest))
            except (ValueError, KeyError, TypeError, OSError) as error:
                report["vision"]["cases"].append({"case_id": case.get("case_id", f"invalid_{index}") if isinstance(case, dict) else f"invalid_{index}", "status": "failed", "reason": str(error)})
        for case, raw, digest in prepared:
            entry = {"case_id": case["case_id"], "kind": case["kind"], "image_sha256": digest}
            messages = [{"role": "user", "content": [
                {"type": "text", "text": 'Read only the ASCII digits visible in the attached image, in order. Return exactly one JSON object with a string field "digits". If no digits are visible, use an empty string. Do not guess. No markdown or explanation.'},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(raw).decode("ascii")}},
            ]}]
            try:
                result = client.chat(messages, output, f"vision_{case['case_id']}")
                entry.update(_evidence(result))
                try:
                    value = _strict_json(result["content"])
                    exact = isinstance(value, dict) and set(value) == {"digits"} and value["digits"] == case["expected"]
                except ValueError:
                    exact = False
                entry["status"] = "passed" if exact else "failed"
                if not exact:
                    entry["reason"] = "Vision response did not exactly match this image/control."
                _require_model_identity(entry, report["selected_model"])
            except ProbeError as error:
                entry.update(_failure(error, unsupported=True))
            report["vision"]["cases"].append(entry)
            save()
        digit_values = {case["expected"] for case, _, _ in prepared if case["kind"] == "digits"}
        has_blank = any(case["kind"] == "blank" for case, _, _ in prepared)
        controls_ok = (len(digit_values) >= 2 and has_blank and len({digest for _, _, digest in prepared}) == len(prepared)
                       and len({case["case_id"] for case, _, _ in prepared}) == len(prepared))
        results = report["vision"]["cases"]
        if not controls_ok:
            report["vision"]["status"] = "failed"
            report["vision"]["reason"] = "Qualification requires at least two different digit images and a blank, with unique image hashes and case IDs."
        elif results and all(case["status"] == "passed" for case in results):
            report["vision"]["status"] = "qualified"
            report["vision"]["qualification"] = "Simple digit/control image input only; mathematical OCR remains unqualified."
        else:
            report["vision"]["status"] = "unsupported" if results and all(case["status"] == "unsupported" for case in results) else "failed"
            report["vision"]["reason"] = "At least one image/control failed; do not rely on this endpoint for visual transcription."
    report["finished_at"] = _now()
    save()
    return report
