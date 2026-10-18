#!/usr/bin/env python3
"""Disposable install smoke test; never reads the contributor's host config."""
import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
# System Bash where it exists (macOS 3.2 is the floor); Windows has no /bin/bash.
BASH = "/bin/bash" if Path("/bin/bash").is_file() else shutil.which("bash")


def assert_safe_target(clone, env):
    unsafe = clone / "skills" / "missing-parent" / "links"
    configuration = (clone / "config.example.yaml").read_text()
    (clone / "config.yaml").write_text(configuration.replace(
        "claude_skills_target: ~/.claude/skills", f"claude_skills_target: {unsafe}"))
    result = subprocess.run([BASH, str(clone / "scripts/install.sh"),
                             "--platform", "claude", "--skills-only"], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode != 0 and "resolves inside the adlc5 clone" in result.stderr, result
    assert not unsafe.parent.exists(), "installer wrote into its source tree"
    (clone / "config.yaml").unlink()


def main():
    with tempfile.TemporaryDirectory(prefix="adlc5-install-") as temp:
        base = Path(temp)
        clone = base / "distribution"
        shutil.copytree(ROOT, clone, ignore=shutil.ignore_patterns(
            ".git", ".adlc5", ".agent-cache", "__pycache__", "config.yaml"))
        subprocess.run(["git", "init", "-q", str(clone)], check=True)
        # Retain frozen baseline objects and named tags without changing candidate files.
        subprocess.run(["git", "-C", str(clone), "fetch", "-q", "--tags", str(ROOT), "HEAD"], check=True)
        subprocess.run(["git", "-C", str(clone), "symbolic-ref", "HEAD", "refs/heads/install-smoke"], check=True)
        subprocess.run(["git", "-C", str(clone), "update-ref", "refs/heads/install-smoke", "FETCH_HEAD"], check=True)
        baseline = json.loads((clone / "templates/evaluation/cases.json").read_text())["baseline_framework_revision"]
        expected = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", baseline])
        assert subprocess.check_output(["git", "-C", str(clone), "rev-parse", baseline]) == expected
        home = base / "home"
        home.mkdir()
        env = dict(os.environ, HOME=str(home))
        missing = base / "missing-tools"
        missing.mkdir()
        for tool in ("dirname", "git", "python3"):
            # Wrappers, not symlinks: Windows refuses symlinks without Developer Mode.
            wrapper = missing / tool
            wrapper.write_text(f'#!/bin/sh\nexec "{Path(shutil.which(tool)).as_posix()}" "$@"\n')
            wrapper.chmod(0o755)
        for script in ("install.sh", "verify-install.sh"):
            result = subprocess.run([BASH, str(clone / "scripts" / script),
                                     "--platform", "claude"],
                                    env=dict(env, PATH=str(missing)),
                                    capture_output=True, text=True)
            assert result.returncode != 0 and "required tool 'jq'" in result.stderr, result
            assert not (clone / "config.yaml").exists()
            assert not list(home.iterdir())
        subprocess.run([BASH, str(clone / "scripts/install.sh"),
                        "--platform", "claude", "--dry-run"], env=env, check=True,
                       stdout=subprocess.DEVNULL)
        assert not (clone / "config.yaml").exists()
        assert not list(home.iterdir())
        assert_safe_target(clone, env)
        for script in ("install.sh", "verify-install.sh"):
            subprocess.run([BASH, str(clone / "scripts" / script),
                            "--platform", "claude"], env=env, check=True,
                           stdout=subprocess.DEVNULL)
        assert (home / ".claude/skills/adlc5/SKILL.md").is_file()
    print("PASS: isolated install, verification, prerequisite and dry-run contracts")


if __name__ == "__main__":
    main()
