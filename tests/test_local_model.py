"""Offline local-client tests; all HTTP traffic stays on a loopback mock server."""

import base64
import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import zlib

from probe.local_model import LocalClient, ProbeError, parse_json_response, probe_model, validate_base_url


def completion(content, *, finish="stop", model="actual-model", **message_extra):
    return {"model": model, "choices": [{"finish_reason": finish, "message": {"role": "assistant", "content": content, **message_extra}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2, "completion_tokens_details": {"reasoning_tokens": 1}}}


def png(value):
    """A valid 2x1 RGB PNG, distinct for every fixture value."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 1, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0" + bytes([value, value, value, 255, 255, 255]))) + chunk(b"IEND", b""))


class MockServer:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.handle_request()

            def do_POST(self):
                self.handle_request()

            def handle_request(self):
                body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
                owner.requests.append({"path": self.path, "body": json.loads(body) if body else None, "authorization": self.headers.get("Authorization")})
                reply = owner.replies.pop(0) if owner.replies else (500, b"unexpected request", {})
                if callable(reply):
                    reply = reply(owner.requests[-1])
                status, payload, headers = reply
                if isinstance(payload, dict):
                    payload = json.dumps(payload).encode()
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, str(value))
                if "Content-Length" not in headers:
                    self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                try:
                    self.wfile.write(payload)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"

    def __enter__(self):
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


def models(*ids):
    return 200, {"data": [{"id": value} for value in ids]}, {}


def reply(content, **kwargs):
    return 200, completion(content, **kwargs), {}


class LocalModelTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_endpoint_whitelist_and_normalization(self):
        for value in ("http://127.0.0.1:8888/v1", "http://192.168.1.100:8888/v1", "https://10.0.0.1/v1", "http://172.16.0.1/v1", "http://localhost/v1", "http://[::1]/v1", "http://[fd00::1]/v1"):
            self.assertEqual(validate_base_url(value), value)
        self.assertEqual(validate_base_url("http://127.0.0.1/"), "http://127.0.0.1/v1")
        for value in ("https://openrouter.ai/api/v1", "http://8.8.8.8/v1", "http://example.local/v1", "http://0.0.0.0/v1", "http://169.254.169.254/v1", "http://172.32.0.1/v1", "http://user:key@127.0.0.1/v1", "http://127.0.0.1/v1?key=x", "http://127.0.0.1/v1?", "http://127.0.0.1/v1#x", "http://127.0.0.1/%2e%2e/v1", "http://127.0.0.1/../v1", "http://2130706433/v1", "ftp://127.0.0.1/v1", "http://127.0.0.1:0/v1", "http://127.0.0.1\\@8.8.8.8/v1", "http://localhost./v1", " http://127.0.0.1/v1", "http://127.0.0.1/\nv1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_base_url(value)

    def test_limits_rejected_before_network(self):
        for options in ({"max_tokens": 4097}, {"max_tokens": True}, {"timeout": 0}, {"timeout": float("nan")}, {"max_response_bytes": 100}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                LocalClient("http://127.0.0.1/v1", **options)

    def test_model_selection_ambiguous_and_exact(self):
        with MockServer([models("glm53-fast", "glm53-regular"), models("glm53-fast", "glm53-regular")]) as server:
            client = LocalClient(server.url)
            with self.assertRaisesRegex(ProbeError, "ambiguous"):
                client.discover_model(self.directory)
            client = LocalClient(server.url, model="glm53-regular")
            self.assertEqual(client.discover_model(self.directory)["selected_model"], "glm53-regular")

    def test_model_selection_prefers_single_glm_and_no_fuzzy_match(self):
        with MockServer([models("another-model", "glm53"), models("glm53"), models("another-model")]) as server:
            self.assertEqual(LocalClient(server.url).discover_model(self.directory)["selected_model"], "glm53")
            with self.assertRaisesRegex(ProbeError, "exact match"):
                LocalClient(server.url, model="glm").discover_model(self.directory)
            with self.assertRaisesRegex(ProbeError, "GLM model selection"):
                LocalClient(server.url).discover_model(self.directory)

    def test_redirect_is_not_followed(self):
        with MockServer([(302, b"", {"Location": "https://openrouter.ai/api/v1/models"})]) as server:
            with self.assertRaisesRegex(ProbeError, "Redirect refused"):
                LocalClient(server.url).discover_model(self.directory)
            self.assertEqual(len(server.requests), 1)
        self.assertTrue(next((self.directory / "attempts").iterdir()).joinpath("request.json").exists())

    def test_proxy_environment_is_ignored_and_key_not_saved(self):
        key = "test-key-must-never-appear-in-files"
        with MockServer([models("glm53"), reply("LOCAL_OK", reasoning_content="private reasoning example")]) as server:
            with patch.dict(os.environ, {"HTTP_PROXY": "http://8.8.8.8:9999", "HTTPS_PROXY": "http://8.8.8.8:9999", "ALL_PROXY": "http://8.8.8.8:9999", "LOCAL_MODEL_API_KEY": key}):
                client = LocalClient(server.url)
                client.discover_model(self.directory)
                result = client.chat([{"role": "user", "content": "test"}], self.directory, "test")
            self.assertEqual(server.requests[0]["authorization"], f"Bearer {key}")
            self.assertNotIn("reasoning_content", result)
            self.assertEqual(result["actual_model"], "actual-model")
            for path in self.directory.rglob("*"):
                if path.is_file():
                    self.assertNotIn(key.encode(), path.read_bytes())
                    if path.name != "response.raw":
                        self.assertNotIn(b"private reasoning example", path.read_bytes())

    def test_truncated_json_is_retained_and_rejected(self):
        with MockServer([(200, b'{"data":[', {})]) as server:
            with self.assertRaisesRegex(ProbeError, "strict JSON"):
                LocalClient(server.url).discover_model(self.directory)
        self.assertEqual(next(self.directory.rglob("response.raw")).read_bytes(), b'{"data":[')

    def test_reflected_api_key_is_redacted_in_raw_and_report(self):
        key = "secret-that-a-broken-server-reflects"
        with MockServer([models("glm53"), reply("LOCAL_OK", model=key, reasoning_content=key), reply('{"probe":"LOCAL_OK"}', model=key)]) as server:
            report = probe_model(LocalClient(server.url, api_key=key), self.directory)
            self.assertEqual(report["text"]["actual_model"], "[REDACTED_API_KEY]")
            for path in self.directory.rglob("*"):
                if path.is_file():
                    self.assertNotIn(key.encode(), path.read_bytes())

    def test_incomplete_http_body_and_oversize_are_rejected(self):
        with MockServer([(200, b'{"data":[]}', {"Content-Length": 30}), (200, b"", {"Content-Length": 2000})]) as server:
            with self.assertRaisesRegex(ProbeError, "Incomplete HTTP"):
                LocalClient(server.url).discover_model(self.directory)
            with self.assertRaisesRegex(ProbeError, "byte limit"):
                LocalClient(server.url, max_response_bytes=1024).discover_model(self.directory)

    def test_length_reasoning_only_and_tool_calls_are_rejected(self):
        responses = [models("glm53"), reply("LOCAL_OK", finish="length"), reply(None, reasoning_content="LOCAL_OK"), reply("LOCAL_OK", tool_calls=[{"id": "bad"}])]
        with MockServer(responses) as server:
            client = LocalClient(server.url)
            client.discover_model(self.directory)
            for _ in range(3):
                with self.assertRaises(ProbeError):
                    client.chat([{"role": "user", "content": "test"}], self.directory, "bad")
            self.assertEqual(len(server.requests), 4)

    def vision_cases(self):
        result = []
        for index, (kind, expected) in enumerate((("digits", "451932"), ("digits", "702586"), ("blank", ""))):
            path = self.directory / f"case_{index}.png"
            path.write_bytes(png(index))
            result.append({"case_id": f"case_{index}", "image_path": str(path), "expected": expected, "kind": kind})
        return result

    def test_successful_vision_control_probe_and_request_bounds(self):
        cases = self.vision_cases()
        responses = [models("glm53"), reply("LOCAL_OK"), reply('{"probe":"LOCAL_OK"}')]
        responses += [reply(json.dumps({"digits": case["expected"]})) for case in cases]
        with MockServer(responses) as server:
            report = probe_model(LocalClient(server.url, max_tokens=333), self.directory / "result", cases)
            self.assertEqual(report["text"]["status"], "passed")
            self.assertEqual(report["strict_json"]["status"], "passed")
            self.assertEqual(report["vision"]["status"], "qualified")
            for request in server.requests[1:]:
                self.assertEqual(request["body"]["max_tokens"], 333)
                self.assertFalse(request["body"]["stream"])
                self.assertNotIn("tools", request["body"])
            for request, case in zip(server.requests[3:], cases):
                content = request["body"]["messages"][0]["content"]
                self.assertNotIn(case["expected"], content[0]["text"]) if case["expected"] else None
                self.assertEqual(base64.b64decode(content[1]["image_url"]["url"].split(",", 1)[1]), Path(case["image_path"]).read_bytes())
            self.assertEqual(len(server.requests), 6)
        self.assertTrue((self.directory / "result" / "capabilities.json").exists())

    def test_vision_mismatch_does_not_erase_text_success(self):
        cases = self.vision_cases()
        responses = [models("glm53"), reply("LOCAL_OK"), reply('{"probe":"LOCAL_OK"}'), reply('{"digits":"451932"}'), reply('{"digits":"WRONG"}'), reply('{"digits":""}')]
        with MockServer(responses) as server:
            report = probe_model(LocalClient(server.url), self.directory / "result", cases)
            self.assertEqual(report["text"]["status"], "passed")
            self.assertEqual(report["vision"]["status"], "failed")
            self.assertEqual(report["vision"]["cases"][1]["status"], "failed")

    def test_unsupported_json_and_vision_are_recorded(self):
        cases = self.vision_cases()
        responses = [models("glm53"), reply("LOCAL_OK"), (400, {"error": "unsupported schema"}, {})]
        responses += [(415, {"error": "unsupported image"}, {}) for _ in cases]
        with MockServer(responses) as server:
            report = probe_model(LocalClient(server.url), self.directory / "result", cases)
            self.assertEqual(report["text"]["status"], "passed")
            self.assertEqual(report["strict_json"]["status"], "unsupported")
            self.assertEqual(report["vision"]["status"], "unsupported")

    def test_duplicate_json_keys_and_missing_control_do_not_qualify(self):
        cases = self.vision_cases()[:1]
        responses = [models("glm53"), reply("LOCAL_OK"), reply('{"probe":"BAD","probe":"LOCAL_OK"}'), reply('{"digits":"451932"}')]
        with MockServer(responses) as server:
            report = probe_model(LocalClient(server.url), self.directory / "result", cases)
            self.assertEqual(report["strict_json"]["status"], "failed")
            self.assertEqual(report["vision"]["status"], "failed")

    def test_timeout_has_no_retry(self):
        def delayed(_):
            time.sleep(0.15)
            return models("glm53")
        with MockServer([delayed]) as server:
            with self.assertRaises(ProbeError):
                LocalClient(server.url, timeout=0.05).discover_model(self.directory)
            self.assertEqual(len(server.requests), 1)

    def test_public_json_parser_rejects_non_strict_response(self):
        self.assertEqual(parse_json_response('{"x":1}'), {"x": 1})
        for text in ('{"x":1,"x":2}', '{"x":NaN}', '```json\n{"x":1}\n```', '{"x":1} trailing'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_json_response(text)

    def test_cli_preflight_with_mock_server_and_portable_fixture_manifest(self):
        from probe import cli
        fixtures = self.directory / "fixtures" / "vision"
        fixtures.mkdir(parents=True)
        cases = self.vision_cases()
        for case in cases:
            actual = fixtures / Path(case["image_path"]).name
            actual.write_bytes(Path(case["image_path"]).read_bytes())
            case["sha256"] = hashlib.sha256(actual.read_bytes()).hexdigest()
            # Distribution manifests must work after the directory is moved.
            case["image_path"] = "/old/build/location/" + actual.name
        (fixtures / "manifest.json").write_text(json.dumps({"cases": cases}), encoding="utf-8")
        source_records = {}
        for source_id in ("paper", "book"):
            source_path = self.directory / f"{source_id}.pdf"
            source_path.write_bytes(f"mock hash-only preflight input: {source_id}".encode())
            source_records[source_id] = {"pdf": source_path.name, "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest()}
        (self.directory / "sources.json").write_text(json.dumps(source_records), encoding="utf-8")
        responses = [models("glm53"), reply("LOCAL_OK"), reply('{"probe":"LOCAL_OK"}')]
        responses += [reply(json.dumps({"digits": case["expected"]})) for case in cases]
        with MockServer(responses) as server:
            config = {"local_only": True, "base_url": server.url, "model": None,
                      "peer_ssh_alias": None, "request_timeout_seconds": 2, "max_output_tokens": 333}
            (self.directory / "config.example.json").write_text(json.dumps(config), encoding="utf-8")
            args = argparse.Namespace(config=None, peer=None, base_url=None, model=None)
            namespace_result = type("Completed", (), {"returncode": 0, "stderr": ""})()
            with patch.object(cli, "ROOT", self.directory), patch.object(cli, "inventory", return_value={"scope": "mock"}), patch.object(cli.subprocess, "run", return_value=namespace_result), contextlib.redirect_stdout(io.StringIO()):
                exit_code = cli.cmd_preflight(args)
            self.assertEqual(exit_code, 0)
            capabilities_path = next((self.directory / "runs").glob("preflight-*/model/capabilities.json"))
            capabilities = json.loads(capabilities_path.read_text())
            self.assertEqual(capabilities["endpoint"], server.url)
            self.assertEqual(capabilities["vision"]["status"], "qualified")
            self.assertEqual(capabilities["text"]["status"], "passed")
            self.assertEqual(len(server.requests), 6)
            self.assertEqual(len(list((self.directory / "results").glob("*-upload.zip"))), 1)

    def test_cli_review_text_only_proposal_does_not_change_source(self):
        from probe import cli
        source_run = self.directory / "source-run"
        attempt = source_run / "attempts" / "paper-unit"
        output = attempt / "output"
        output.mkdir(parents=True)
        (attempt / "input.pdf").write_bytes(b"mock-source-bytes-not-opened-in-text-only-review")
        (output / "document.tex").write_text("original-source-mathematics", encoding="utf-8")
        (attempt / "page-map.json").write_text(json.dumps([{"owner": True, "original_physical_page": 3}]), encoding="utf-8")
        candidate = {"id": "eq-1", "page_idx": 0, "kind": "equation", "text": "x=1", "text_truncated": False}
        (output / "review_candidates.json").write_text(json.dumps([candidate]), encoding="utf-8")
        record = {"status": "completed", "source_id": "paper", "attempt": "attempts/paper-unit",
                  "files": cli.files_manifest(output),
                  "evidence_files": [{"path": name, "sha256": hashlib.sha256((attempt / name).read_bytes()).hexdigest()}
                                     for name in ("input.pdf", "page-map.json")]}
        state = {"settings": {"sources": {"paper": {}}}, "units": {"paper-1": record}}
        (source_run / "state.json").write_text(json.dumps(state), encoding="utf-8")
        preflight = self.directory / "preflight"
        (preflight / "model").mkdir(parents=True)
        responses = [models("glm53"), reply('{"proposed_latex":"x=2","issues":["unverified suggestion"],"uncertain":false}')]
        with MockServer(responses) as server:
            caps = {"endpoint": server.url, "model_discovery": {"selected_model": "glm53"}, "text": {"status": "passed"}, "strict_json": {"status": "passed"}, "vision": {"status": "failed"}}
            (preflight / "model" / "capabilities.json").write_text(json.dumps(caps), encoding="utf-8")
            config = {"local_only": True, "base_url": server.url, "model": None,
                      "request_timeout_seconds": 2, "max_output_tokens": 333, "max_review_candidates": 2}
            (self.directory / "config.example.json").write_text(json.dumps(config), encoding="utf-8")
            args = argparse.Namespace(config=None, run=str(source_run), preflight=str(preflight))
            with patch.object(cli, "ROOT", self.directory), contextlib.redirect_stdout(io.StringIO()):
                exit_code = cli.cmd_review(args)
            self.assertEqual(exit_code, 0)
            proposal_path = next((self.directory / "runs").glob("review-*/proposals.json"))
            proposals = json.loads(proposal_path.read_text())
            self.assertEqual(proposals[0]["status"], "proposal_unaccepted")
            self.assertTrue(proposals[0]["proposal"]["uncertain"])
            self.assertEqual((output / "document.tex").read_text(), "original-source-mathematics")
            summary = json.loads((proposal_path.parent / "summary.json").read_text())
            self.assertEqual(summary["automatically_accepted"], 0)
            self.assertEqual(summary["mathematical_vision"], "unqualified")
            self.assertNotIn("image_url", json.dumps(server.requests[1]["body"]))


if __name__ == "__main__":
    unittest.main()
