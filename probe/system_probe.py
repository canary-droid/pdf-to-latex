"""Read-only host inventory and resource observations; no service control.

Only fixed diagnostic commands run here. No model packages are imported, packages
installed, environment variables enumerated, or full process arguments collected.
Resource observations are evidence for a caller's policy, not an automatic kill
or dispatch mechanism. GPU counters may be unavailable on unified-memory GB10.
"""

from __future__ import annotations

import csv
import importlib.metadata
import io
import json
import math
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import resource
except ImportError:  # Metadata-only operation can still run on non-Unix hosts.
    resource = None


GPU_FIELDS = (
    "index", "uuid", "name", "driver_version", "memory.total", "memory.used",
    "memory.free", "temperature.gpu", "utilization.gpu", "power.draw",
)
PROCESS_FIELDS = ("gpu_uuid", "pid", "process_name", "used_gpu_memory")
CLI_NAMES = (
    "python3", "nvidia-smi", "mineru", "mineru-kit", "pdfinfo", "pdftotext",
    "pdftoppm", "mutool", "latexmk", "pdflatex", "xelatex", "lualatex", "ssh",
)
DEPENDENCIES = {
    "mineru": "mineru", "torch": "torch", "onnxruntime": "onnxruntime",
    "onnxruntime-gpu": "onnxruntime-gpu", "fitz": "PyMuPDF", "pypdf": "pypdf",
    "pillow": "Pillow", "transformers": "transformers",
}
MEMORY_KEYS = ("MemTotal", "MemAvailable", "MemFree", "SwapTotal", "SwapFree")
_OUTPUT_LIMIT = 32768


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def parse_meminfo(text):
    """Parse Linux meminfo into integer bytes; unknown/malformed units are omitted.

    Linux labels binary KiB as 'kB'. Unitless counters (e.g. HugePages_Total)
    are deliberately omitted rather than falsely labelled as memory bytes.
    """
    result = {}
    for line in (text or "").splitlines():
        match = re.fullmatch(r"([A-Za-z_][A-Za-z_0-9]*):\s*(\d+)\s+kB\s*", line)
        if match:
            result[match.group(1)] = int(match.group(2)) * 1024
    return result


def memory_inventory():
    raw = _read_text("/proc/meminfo")
    parsed = parse_meminfo(raw)
    data = {key + "_bytes": parsed.get(key) for key in MEMORY_KEYS}
    total, free = data["SwapTotal_bytes"], data["SwapFree_bytes"]
    data["SwapUsed_bytes"] = total - free if total is not None and free is not None else None
    data["source"] = "/proc/meminfo"
    data["status"] = "ok" if data["MemAvailable_bytes"] is not None else "unavailable"
    return data


def validate_minimum_available_bytes(value):
    """Accept an explicit nonnegative integer byte threshold, or None (disabled)."""
    if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
        raise ValueError("minimum_available_bytes must be a nonnegative integer or None")
    return value


def memory_policy(memory, minimum_available_bytes=None):
    minimum = validate_minimum_available_bytes(minimum_available_bytes)
    available = memory.get("MemAvailable_bytes")
    if minimum is None:
        status = "disabled"
    elif available is None:
        status = "unavailable"
    else:
        status = "below_minimum" if available < minimum else "meets_minimum"
    return {"status": status, "minimum_available_bytes": minimum,
            "available_bytes": available, "below_minimum":
            (available < minimum) if minimum is not None and available is not None else None}


def _decode(value):
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return (value or "")[:_OUTPUT_LIMIT]


