"""repair_task.py — Repair task dataclass for AutoRepair system."""


class RepairTask:
    """Single repair task with status tracking."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    FAILED = "failed"
    SKIPPED = "skipped"

    def __init__(self, skill_name, issue_type, description, severity="medium"):
        self.skill_name = skill_name
        self.issue_type = issue_type
        self.description = description
        self.severity = severity
        self.status = self.PENDING
        self.attempts = 0
        self.max_attempts = 3
        self.result = None
        self.reflection = None

    def __repr__(self):
        return (f"RepairTask({self.skill_name}/{self.issue_type}: "
                f"{self.status}, {self.attempts}/{self.max_attempts})")
