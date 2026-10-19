"""No OCR/model imports: check evidence preservation and containment setup."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "probe" / "mineru_worker.py"
spec = importlib.util.spec_from_file_location("mineru_worker_test_target", MODULE)
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class WorkerContractTests(unittest.TestCase):
    def test_review_keeps_math_and_native_arrays(self):
        content = [{"type": "text", "content": "Let "},
                   {"type": "inline_equation", "content": r"X_t^{-1}"},
                   {"type": "text", "content": " be positive."}]
        payload = {"pages": [{"page_idx": 0, "blocks": [
            {"type": "text", "index": 2, "content": content},
            {"type": "equation", "index": 3, "content": ""}]}]}
        summary, candidates = worker.inspect_structure(payload, 1)
        self.assertEqual(candidates[0]["native_content"], content)
        self.assertEqual(candidates[0]["text"], r"Let X_t^{-1} be positive.")
        self.assertTrue(summary["page_coverage_complete"])
        self.assertEqual(summary["empty_math_block_ids"], ["p0:b3:n1"])

    def test_coverage_does_not_treat_duplicates_as_completeness(self):
        payload = {"pages": [{"page_idx": 0, "blocks": []}, {"page_idx": 0, "blocks": []},
                             {"page_idx": 3, "blocks": []}]}
        summary, _ = worker.inspect_structure(payload, 2)
        self.assertFalse(summary["page_coverage_complete"])
        self.assertEqual(summary["missing_page_indices"], [1])
        self.assertEqual(summary["duplicate_page_indices"], [0])
        self.assertEqual(summary["unexpected_page_indices"], [3])

    def test_private_config_overrides_inherited_remote_without_changing_home(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            models = root / "models"
            models.mkdir()
            with patch.dict(os.environ, {"MINERU_MODEL_VLM_SERVER_URL": "https://example.invalid",
                                         "MINERU_LLM_AIDED_FEATURES_TITLE_LEVELING": "true"}, clear=False):
                original_home = os.environ.get("HOME")
                worker.configure_local_environment(root, models, "basic")
                config = json.loads((root / "runtime" / "config.yaml").read_text())
                self.assertEqual(config["model"]["source"], "local")
                self.assertEqual(config["model"]["vlm"]["server_url"], "")
                self.assertNotIn("MINERU_MODEL_VLM_SERVER_URL", os.environ)
                self.assertFalse(config["llm_aided"]["features"]["title_leveling"])
                self.assertEqual(os.environ.get("HOME"), original_home)
                self.assertEqual(os.environ["CUDA_VISIBLE_DEVICES"], "")
                self.assertEqual(config["llm_aided"]["base_url"], "")
                self.assertFalse(config["llm_aided"]["features"]["cross_page_table_cell_merge"])
                self.assertEqual(os.environ["MINERU_MODEL_SOURCE"], "local")
                self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
                self.assertEqual(os.environ["TRANSFORMERS_OFFLINE"], "1")
                self.assertEqual(os.environ["HF_HUB_DISABLE_TELEMETRY"], "1")
                self.assertEqual(os.environ["VLLM_NO_USAGE_STATS"], "1")

    def test_python_guard_blocks_non_loopback_before_connect(self):
        code = (
            "import importlib.util,socket\n"
            f"s=importlib.util.spec_from_file_location('w',{str(MODULE)!r})\n"
            "w=importlib.util.module_from_spec(s);s.loader.exec_module(w)\n"
            "w.install_socket_audit_guard()\n"
            "try:\n socket.getaddrinfo('192.0.2.1',9)\n"
            "except PermissionError:\n print('blocked')\n"
            "else:\n raise RuntimeError('guard did not block')\n"
        )
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "blocked")


if __name__ == "__main__":
    unittest.main()