def _run_diagnostic(command, timeout=5):
    # Private helper: all call sites below construct fixed commands, with only a
    # strictly validated explicit SSH alias as user-controlled command input.
    started = time.monotonic()
    try:
        proc = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=timeout, check=False, shell=False)
        result = {"status": "ok" if proc.returncode == 0 else "error",
                  "returncode": proc.returncode, "stdout": _decode(proc.stdout),
                  "stderr": _decode(proc.stderr),
                  "output_truncated": len(proc.stdout or "") > _OUTPUT_LIMIT
                                      or len(proc.stderr or "") > _OUTPUT_LIMIT}
    except subprocess.TimeoutExpired as exc:
        result = {"status": "timeout", "returncode": None, "stdout": _decode(exc.stdout),
                  "stderr": _decode(exc.stderr), "timeout_seconds": timeout}
    except OSError as exc:
        result = {"status": "unavailable", "returncode": None, "stdout": "",
                  "stderr": str(exc)}
    result["elapsed_seconds"] = round(time.monotonic() - started, 4)
    return result


def _csv_records(text, fields):
    """Keep N/A/[Not Supported] literally; no false zero-valued GPU counters."""
    records = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) == len(fields):
            records.append(dict(zip(fields, (value.strip() for value in row))))
    return records


def gpu_inventory(include_processes=True, timeout=5):
    executable = shutil.which("nvidia-smi")
    if not executable:
        return {"status": "unavailable", "reason": "nvidia-smi not on PATH"}
    metrics = _run_diagnostic(
        [executable, "--query-gpu=" + ",".join(GPU_FIELDS), "--format=csv,noheader,nounits"], timeout)
    metrics["records"] = _csv_records(metrics["stdout"], GPU_FIELDS) if metrics["status"] == "ok" else []
    result = {"status": metrics["status"], "metrics": metrics,
              "units": {"memory": "MiB", "temperature": "Celsius", "utilization": "percent", "power": "watts"}}
    if include_processes:
        processes = _run_diagnostic(
            [executable, "--query-compute-apps=" + ",".join(PROCESS_FIELDS),
             "--format=csv,noheader,nounits"], timeout)
        processes["records"] = (_csv_records(processes["stdout"], PROCESS_FIELDS)
                                if processes["status"] == "ok" else [])
        result["compute_processes"] = processes
    return result


def process_memory():
    parsed = parse_meminfo(_read_text("/proc/self/status"))
    peak = None
    if resource is not None:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        peak = int(usage.ru_maxrss) * (1 if platform.system() == "Darwin" else 1024)
    return {"pid": os.getpid(), "rss_bytes": parsed.get("VmRSS"),
            "process_lifetime_peak_rss_bytes": peak,
            "scope": "root Python process only; child/converter/GPU allocations excluded"}


def _os_release():
    selected = {}
    allowed = {"ID", "NAME", "VERSION", "VERSION_ID", "VERSION_CODENAME", "PRETTY_NAME"}
    for line in (_read_text("/etc/os-release") or "").splitlines():
        key, separator, value = line.partition("=")
        if separator and key in allowed:
            selected[key] = value.strip().strip('"')
    return selected


def inventory(path="."):
    """Inventory this host and filesystem only; dependency metadata is not readiness."""
    selected_path = str(Path(path).resolve())
    try:
        disk = dict(zip(("total_bytes", "used_bytes", "free_bytes"), shutil.disk_usage(selected_path)))
        disk.update({"status": "ok", "path": selected_path})
    except OSError as exc:
        disk = {"status": "unavailable", "path": selected_path, "error": str(exc)}
    dependencies = {}
    for name, distribution in DEPENDENCIES.items():
        try:
            version = importlib.metadata.version(distribution)
            dependencies[name] = {"distribution": distribution, "version": version, "status": "installed"}
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = {"distribution": distribution, "version": None, "status": "not_found"}
    cpu_names = []
    for line in (_read_text("/proc/cpuinfo") or "").splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() in {"model name", "Hardware", "Processor"}:
            value = value.strip()
            if value and value not in cpu_names:
                cpu_names.append(value)
    try:
        affinity_count = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        affinity_count = None
    return {
        "schema_version": 1, "observed_at_utc": _utc_now(), "hostname": socket.gethostname(),
        "architecture": platform.machine(), "os": {"system": platform.system(),
        "kernel": platform.release(), "release": _os_release()},
        "python": {"version": platform.python_version(), "implementation": platform.python_implementation()},
        "cpu": {"logical_count": os.cpu_count(), "affinity_count": affinity_count, "models": cpu_names},
        "disk": disk, "memory": memory_inventory(), "process_memory": process_memory(),
        "gpu": gpu_inventory(), "dependencies": dependencies,
        "cli_paths": {name: shutil.which(name) for name in CLI_NAMES},
        "limitations": ["Package metadata and CLI presence do not prove ARM64/GB10 compatibility or GPU execution.",
                        "Unified-memory GPU counters may be unsupported; MemAvailable is sampled separately.",
                        "No environment variables, process command lines, Docker socket, or service mutations are used."],
    }


