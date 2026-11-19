import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("run_claude_marketing", Path(__file__).resolve().parents[1] / "run_claude_marketing.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class OrchestratorPreflightTests(unittest.TestCase):
    def test_not_due_does_not_load_credentials_or_launch_claude(self):
        result = subprocess.CompletedProcess([], 10, json.dumps({"due": False, "reason": "before first slot"}))
        with patch.object(runner.subprocess, "run", return_value=result) as run, patch.object(runner.runpy, "run_path") as load:
            self.assertEqual(runner.preflight()["status"], "skipped")
        load.assert_not_called()
        self.assertEqual(run.call_count, 1)

    def test_missing_key_blocks_before_invoking_claude(self):
        class MissingKey(Exception):
            pass

        class Provider:
            def check_available(self, today):
                raise MissingKey("OPENAI_API_KEY is not set")

        result = subprocess.CompletedProcess([], 0, json.dumps({"due": True}))
        with patch.object(runner.subprocess, "run", return_value=result) as run, patch.object(
            runner.runpy, "run_path", return_value={"get_provider": lambda cfg, root: Provider(), "TTSUnavailable": MissingKey},
        ):
            self.assertEqual(runner.preflight()["status"], "blocked_audio")
        self.assertEqual(run.call_count, 1)

    def test_schedule_failure_is_not_reported_as_success(self):
        result = subprocess.CompletedProcess([], 1, "")
        with patch.object(runner.subprocess, "run", return_value=result):
            self.assertEqual(runner.preflight()["status"], "failed")


if __name__ == "__main__":
    unittest.main()
