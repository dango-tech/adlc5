"""Materialize matching worker trees and an operator-only evidence manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
ANCHORS = (
    ".github/workflows/inventory-contract.yml",
    "fixtures/legacy-stock.json",
    "regression.py",
    "reporting.py",
    "reservation_check.py",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="new operator-owned experiment directory")
    args = parser.parse_args()
    try:
        args.directory.mkdir()
    except FileExistsError:
        parser.error("experiment directory already exists")

    for host in ("codex", "claude"):
        worker = args.directory / host
        shutil.copytree(ROOT / "seed", worker, ignore=shutil.ignore_patterns("__pycache__"))
        for filename in ("app.py", "regression.py"):
            shutil.copyfile(ROOT.parent / "consumer" / filename, worker / filename)

    shutil.copytree(ROOT / "operator", args.directory / "operator")
    shutil.copyfile(ROOT / "TASK.md", args.directory / "operator" / "TASK.md")
    seed = args.directory / "codex"
    manifest = {
        "seed_sha256": {
            path.relative_to(seed).as_posix(): sha256(path)
            for path in sorted(seed.rglob("*"))
            if path.is_file()
        },
        "anchor_paths": ANCHORS,
        "operator_sha256": {
            path.name: sha256(path)
            for path in sorted((args.directory / "operator").iterdir())
            if path.is_file()
        },
    }
    (args.directory / "operator" / "fixture.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
