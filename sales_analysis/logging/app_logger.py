import datetime
import json
from pathlib import Path

from sales_analysis.project_paths import ProjectPaths


class AppActionLogger:
    def __init__(self, log_path: str | Path = "logs/app_actions.jsonl"):
        self.log_path = ProjectPaths.resolve(log_path)

    def log(self, actor, action, status="success", details=None):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": self.timestamp(),
            "actor": actor,
            "action": action,
            "status": status,
            "details": details or {},
        }
        with self.log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(event, sort_keys=True) + "\n")

    @staticmethod
    def timestamp():
        now = datetime.datetime.now(datetime.UTC)
        return now.isoformat(timespec="seconds")


class NullActionLogger:
    def log(self, actor, action, status="success", details=None):
        return None
