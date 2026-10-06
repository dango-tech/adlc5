#!/usr/bin/env python3
"""Disposable install smoke test; never reads the contributor's host config."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def assert_safe_target(clone, env):
    unsafe = clone / "skills" / "missing-parent" / "links"
    configuration = (clone / "config.example.yaml").read_text()
    (clone / "config.yaml").write_text(configuration.replace(
        "claude_skills_target: ~/.claude/skills", f"claude_skills_target: {unsafe}"))
    result = subprocess.run(["/bin/bash", str(clone / "scripts/install.sh"),
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
        # Retain the frozen baseline objects without changing copied candidate files.
        subprocess.run(["git", "-C", str(clone), "fetch", "-q", str(ROOT), "HEAD"], check=True)
        subprocess.run(["git", "-C", str(clone), "symbolic-ref", "HEAD", "refs/heads/install-smoke"], check=True)
        subprocess.run(["git", "-C", str(clone), "update-ref", "refs/heads/install-smoke", "FETCH_HEAD"], check=True)
        home = base / "home"
        home.mkdir()
        env = dict(os.environ, HOME=str(home))
        missing = base / "missing-tools"
        missing.mkdir()
        for tool in ("dirname", "git", "python3"):
            (missing / tool).symlink_to(shutil.which(tool))
        for script in ("install.sh", "verify-install.sh"):
            result = subprocess.run(["/bin/bash", str(clone / "scripts" / script),
                                     "--platform", "claude"],
                                    env=dict(env, PATH=str(missing)),
                                    capture_output=True, text=True)
            assert result.returncode != 0 and "required tool 'jq'" in result.stderr, result
            assert not (clone / "config.yaml").exists()
            assert not list(home.iterdir())
        subprocess.run(["/bin/bash", str(clone / "scripts/install.sh"),
                        "--platform", "claude", "--dry-run"], env=env, check=True,
                       stdout=subprocess.DEVNULL)
        assert not (clone / "config.yaml").exists()
        assert not list(home.iterdir())
        assert_safe_target(clone, env)
        for script in ("install.sh", "verify-install.sh"):
            subprocess.run(["/bin/bash", str(clone / "scripts" / script),
                            "--platform", "claude"], env=env, check=True,
                           stdout=subprocess.DEVNULL)
        assert (home / ".claude/skills/adlc5/SKILL.md").is_file()
    print("PASS: isolated install, verification, prerequisite and dry-run contracts")


if __name__ == "__main__":
    main()