def validate_ssh_alias(alias):
    """Only a simple, explicitly supplied SSH config alias; no user@host or options."""
    if not isinstance(alias, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,252}", alias):
        raise ValueError("SSH alias must be 1-253 letters/digits/dots/underscores/hyphens, starting with a letter or digit")
    return alias


# Fixed remote program: no uploaded package, imports of ML runtimes, privileged
# operations, arbitrary remote commands, or modifications of remote files.
_REMOTE_SCRIPT = r'''
import datetime, json, os, platform, shutil, socket, subprocess
from pathlib import Path
def read(path):
    try: return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError: return None
def query(option):
    exe = shutil.which("nvidia-smi")
    if not exe: return {"status": "unavailable", "stdout": "", "stderr": "nvidia-smi not on PATH"}
    try:
        p = subprocess.run([exe, option, "--format=csv,noheader,nounits"], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=5, check=False)
        return {"status": "ok" if p.returncode == 0 else "error", "returncode": p.returncode, "stdout": p.stdout[:32768], "stderr": p.stderr[:32768]}
    except subprocess.TimeoutExpired: return {"status": "timeout", "timeout_seconds": 5}
    except OSError as e: return {"status": "unavailable", "stderr": str(e)}
print(json.dumps({"observed_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "hostname": socket.gethostname(), "architecture": platform.machine(), "system": platform.system(), "kernel": platform.release(), "python_version": platform.python_version(), "logical_cpu_count": os.cpu_count(), "meminfo": read("/proc/meminfo"), "gpu": query("--query-gpu=index,uuid,name,driver_version,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,power.draw"), "compute_processes": query("--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory")}))
'''.strip()


def remote_inventory(alias):
    """Explicit optional SSH probe. Never enabled by default or by guessing an alias.

    Requires an existing trusted host key and noninteractive authentication. SSH
    multiplexing, local hooks, forwarding and known-host updates are disabled.
    Existing SSH config can still select the connection route (e.g. ProxyJump).
    """
    alias = validate_ssh_alias(alias)
    executable = shutil.which("ssh")
    if not executable:
        return {"status": "unavailable", "ssh_alias": alias, "reason": "ssh not on PATH"}
    command = [executable, "-oBatchMode=yes", "-oConnectTimeout=8", "-oStrictHostKeyChecking=yes",
               "-oUpdateHostKeys=no", "-oControlMaster=no", "-oControlPath=none",
               "-oClearAllForwardings=yes", "-oPermitLocalCommand=no", "-oRequestTTY=no",
               "--", alias, "python3", "-c", shlex.quote(_REMOTE_SCRIPT)]
    transport = _run_diagnostic(command, timeout=25)
    result = {"status": transport["status"], "ssh_alias": alias, "transport": transport}
    if transport["status"] == "ok":
        try:
            data = json.loads(transport["stdout"])
            if not isinstance(data, dict):
                raise ValueError("Remote inventory was not a JSON object")
            mem = parse_meminfo(data.pop("meminfo", None))
            data["memory"] = {key + "_bytes": mem.get(key) for key in MEMORY_KEYS}
            for key, fields in (("gpu", GPU_FIELDS), ("compute_processes", PROCESS_FIELDS)):
                query = data.get(key, {})
                query["records"] = _csv_records(query.get("stdout", ""), fields) if query.get("status") == "ok" else []
            result["inventory"] = data
        except (ValueError, TypeError, AttributeError) as exc:
            result.update({"status": "invalid_response", "error": str(exc)})
    return result


