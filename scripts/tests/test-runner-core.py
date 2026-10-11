"""Small deterministic checks for the runner journal and lock contracts."""
import importlib.util
import json
import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("runner_run", ROOT / "scripts/runner/run.py")
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(runner)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        lock = Path(temp) / "runner.lock"
        runner.acquire_lock(lock)
        try:
            try:
                runner.acquire_lock(lock)
            except RuntimeError as exc:
                assert "locked by pid" in str(exc)
            else:
                raise AssertionError("second owner acquired an active lock")
        finally:
            lock.unlink()
        journal = Path(temp) / "attempts.jsonl"
        attempt = {"attempt_id": "a", "step": "implement-1-build", "start_commit": "abc", "number": 1}
        runner.append(journal, attempt)
        runner.record_checkpoint(journal, attempt, "launched")
        assert runner.attempt_event(runner.journal(journal), "a", "launched")
        result = Path(temp) / "result.json"
        result.write_text(json.dumps({"attempt_id": "other", "status": "completed"}))
        assert json.loads(result.read_text())["attempt_id"] != attempt["attempt_id"]


if __name__ == "__main__":
    main()
    print("runner core checks passed")
