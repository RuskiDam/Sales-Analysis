import json
import tempfile
import unittest
from pathlib import Path

from sales_analysis.logging.app_logger import AppActionLogger


class AppActionLoggerTest(unittest.TestCase):
    def test_log_writes_json_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "actions.jsonl"
            logger = AppActionLogger(log_path)

            logger.log(
                "user",
                "run_historical_simulation",
                details={"months": 6},
            )

            rows = log_path.read_text(encoding="utf-8").splitlines()
            event = json.loads(rows[0])
            self.assertEqual(len(rows), 1)
            self.assertEqual(event["actor"], "user")
            self.assertEqual(event["action"], "run_historical_simulation")
            self.assertEqual(event["status"], "success")
            self.assertEqual(event["details"]["months"], 6)
            self.assertIn("timestamp", event)

    def test_log_appends_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "actions.jsonl"
            logger = AppActionLogger(log_path)

            logger.log("user", "reset_simulation")
            logger.log(
                "app",
                "ask_ai",
                "error",
                {"message": "Missing LLM API key."},
            )

            rows = log_path.read_text(encoding="utf-8").splitlines()
            first_event = json.loads(rows[0])
            second_event = json.loads(rows[1])
            self.assertEqual(len(rows), 2)
            self.assertEqual(first_event["action"], "reset_simulation")
            self.assertEqual(second_event["status"], "error")
            self.assertEqual(
                second_event["details"]["message"],
                "Missing LLM API key.",
            )


if __name__ == "__main__":
    unittest.main()