def resource_sample(minimum_available_bytes=None, include_gpu=True):
    memory = memory_inventory()
    return {"observed_at_utc": _utc_now(), "memory": memory,
            "memory_policy": memory_policy(memory, minimum_available_bytes),
            "process_memory": process_memory(),
            "gpu": gpu_inventory(include_processes=False, timeout=3) if include_gpu else {"status": "not_sampled"}}


class ResourceMonitor:
    """Context manager recording resources approximately every two seconds.

    A sample may take longer if a diagnostic times out. Threshold crossings are
    recorded, never acted upon; the caller must check them before dispatch. RSS
    is for this Python process, not converter children. Sampling can miss peaks.
    """

    def __init__(self, interval_seconds=2.0, minimum_available_bytes=None, include_gpu=True):
        if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, (int, float)) or not math.isfinite(interval_seconds) or interval_seconds <= 0:
            raise ValueError("interval_seconds must be a finite positive number")
        self.interval_seconds = float(interval_seconds)
        self.minimum_available_bytes = validate_minimum_available_bytes(minimum_available_bytes)
        self.include_gpu = bool(include_gpu)
        self._samples = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._started = None
        self._ended = None
        self._final_process_memory = None

    @property
    def samples(self):
        # JSON roundtrip gives callers an independent snapshot of nested values.
        with self._lock:
            return json.loads(json.dumps(self._samples))

    @property
    def minimum_breached(self):
        return any(sample.get("memory_policy", {}).get("below_minimum") is True for sample in self.samples)

    def _sample(self):
        try:
            sample = resource_sample(self.minimum_available_bytes, self.include_gpu)
        except Exception as exc:  # Monitoring must not disguise a conversion failure.
            sample = {"observed_at_utc": _utc_now(), "status": "sampling_error", "error": str(exc)}
        sample["elapsed_seconds"] = round(time.monotonic() - self._started, 4)
        with self._lock:
            self._samples.append(sample)

    def _loop(self):
        while not self._stop.wait(self.interval_seconds):
            self._sample()

    def start(self):
        if self._started is not None:
            raise RuntimeError("A ResourceMonitor instance can be started only once")
        self._started = time.monotonic()
        self._sample()
        self._thread = threading.Thread(target=self._loop, name="pdf2tex-resource-monitor", daemon=True)
        self._thread.start()
        return self

    def stop(self):
        if self._started is None or self._ended is not None:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join()  # Its sole subprocess has a bounded 3-second timeout.
        self._final_process_memory = process_memory()
        self._ended = time.monotonic()

    def summary(self):
        samples = self.samples
        values = [s["memory"]["MemAvailable_bytes"] for s in samples
                  if s.get("memory", {}).get("MemAvailable_bytes") is not None]
        return {"sample_count": len(samples), "minimum_available_bytes_observed": min(values) if values else None,
                "configured_minimum_available_bytes": self.minimum_available_bytes,
                "minimum_breached": self.minimum_breached,
                "sampling_errors": sum(s.get("status") == "sampling_error" for s in samples),
                "elapsed_seconds": round((self._ended or time.monotonic()) - self._started, 4) if self._started else None,
                "process_memory_at_stop": self._final_process_memory,
                "limitations": ["Sampled observations may miss short peaks or threshold crossings.",
                                "Root-process peak RSS covers the process lifetime and excludes children/GPU allocations.",
                                "No services are stopped; no temperature threshold or dispatch action is imposed."]}

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        return False
