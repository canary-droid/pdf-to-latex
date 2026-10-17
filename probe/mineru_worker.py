"""One stateless, local MinerU 4.0.12 extraction in an isolated interpreter.

This module deliberately imports no MinerU code until its private configuration
is installed. OS network isolation belongs to the controller. The Python audit
hook is additional protection, not an OS sandbox or a claim about native code.
See docs/UPSTREAM_MINERU.md for the source contract used here.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.metadata
import ipaddress
import json
import os
from pathlib import Path
import platform
import socket
import sys
import time
from typing import Any

EXPECTED_MINERU = "4.0.12"
MAX_CANDIDATE_CHARS = 40000


class PreflightBlocked(RuntimeError):
    pass


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configure_local_environment(output: Path, models: Path, tier: str) -> dict[str, Any]:
    """Set only this child process's environment; do not touch HOME/system Python."""
    if any(name == "mineru" or name.startswith("mineru.") for name in sys.modules):
        raise PreflightBlocked("MinerU was imported before private configuration")
    for name in list(os.environ):
        if name.startswith("MINERU_"):
            del os.environ[name]
    runtime_dir = output / "runtime"
    runtime_dir.mkdir()
    configuration = {
        "model": {
            "source": "local", "base_dir": str(models), "small_backend": "onnx",
            "vlm": {"engine": "vllm" if tier == "standard" else "llama-cpp",
                    "server_url": "", "api_key": "", "model": "", "max_concurrency": 1},
        },
        "llm_aided": {"api_key": "", "base_url": "", "model": "", "max_concurrency": 1,
                      "features": {"title_leveling": False, "cross_page_table_cell_merge": False}},
    }
    # JSON is a valid YAML subset; no third-party YAML import is needed here.
    config_path = runtime_dir / "config.yaml"
    write_json(config_path, configuration)
    os.environ.update({
        "MINERU_HOME": str(runtime_dir), "MINERU_CONFIG": str(config_path),
        "MINERU_MODEL_SOURCE": "local", "MINERU_MODEL_BASE_DIR": str(models),
        "MINERU_MODEL_SMALL_BACKEND": "onnx", "MINERU_TABLE_DEVICE": "cpu",
        "MINERU_DEVICE_MODE": "cuda" if tier == "standard" else "cpu",
        "MINERU_PROCESSING_WINDOW_SIZE": "2", "MINERU_PDF_RENDER_THREADS": "1",
        "MINERU_INTRA_OP_NUM_THREADS": "2", "MINERU_INTER_OP_NUM_THREADS": "1",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
        "VLLM_NO_USAGE_STATS": "1", "DO_NOT_TRACK": "1", "GRADIO_ANALYTICS_ENABLED": "False",
    })
    if tier == "basic":
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    # Never let an inherited proxy or cloud credential direct this local worker.
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy",
                 "OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENROUTER_API_KEY", "HF_TOKEN", "HUGGING_FACE_HUB_TOKEN"):
        os.environ.pop(name, None)
    return configuration


def install_socket_audit_guard() -> None:
    """Deny Python Internet sockets except loopback; allow local IPC."""
    def guard(event: str, args: tuple[Any, ...]) -> None:
        if event not in {"socket.connect", "socket.sendto", "socket.getaddrinfo"}:
            return
        if event == "socket.getaddrinfo":
            host = args[0]
        else:
            sock = args[0]
            if getattr(sock, "family", None) not in (socket.AF_INET, socket.AF_INET6):
                return
            address = args[1] if event == "socket.connect" else args[-1]
            host = address[0] if isinstance(address, tuple) else address
        if host is None or host in ("localhost", b"localhost"):
            return
        if isinstance(host, bytes):
            host = host.decode("ascii", errors="strict")
        try:
            local = ipaddress.ip_address(str(host).split("%", 1)[0]).is_loopback
        except ValueError:
            local = False
        if not local:
            raise PermissionError("Local probe blocked a non-loopback Python socket")
    sys.addaudithook(guard)


