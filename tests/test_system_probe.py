"""Bounded unit tests; no SSH connection, GPU query, or package import is run."""
import json
import subprocess
import unittest
from unittest.mock import patch

from probe import system_probe as sp


class MeminfoTests(unittest.TestCase):
    def test_kb_means_kib_and_missing_is_not_zero(self):
        result = sp.parse_meminfo("MemTotal: 128000 kB\nMemAvailable: 42 kB\nSwapFree: 0 kB\nHugePages_Total: 3\n")
        self.assertEqual(result["MemTotal"], 128000 * 1024)
        self.assertEqual(result["MemAvailable"], 42 * 1024)
        self.assertEqual(result["SwapFree"], 0)
        self.assertNotIn("HugePages_Total", result)
        self.assertNotIn("SwapTotal", result)

    def test_bad_or_unknown_units_are_not_trusted(self):
        self.assertEqual(sp.parse_meminfo("MemAvailable: -1 kB\nMemTotal: 1 MB\nSwapFree: no kB"), {})
        self.assertEqual(sp.parse_meminfo(None), {})

    def test_policy_boundary_and_unavailable(self):
        self.assertFalse(sp.memory_policy({"MemAvailable_bytes": 100}, 100)["below_minimum"])
        self.assertTrue(sp.memory_policy({"MemAvailable_bytes": 99}, 100)["below_minimum"])
        self.assertEqual(sp.memory_policy({}, 100)["status"], "unavailable")
        self.assertEqual(sp.memory_policy({}, None)["status"], "disabled")

    def test_threshold_validation(self):
        for invalid in (-1, 1.5, True, "5", float("inf")):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                sp.validate_minimum_available_bytes(invalid)
        self.assertEqual(sp.validate_minimum_available_bytes(0), 0)


class SSHTests(unittest.TestCase):
    def test_valid_aliases(self):
        for alias in ("spark-92a4", "gpu.local", "spark_A", "192.168.1.109"):
            self.assertEqual(sp.validate_ssh_alias(alias), alias)

    def test_options_and_metacharacters_rejected_before_subprocess(self):
        invalid = ("", "-oProxyCommand=id", "--", "spark;id", "spark$(id)", "spark`id`",
                   "spark\nwhoami", "spark node", "user@spark", "../spark", "[::1]", None, "a" * 254)
        with patch.object(sp, "_run_diagnostic") as run:
            for alias in invalid:
                with self.subTest(alias=alias), self.assertRaises(ValueError):
                    sp.remote_inventory(alias)
            run.assert_not_called()

    @patch.object(sp.shutil, "which", return_value="/usr/bin/ssh")
    def test_fixed_remote_program_and_trusted_noninteractive_transport(self, _which):
        payload = {"hostname": "test", "meminfo": "MemAvailable: 10 kB\n",
                   "gpu": {"status": "error", "stdout": "unsupported"},
                   "compute_processes": {"status": "ok", "stdout": ""}}
        with patch.object(sp, "_run_diagnostic", return_value={"status": "ok", "stdout": json.dumps(payload)}) as run:
            result = sp.remote_inventory("spark-92a4")
        command = run.call_args.args[0]
        separator = command.index("--")
        self.assertEqual(command[separator + 1:separator + 4], ["spark-92a4", "python3", "-c"])
        self.assertIn("-oBatchMode=yes", command)
        self.assertIn("-oStrictHostKeyChecking=yes", command)
        self.assertIn("-oUpdateHostKeys=no", command)
        self.assertEqual(result["inventory"]["memory"]["MemAvailable_bytes"], 10240)


class DiagnosticTests(unittest.TestCase):
    def test_timeout_partial_output_and_shell_false(self):
        with patch.object(sp.subprocess, "run", side_effect=subprocess.TimeoutExpired("nvidia-smi", 1, output=b"partial")) as run:
            result = sp._run_diagnostic(["nvidia-smi"], timeout=1)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["stdout"], "partial")
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_unsupported_gpu_values_are_not_zero(self):
        records = sp._csv_records('0, GPU-test, NVIDIA GB10, 580, [N/A], [Not Supported], [N/A], 45, 0, 12\n', sp.GPU_FIELDS)
        self.assertEqual(records[0]["memory.used"], "[Not Supported]")
        self.assertEqual(records[0]["temperature.gpu"], "45")


class MonitorTests(unittest.TestCase):
    def test_threshold_is_record_only_and_body_exception_survives(self):
        sample = {"memory": {"MemAvailable_bytes": 10}, "memory_policy": {"below_minimum": True}}
        with patch.object(sp, "resource_sample", return_value=sample), patch.object(sp, "process_memory", return_value={"rss_bytes": 2}):
            monitor = sp.ResourceMonitor(interval_seconds=100, minimum_available_bytes=20, include_gpu=False)
            with self.assertRaisesRegex(RuntimeError, "conversion failed"):
                with monitor:
                    raise RuntimeError("conversion failed")
        self.assertTrue(monitor.minimum_breached)
        self.assertEqual(monitor.summary()["minimum_available_bytes_observed"], 10)
        self.assertFalse(monitor._thread.is_alive())
        self.assertEqual(monitor.summary()["sample_count"], 1)

    def test_no_infinite_or_nonpositive_sampling_intervals(self):
        for invalid in (0, -1, float("nan"), float("inf"), True, "2"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                sp.ResourceMonitor(interval_seconds=invalid)


if __name__ == "__main__":
    unittest.main()
