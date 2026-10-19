"""CLI integration checks with real PDF windows and a deterministic fake worker.

These exercise persisted runs, resume, ownership and browser-facing reports.
They execute no converter, SSH, GPU query, model request or network namespace.
"""
import contextlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import fitz

from probe import cli
from probe.common import atomic_json, read_json, sha


class _HTMLTags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attributes = []

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)


class CLIIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "sources").mkdir()
        self.source = self.root / "sources/paper.pdf"
        with fitz.open() as pdf:
            for number in range(1, 12):
                pdf.new_page().insert_text((50, 70), "SOURCE SELECTED PAGE %d" % number)
            pdf.save(self.source)
        atomic_json(self.root / "sources.json", {
            "paper": {"pdf": "sources/paper.pdf", "sha256": sha(self.source),
                      "pages": 11, "original_pages": list(range(101, 112)), "ocr_mode": "auto"}
        })
        self.config = self.root / "configuration.json"
        atomic_json(self.config, {"local_only": True, "window_pages": 4, "overlap_pages": 1,
                                 "minimum_available_gib_basic": 2,
                                 "conversion_timeout_seconds": 30})
        self.isolation_mode = "namespace"
        self.executions = []
        self.worker_status = "completed"
        self.summary_transform = lambda data: data
        self.raw_summary = None
        self.worker_text = None
        self.root_patch = patch.object(cli, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.runtime_patch = patch.object(cli, "runtime_signature", return_value={
            "packages": [["mineru", "4.0.12"]], "model_files": [{"sha256": "fixture"}],
            "worker_sha256": "mock-worker-v1"})
        self.runtime_mock = self.runtime_patch.start()
        self.addCleanup(self.runtime_patch.stop)
        self.namespace_patch = patch.object(cli.subprocess, "run", return_value=subprocess.CompletedProcess(
            ["unshare"], 0, stdout="", stderr=""))
        self.namespace_mock = self.namespace_patch.start()
        self.addCleanup(self.namespace_patch.stop)
        self.memory_patch = patch.object(cli, "memory_inventory", return_value={"MemAvailable_bytes": 64 * 1024 ** 3})
        self.memory_patch.start()
        self.addCleanup(self.memory_patch.stop)
        self.worker_patch = patch.object(cli, "execute_window", side_effect=self._fake_worker)
        self.worker_mock = self.worker_patch.start()
        self.addCleanup(self.worker_patch.stop)

    def _fake_worker(self, command, attempt, minimum, timeout):
        self.executions.append(Path(attempt))
        if self.isolation_mode == "namespace":
            self.assertEqual(command[:4], ["unshare", "--user", "--map-root-user", "--net"])
        else:
            self.assertEqual(command[0], str(Path(sys.executable).absolute()))
            self.assertFalse(any(item in ("unshare", "bwrap") for item in command))
        output = Path(command[command.index("--output") + 1])
        self.assertEqual(output, attempt / "output")
        output.mkdir()
        with fitz.open(attempt / "input.pdf") as pdf:
            count = pdf.page_count
            text = "\n".join(page.get_text() for page in pdf)
        summary = {"status": "extracted_unreviewed", "observed_page_indices": list(range(count)),
                   "scope": "synthetic mock converter"}
        if self.raw_summary is None:
            atomic_json(output / "summary.json", self.summary_transform(summary))
        else:
            (output / "summary.json").write_text(self.raw_summary, encoding="utf-8")
        (output / "document.md").write_text(self.worker_text if self.worker_text is not None else text, encoding="utf-8")
        (output / "document.tex").write_text("% synthetic test output; not OCR or compile gold\n", encoding="utf-8")
        (attempt / "worker.log").write_text("Synthetic converter; no inference executed.\n", encoding="utf-8")
        return self.worker_status

    def _convert(self, resume=None, isolation=None):
        before = set((self.root / "runs").glob("convert-*")) if (self.root / "runs").exists() else set()
        args = ["--config", str(self.config), "convert", "--source", "paper",
                "--converter-python", sys.executable, "--models-dir", str(self.root / "models")]
        if isolation is not None:
            self.isolation_mode = isolation
            args += ["--ocr-isolation", isolation]
        if resume is not None:
            args += ["--resume", str(resume)]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(args)
        created = set((self.root / "runs").glob("convert-*")) - before
        if resume is not None:
            return code, resume
        return code, next(iter(created)) if created else None

    def test_none_skips_namespace_and_persists_mode_and_refuses_changed_resume(self):
        self.namespace_mock.side_effect = FileNotFoundError("namespace tools unavailable")
        code, run = self._convert(isolation="none")
        self.assertEqual(code, 0)
        self.namespace_mock.assert_not_called()
        state = read_json(run / "state.json")
        self.assertEqual(state["settings"]["ocr_isolation"], "none")
        self.assertEqual(state["ocr_isolation"]["status"], "deliberately_not_run")
        for attempt in self.executions:
            evidence = read_json(attempt / "completion.json")["ocr_isolation"]
            self.assertFalse(evidence["namespace_established"])
            self.assertEqual(evidence["worker_namespace_status"], "not_requested")
        self.assertIn("local processing; no OS network isolation", (run / "review.html").read_text())
        report = read_json(run / "quality-report.json")["ocr_isolation"]
        self.assertEqual(report["requested"], "none")
        self.assertEqual(report["namespace_probe"]["status"], "deliberately_not_run")
        self.assertTrue(all(item["worker"]["namespace_established"] is False
                            for item in report["attempts"].values()))
        before = (run / "state.json").read_bytes()
        self.executions.clear()
        code, _ = self._convert(run, isolation="namespace")
        self.assertEqual(code, 2)
        self.assertEqual(self.executions, [])
        self.assertEqual((run / "state.json").read_bytes(), before)
        self.namespace_mock.assert_not_called()

    def test_explicit_namespace_failure_never_falls_back(self):
        self.namespace_mock.side_effect = FileNotFoundError("unshare missing")
        code, run = self._convert(isolation="namespace")
        self.assertEqual(code, 3)
        self.worker_mock.assert_not_called()
        evidence = read_json(run / "state.json")["ocr_isolation"]
        self.assertEqual(evidence["status"], "failed")
        self.assertFalse(evidence["namespace_established"])

    def test_windows_own_each_selected_page_once_and_keep_real_adjacent_context(self):
        code, run = self._convert()
        self.assertEqual(code, 0)
        owned = []
        repeated_context = []
        for attempt in self.executions:
            mapping = read_json(attempt / "page-map.json")
            with fitz.open(attempt / "input.pdf") as pdf:
                self.assertEqual(pdf.page_count, len(mapping))
                for index, record in enumerate(mapping):
                    self.assertEqual(record["local_page_idx"], index)
                    self.assertIn("SOURCE SELECTED PAGE %d" % record["selected_page"], pdf[index].get_text())
                    self.assertEqual(record["original_physical_page"], record["selected_page"] + 100)
                    (owned if record["owner"] else repeated_context).append(record["selected_page"])
        self.assertEqual(sorted(owned), list(range(1, 12)))
        self.assertGreater(len(repeated_context), 0)
        quality = read_json(run / "quality-report.json")
        self.assertEqual(quality["coverage"]["paper"]["duplicated_owned_pages"], 0)
        self.assertEqual(quality["coverage"]["paper"]["missing_selected_pages"], [])
        self.assertEqual(quality["fidelity"], "unreviewed")

    def test_missing_page_is_partial_and_not_counted_as_owned_coverage(self):
        self.summary_transform = lambda data: {**data, "observed_page_indices": data["observed_page_indices"][:-1]}
        code, run = self._convert()
        self.assertNotEqual(code, 0)
        state = read_json(run / "state.json")
        self.assertEqual(state["status"], "partial")
        self.assertEqual(len(self.executions), 1)
        self.assertIn("coverage_error", next(iter(state["units"].values())))
        quality = read_json(run / "quality-report.json")
        self.assertEqual(quality["coverage"]["paper"]["accounted_by_successful_windows"], 0)

    def test_duplicate_page_is_rejected_even_when_page_count_matches(self):
        def duplicate(data):
            pages = list(data["observed_page_indices"])
            pages[-1] = pages[-2]
            return {**data, "observed_page_indices": pages}
        self.summary_transform = duplicate
        code, run = self._convert()
        self.assertNotEqual(code, 0)
        self.assertEqual(read_json(run / "state.json")["status"], "partial")
        self.assertEqual(len(self.executions), 1)

    def test_boolean_indices_cannot_certify_page_coverage(self):
        def booleans(data):
            pages = list(data["observed_page_indices"])
            pages[0], pages[1] = False, True
            return {**data, "observed_page_indices": pages}
        self.summary_transform = booleans
        code, run = self._convert()
        self.assertNotEqual(code, 0, "False/True compare equal to 0/1 but are not valid page indices")
        self.assertNotEqual(read_json(run / "state.json")["status"], "conversion_completed_unreviewed")

    def test_successful_resume_dispatches_nothing_and_preserves_attempt_bytes(self):
        code, run = self._convert()
        self.assertEqual(code, 0)
        before = {path.relative_to(run).as_posix(): path.read_bytes()
                  for path in (run / "attempts").rglob("*") if path.is_file()}
        self.executions.clear()
        code, _ = self._convert(run)
        self.assertEqual(code, 0)
        self.assertEqual(self.executions, [])
        after = {path.relative_to(run).as_posix(): path.read_bytes()
                 for path in (run / "attempts").rglob("*") if path.is_file()}
        self.assertEqual(before, after)

    def test_resume_refuses_changed_output_hash_without_dispatching(self):
        _, run = self._convert()
        changed = self.executions[0] / "output/document.md"
        changed.write_text("unexpected later change", encoding="utf-8")
        self.executions.clear()
        code, _ = self._convert(run)
        self.assertNotEqual(code, 0)
        self.assertEqual(self.executions, [])
        self.assertEqual(changed.read_text(), "unexpected later change")

    def test_resume_refuses_unmanifested_added_output(self):
        _, run = self._convert()
        (self.executions[0] / "output/untracked-later-file.txt").write_text("not part of accepted generation")
        self.executions.clear()
        code, _ = self._convert(run)
        self.assertNotEqual(code, 0, "Changed output membership must invalidate an immutable generation")
        self.assertEqual(self.executions, [])

    def test_changed_source_is_rejected_before_runtime_or_child_dispatch(self):
        with self.source.open("ab") as output:
            output.write(b"\nchanged after registration\n")
        code, run = self._convert()
        self.assertNotEqual(code, 0)
        self.assertIsNone(run)
        self.runtime_mock.assert_not_called()
        self.worker_mock.assert_not_called()

    def test_failed_egress_boundary_persists_blocked_state_without_child(self):
        self.namespace_mock.return_value = subprocess.CompletedProcess(["unshare"], 1, stdout="", stderr="operation not permitted")
        code, run = self._convert()
        self.assertEqual(code, 3)
        self.assertEqual(read_json(run / "state.json")["status"], "blocked_network_isolation")
        self.worker_mock.assert_not_called()
        self.assertFalse((run / "attempts").exists())

    def test_retry_keeps_failed_attempt_and_creates_new_attempt(self):
        self.worker_status = "failed"
        code, run = self._convert()
        self.assertNotEqual(code, 0)
        original = self.executions[0]
        before = {path.relative_to(original).as_posix(): path.read_bytes()
                  for path in original.rglob("*") if path.is_file()}
        self.worker_status = "completed"
        self.executions.clear()
        code, _ = self._convert(run)
        self.assertEqual(code, 0)
        self.assertNotIn(original, self.executions)
        after = {path.relative_to(original).as_posix(): path.read_bytes()
                 for path in original.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(read_json(original / "completion.json")["status"], "failed")

    def test_unavailable_namespace_tool_still_bundles_blocked_diagnostics(self):
        for error in (FileNotFoundError("unshare missing"), subprocess.TimeoutExpired("unshare", 10)):
            with self.subTest(error=type(error).__name__):
                self.namespace_mock.side_effect = error
                code, run = self._convert()
                self.assertEqual(code, 3)
                self.assertEqual(read_json(run / "state.json")["status"], "blocked_network_isolation")
                self.assertTrue((self.root / "results" / (run.name + "-upload.zip")).is_file())
                self.worker_mock.assert_not_called()

    def test_mid_window_memory_pause_preserves_evidence_and_returns_75(self):
        self.worker_status = "paused_memory"
        code, run = self._convert()
        self.assertEqual(code, 75)
        self.assertEqual(len(self.executions), 1)
        self.assertEqual(read_json(run / "state.json")["status"], "paused_memory")
        self.assertEqual(read_json(self.executions[0] / "completion.json")["status"], "paused_memory")
        self.assertTrue((self.root / "results" / (run.name + "-upload.zip")).is_file())

    def test_malformed_summary_persists_terminal_failure_and_attempt_evidence(self):
        self.raw_summary = '{"observed_page_indices": INVALID JSON'
        code, run = self._convert()
        self.assertNotEqual(code, 0)
        state = read_json(run / "state.json")
        self.assertNotIn(state["status"], ("running", "created", "conversion_completed_unreviewed"))
        record = next(iter(state["units"].values()))
        self.assertNotIn(record["status"], ("running", "completed"))
        completion = run / record["attempt"] / "completion.json"
        self.assertTrue(completion.exists(), "Worker-success/output-validation failure still needs an attempt result")
        self.assertEqual((run / record["attempt"] / "output/summary.json").read_text(), self.raw_summary)

    def test_nonobject_summary_is_a_recorded_validation_failure(self):
        self.raw_summary = '[]'
        code, run = self._convert()
        self.assertNotEqual(code, 0)
        state = read_json(run / "state.json")
        self.assertNotIn(state["status"], ("running", "created", "conversion_completed_unreviewed"))
        record = next(iter(state["units"].values()))
        self.assertTrue((run / record["attempt"] / "completion.json").exists())

    def test_report_escapes_recognized_text_and_persisted_display_fields(self):
        self.worker_text = '</pre><script>alert("ocr")</script><img src=x onerror=alert(1)>& text'
        _, run = self._convert()
        state = read_json(run / "state.json")
        state["status"] = '<svg onload="alert(2)">'
        old = next(iter(state["units"]))
        state["units"]['<script>alert("unit")</script>'] = state["units"].pop(old)
        atomic_json(run / "state.json", state)
        with contextlib.redirect_stdout(io.StringIO()):
            cli.report_run(run)
        source = (run / "review.html").read_text()
        parsed = _HTMLTags()
        parsed.feed(source)
        for forbidden in ("script", "img", "svg"):
            self.assertNotIn(forbidden, parsed.tags)
        self.assertFalse(any(name.lower().startswith("on") for name, value in parsed.attributes))
        self.assertIn("&lt;script&gt;", source)
        self.assertIn("&amp; text", source)

    def test_report_never_emits_active_javascript_attempt_links(self):
        _, run = self._convert()
        state = read_json(run / "state.json")
        next(iter(state["units"].values()))["attempt"] = "javascript:alert(1)//"
        atomic_json(run / "state.json", state)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                cli.report_run(run)
        except ValueError:
            return  # Rejecting the corrupt record is also safe.
        parsed = _HTMLTags()
        parsed.feed((run / "review.html").read_text())
        self.assertFalse(any(name == "href" and value.lower().startswith("javascript:")
                             for name, value in parsed.attributes))


if __name__ == "__main__":
    unittest.main()