def package_versions() -> dict[str, str | None]:
    result = {}
    for name in ("mineru", "docvortex", "onnxruntime", "onnxruntime-gpu", "pypdfium2", "numpy",
                 "mineru-vl-utils", "mineru-llama-cpp", "torch", "torchvision", "transformers", "vllm"):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def verify_runtime(tier: str, engine: str | None, models: Path, *, hash_models: bool) -> dict[str, Any]:
    versions = package_versions()
    if versions["mineru"] != EXPECTED_MINERU:
        raise PreflightBlocked(f"Requires MinerU {EXPECTED_MINERU}; installed {versions['mineru']!r}")
    missing = [name for name in ("docvortex", "onnxruntime", "pypdfium2") if not versions[name]]
    if missing:
        raise PreflightBlocked("Required extraction packages are absent: " + ", ".join(missing))
    try:
        from packaging.version import Version
        if not Version("0.5.16") <= Version(versions["docvortex"]) < Version("1"):
            raise PreflightBlocked("DocVortex does not satisfy the pinned MinerU requirement >=0.5.16,<1")
    except ImportError as exc:
        raise PreflightBlocked("Runtime is incomplete: packaging.version is unavailable") from exc
    if versions["onnxruntime-gpu"]:
        raise PreflightBlocked("Use the CPU onnxruntime distribution, without onnxruntime-gpu, for this probe")
    if tier == "standard" and engine != "vllm":
        raise PreflightBlocked("Standard requires explicit --engine vllm; no engine fallback is allowed")
    if tier == "basic" and engine is not None:
        raise PreflightBlocked("Basic uses ONNX CPU and accepts no VLM engine")
    from mineru.config import config
    from mineru.model.download import verify_model_repo
    from mineru.model.registry import model_repos_for_tier
    from mineru.model.runtime.device import resolve_small_model_backend
    import onnxruntime

    if (config.model.source != "local" or config.model.vlm.server_url or
            config.llm_aided.features.title_leveling or config.llm_aided.features.cross_page_table_cell_merge):
        raise PreflightBlocked("Effective configuration is not the required local-only configuration")
    if resolve_small_model_backend() != "onnx":
        raise PreflightBlocked("Small-model backend drifted from explicit ONNX")
    runtime: dict[str, Any] = {
        "versions": versions, "python": sys.version, "architecture": platform.machine(),
        "small_backend_selected": "onnx", "small_device_selected": "cpu",
        "onnx_available_providers": onnxruntime.get_available_providers(),
        "vlm_engine_selected": "vllm" if tier == "standard" else None,
        "device_measurement_scope": "selection and availability; session/kernel execution is not independently instrumented",
        "models_dir": str(models),
    }
    if tier == "standard":
        if not versions["vllm"] or not versions["torch"]:
            raise PreflightBlocked("Standard requires an independently prepared, qualified local vLLM/Torch environment")
        import torch
        from mineru.model.vlm.selector import resolve_vlm_engine
        if resolve_vlm_engine("vllm") != "vllm" or not torch.cuda.is_available():
            raise PreflightBlocked("Explicit vLLM CUDA runtime is unavailable")
        free, total = torch.cuda.mem_get_info()
        runtime["cuda"] = {"name": torch.cuda.get_device_name(), "capability": list(torch.cuda.get_device_capability()),
                           "torch_cuda": torch.version.cuda, "free_bytes": free, "total_bytes": total}
        # Probe operating policy, not a vendor requirement or fit guarantee.
        if free < 16 * 1024**3:
            raise PreflightBlocked("Standard probe requires at least 16 GiB currently free on its selected GPU")
        runtime["vlm_memory_policy"] = "Pinned MinerU native vLLM default; upstream has a 0.1 total-memory floor. No claim of coexistence with GLM."

    repos = model_repos_for_tier(tier, small_backend="onnx", vlm_engine="vllm" if tier == "standard" else None)
    readiness = []
    roots: list[Path] = []
    for repo in repos:
        check = verify_model_repo(repo)
        readiness.append({"name": repo.name, "root": str(check.root), "ready": check.ready,
                          "missing_paths": [str(item) for item in check.missing_paths]})
        roots.append(Path(check.root))
    runtime["model_readiness"] = readiness
    if not all(item["ready"] for item in readiness):
        raise PreflightBlocked("Required local model assets are incomplete; prepare them separately without passing a PDF")
    if hash_models:
        assets = []
        seen: set[Path] = set()
        for root in roots:
            for file in sorted(root.rglob("*")):
                if not file.is_file() or ".cache" in file.relative_to(root).parts:
                    continue
                actual = file.resolve()
                if actual in seen:
                    continue
                seen.add(actual)
                stat = file.stat()
                assets.append({"path": str(file.relative_to(models)), "size": stat.st_size,
                               "mtime_ns": stat.st_mtime_ns, "sha256": sha256_file(file)})
        runtime["model_assets"] = assets
        runtime["model_asset_hash_scope"] = "All files under required model roots, excluding provider .cache bookkeeping; content hashes, not upstream authenticity verification"
    return runtime


