"""Regression checks for pilot metadata initialization and wall-clock start."""
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check(existing: bool) -> None:
    with tempfile.TemporaryDirectory() as temp:
        workspace = Path(temp)
        feature_dir = workspace / ".adlc5/demo/pilot"
        feature_dir.mkdir(parents=True)
        meta = feature_dir / "meta.json"
        if existing:
            meta.write_text('{"run_id":"prior","iteration_count":0}')
        proc = subprocess.run(
            ["bash", str(ROOT / "scripts/pilot-autopilot.sh"), "--feature", "demo", "--workspace", str(workspace)],
            capture_output=True, text=True, check=False,
        )
        assert proc.returncode == 2 and "state.json missing" in proc.stdout
        data = json.loads(meta.read_text())
        assert data.get("started_at"), data


if __name__ == "__main__":
    check(False)
    check(True)
    print("pilot metadata checks passed")