def native_text(content: Any) -> str:
    """Convenience view only: preserve original content separately in candidates."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(native_text(item.get("content", "")) if isinstance(item, dict) else native_text(item) for item in content)
    return ""


def inspect_structure(payload: dict[str, Any], expected_count: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    pages = payload.get("pages", [])
    if not isinstance(pages, list):
        raise ValueError("MiddleJson pages is not an array")
    observed, candidates, counts, empty_pages, image_math = [], [], Counter(), [], []
    for page in pages:
        index = page.get("page_idx")
        if not isinstance(index, int) or isinstance(index, bool):
            raise ValueError("Missing or invalid native page_idx")
        observed.append(index)
        blocks = page.get("blocks", [])
        if not blocks:
            empty_pages.append(index)
        for ordinal, block in enumerate(blocks):
            if not isinstance(block, dict):
                raise ValueError("Native block is not an object")
            kind = str(block.get("type", "unknown"))
            counts[kind] += 1
            identity = f"p{index}:b{block.get('index', ordinal)}:n{ordinal}"
            text = native_text(block.get("content"))
            candidate = {"id": identity, "page_idx": index, "kind": kind,
                         "text": text[:MAX_CANDIDATE_CHARS], "text_truncated": len(text) > MAX_CANDIDATE_CHARS,
                         "native_content": block.get("content"), "source_block_index": block.get("index"),
                         "text_is_backend_transcription_not_verified": True}
            if "bbox" in block:
                candidate["bbox"] = block["bbox"]
            candidates.append(candidate)
            if kind in {"equation", "formula", "display_equation"} and not text.strip():
                image_math.append(identity)
    duplicates = sorted(index for index, number in Counter(observed).items() if number > 1)
    expected = set(range(expected_count))
    return {
        "observed_page_indices": observed, "expected_page_count": expected_count,
        "missing_page_indices": sorted(expected - set(observed)),
        "unexpected_page_indices": sorted(set(observed) - expected), "duplicate_page_indices": duplicates,
        "page_coverage_complete": set(observed) == expected and not duplicates,
        "empty_block_page_indices": empty_pages, "block_counts": dict(counts),
        "empty_math_block_ids": image_math,
        "quality_status": "unreviewed; page coverage and compilation cannot establish mathematical fidelity",
    }, candidates


def run(args: argparse.Namespace) -> int:
    output = Path(args.output).expanduser().resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise PreflightBlocked("Output must be a new or empty directory")
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    summary: dict[str, Any] = {"status": "preflight", "tier": args.tier, "ocr_mode": args.ocr_mode,
        "observed_page_indices": [], "backend": "mineru", "expected_backend_version": EXPECTED_MINERU,
        "network": {"policy": "local SDK only; no downloads; no remote VLM or LLM-aided stage",
                    "python_socket_guard": "non-loopback denied; not an OS/native-code security boundary",
                    "os_network_isolation": "controller responsibility; not asserted by this worker"},
        "telemetry": {"mineru_doclib": "not started or used by stateless SDK", "vllm_usage_stats": "disabled by environment",
                      "huggingface": "disabled and offline"}}
    try:
        model_value = args.models_dir or os.environ.get("PDF2TEX_MODELS_DIR")
        if not model_value:
            raise PreflightBlocked("Pass --models-dir or PDF2TEX_MODELS_DIR explicitly")
        models = Path(model_value).expanduser().resolve(strict=True)
        if not models.is_dir():
            raise PreflightBlocked("Model cache is not a directory")
        configure_local_environment(output, models, args.tier)
        install_socket_audit_guard()
        summary["runtime"] = {"versions": package_versions()}
        summary["runtime"] = verify_runtime(args.tier, args.engine, models, hash_models=args.probe_runtime)
        if args.probe_runtime:
            summary["status"] = "runtime_preflight_passed_not_inference_tested"
            return 0
        if not args.input:
            raise PreflightBlocked("--input is required except with --probe-runtime")
        pdf = Path(args.input).expanduser().resolve(strict=True)
        if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
            raise PreflightBlocked("Input must be an existing local PDF")
        if output == pdf.parent or output in pdf.parents:
            raise PreflightBlocked("Input cannot be inside the output directory")
        import pypdfium2
        with pypdfium2.PdfDocument(str(pdf)) as document:
            expected_count = len(document)
        if expected_count < 1:
            raise PreflightBlocked("PDF contains no pages")
        summary["input"] = {"name": pdf.name, "sha256": sha256_file(pdf), "page_count": expected_count}
        from mineru.config import VlmConfig
        from mineru.parser import ParseResult, parse
        from mineru.parser.writer import FileBasedDataWriter
        from mineru.render import render_latex
        settings = VlmConfig(engine="vllm" if args.tier == "standard" else "llama-cpp",
                             server_url="", api_key="", model="", max_concurrency=1)
        result = parse(str(pdf), tier=args.tier, ocr_mode=args.ocr_mode,
                       image_analysis=True, page_range="all", vlm_config=settings)
        (output / "raw_middle_json.json").write_text(result.to_json(), encoding="utf-8")
        result.save(FileBasedDataWriter(str(output)))
        # save() materializes assets on a copy. Reload THAT representation for
        # LaTeX so its image paths match the exported assets, not transient data.
        saved = ParseResult.from_json((output / "middle_json.json").read_text(encoding="utf-8"))
        payload = json.loads((output / "middle_json.json").read_text(encoding="utf-8"))
        if payload.get("schema") != "docvortex.middle" or payload.get("schema_version") != "2.0":
            raise RuntimeError("Unexpected MiddleJson schema; raw outputs retained")
        tex = render_latex(saved.middle_json, asset_base_path="")
        if not isinstance(tex, str) or "\\documentclass" not in tex or "\\end{document}" not in tex:
            raise RuntimeError("Native LaTeX renderer did not return a full document")
        (output / "document.tex").write_text(tex, encoding="utf-8")
        (output / "document.md").write_bytes((output / "markdown.md").read_bytes())
        checks, candidates = inspect_structure(payload, expected_count)
        summary.update(checks)
        summary["native_extensions"] = payload.get("extensions", {})
        summary["producer"] = payload.get("metadata", {}).get("producer")
        summary["schema"] = {"name": payload.get("schema"), "version": payload.get("schema_version")}
        summary["raw_json_note"] = "raw_middle_json.json omits PDF embedded bytes per upstream; middle_json.json plus images/ is the materialized complete package"
        write_json(output / "review_candidates.json", candidates)
        summary["assets"] = [{"path": str(path.relative_to(output)), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
                             for path in sorted((output / "images").rglob("*")) if path.is_file()]
        summary["native_latex_status"] = "exported; compilation and fidelity not verified"
        summary["status"] = "extracted_unreviewed"
        return 0
    except PreflightBlocked as exc:
        summary.update(status="preflight_blocked", error=str(exc))
        return 2
    except Exception as exc:
        summary.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        return 3
    finally:
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        write_json(output / "summary.json", summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input")
    parser.add_argument("--output", required=True)
    parser.add_argument("--tier", choices=("basic", "standard"), default="basic")
    parser.add_argument("--ocr-mode", choices=("auto", "ocr"), default="auto")
    parser.add_argument("--engine", choices=("vllm",))
    parser.add_argument("--models-dir")
    parser.add_argument("--probe-runtime", action="store_true", help="Check dependencies/readiness and hash model files; do not open a PDF or run inference")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except (PreflightBlocked, OSError) as exc:
        print(f"Worker blocked before output creation: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
