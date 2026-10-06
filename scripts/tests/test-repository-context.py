#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "scripts" / "repository-context.py"
FACADE = ROOT / "scripts" / "adlc5"


class RepositoryContextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp.name)
        (self.workspace / "src").mkdir()
        (self.workspace / "tests").mkdir()
        (self.workspace / "src" / "repository.py").write_text(
            "class CreativeRepository:\n    pass\n", encoding="utf-8"
        )
        (self.workspace / "src" / "creative.py").write_text(
            "from src.repository import CreativeRepository\n\n"
            "class CreativeService:\n"
            "    def create(self):\n"
            "        return CreativeRepository()\n",
            encoding="utf-8",
        )
        (self.workspace / "tests" / "test_creative.py").write_text(
            "from src.creative import CreativeService\n\n"
            "def test_create():\n"
            "    assert CreativeService().create() is not None\n",
            encoding="utf-8",
        )
        (self.workspace / "package.json").write_text(
            json.dumps(
                {
                    "name": "creative-demo",
                    "scripts": {"test": "pytest", "lint": "ruff check ."},
                }
            ),
            encoding="utf-8",
        )
        (self.workspace / ".env").write_text(
            "API_KEY=must-never-appear-in-repository-context\n", encoding="utf-8"
        )
        (self.workspace / "secrets.py").write_text(
            "class MustNeverBeIndexed:\n    pass\n", encoding="utf-8"
        )
        self.git("init", "-q")
        self.git("config", "user.email", "repository-context@test")
        self.git("config", "user.name", "repository-context")
        self.git("add", "src", "tests", "package.json")
        self.git("commit", "-qm", "fixture")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.workspace), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def run_tool(
        self, area: str, action: str, *, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(TOOL),
                area,
                action,
                "--workspace",
                str(self.workspace),
            ],
            check=check,
            capture_output=True,
            text=True,
        )

    def test_repo_spec_init_is_filled_idempotent_and_valid(self) -> None:
        result = self.run_tool("repo-spec", "init")
        self.assertEqual(json.loads(result.stdout)["status"], "ok")

        agent = self.workspace / ".agents"
        expected = {
            agent / "architecture.yaml",
            agent / "boundaries.yaml",
            agent / "commands.yaml",
            agent / "schemas" / "task-spec.schema.json",
        }
        self.assertTrue(all(path.is_file() for path in expected))
        self.assertIn("creative-demo", (agent / "architecture.yaml").read_text())
        self.assertIn("src", (agent / "architecture.yaml").read_text())
        self.assertIn("pytest", (agent / "commands.yaml").read_text())

        validation = self.run_tool("repo-spec", "validate")
        self.assertEqual(json.loads(validation.stdout)["status"], "ok")

        architecture = agent / "architecture.yaml"
        architecture.write_text("schema_version: '1.0'\nstatus: approved\n", encoding="utf-8")
        self.run_tool("repo-spec", "init")
        self.assertEqual(
            architecture.read_text(encoding="utf-8"),
            "schema_version: '1.0'\nstatus: approved\n",
        )

    def test_repo_index_is_deterministic_safe_and_freshness_aware(self) -> None:
        result = self.run_tool("repo-index", "build")
        self.assertEqual(json.loads(result.stdout)["status"], "ok")

        cache = self.workspace / ".agent-cache"
        files = {
            "manifest.json",
            "repo-index.json",
            "module-map.json",
            "symbols.json",
            "dependency-graph.json",
            "test-map.json",
        }
        self.assertEqual(files, {path.name for path in cache.glob("*.json")})
        self.assertIn(".agent-cache/", (self.workspace / ".gitignore").read_text())

        symbols = json.loads((cache / "symbols.json").read_text())
        self.assertTrue(
            any(symbol["name"] == "CreativeService" for symbol in symbols["symbols"])
        )
        dependencies = json.loads((cache / "dependency-graph.json").read_text())
        self.assertTrue(
            any(
                edge["source"] == "src/creative.py"
                and edge["target"] == "src.repository"
                for edge in dependencies["edges"]
            )
        )
        tests = json.loads((cache / "test-map.json").read_text())
        self.assertIn("tests/test_creative.py", tests["by_source"]["src/creative.py"])

        combined = "\n".join(path.read_text() for path in cache.glob("*.json"))
        self.assertNotIn("must-never-appear", combined)
        self.assertNotIn("MustNeverBeIndexed", combined)
        self.assertNotIn("return CreativeRepository", combined)

        before = {path.name: path.read_bytes() for path in cache.glob("*.json")}
        self.run_tool("repo-index", "refresh")
        after = {path.name: path.read_bytes() for path in cache.glob("*.json")}
        self.assertEqual(before, after)

        current = self.run_tool("repo-index", "check")
        self.assertEqual(json.loads(current.stdout)["status"], "ok")

        creative = self.workspace / "src" / "creative.py"
        creative.write_text(
            creative.read_text() + "\nclass CompanionCreative:\n    pass\n",
            encoding="utf-8",
        )
        stale = self.run_tool("repo-index", "check", check=False)
        self.assertNotEqual(stale.returncode, 0)
        self.assertEqual(json.loads(stale.stdout)["status"], "stale")

        self.run_tool("repo-index", "refresh")
        refreshed = json.loads((cache / "symbols.json").read_text())
        self.assertTrue(
            any(symbol["name"] == "CompanionCreative" for symbol in refreshed["symbols"])
        )

        refreshed["symbols"].append(
            {"file": "fake.py", "kind": "class", "line": 1, "name": "Fake", "public": True}
        )
        (cache / "symbols.json").write_text(json.dumps(refreshed), encoding="utf-8")
        tampered = self.run_tool("repo-index", "check", check=False)
        self.assertNotEqual(tampered.returncode, 0)
        self.assertEqual(json.loads(tampered.stdout)["status"], "stale")

        self.run_tool("repo-index", "refresh")
        (cache / "symbols.json").unlink()
        incomplete = self.run_tool("repo-index", "check", check=False)
        self.assertNotEqual(incomplete.returncode, 0)
        self.assertEqual(json.loads(incomplete.stdout)["status"], "stale")

    def test_kernel_and_existing_initializers_provide_repository_context(self) -> None:
        subprocess.run(
            [
                str(ROOT / "scripts" / "init-workspace.sh"),
                "--project",
                str(self.workspace),
                "--no-skills",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertTrue((self.workspace / ".agents" / "architecture.yaml").is_file())
        self.assertTrue((self.workspace / ".agent-cache" / "repo-index.json").is_file())

        spec = subprocess.run(
            [str(FACADE), "repo-spec", "validate", "--workspace", str(self.workspace)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(spec.stdout)["status"], "ok")
        index = subprocess.run(
            [str(FACADE), "repo-index", "check", "--workspace", str(self.workspace)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(index.stdout)["status"], "ok")

        creative = self.workspace / "src" / "creative.py"
        creative.write_text(creative.read_text() + "\n# working change\n", encoding="utf-8")
        subprocess.run(
            [
                str(ROOT / "scripts" / "init-feature.sh"),
                "--feature",
                "repository-context-demo",
                "--workspace",
                str(self.workspace),
                "--mode",
                "brownfield",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        refreshed = subprocess.run(
            [str(FACADE), "repo-index", "check", "--workspace", str(self.workspace)],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(refreshed.stdout)["status"], "ok")

    def test_init_adopts_legacy_agent_and_keeps_existing_agents(self) -> None:
        skills = self.workspace / ".agents" / "skills"
        skills.mkdir(parents=True)
        (skills / "custom-note").write_text("keep-me\n", encoding="utf-8")
        legacy = self.workspace / ".agent"
        (legacy / "schemas").mkdir(parents=True)
        (legacy / "architecture.yaml").write_text(
            "schema_version: '1.0'\nstatus: approved\nsystem:\n  name: legacy\n"
            "architecture:\n  style: hexagonal\nsource_roots:\n  - src\ncomponents: []\n",
            encoding="utf-8",
        )
        (legacy / "boundaries.yaml").write_text(
            "schema_version: '1.0'\nstatus: approved\ndependency_rules: []\ntrust_boundaries: []\n",
            encoding="utf-8",
        )
        (legacy / "commands.yaml").write_text(
            "schema_version: '1.0'\nstatus: approved\ncommands: {}\n",
            encoding="utf-8",
        )
        (legacy / "schemas" / "task-spec.schema.json").write_text("{}\n", encoding="utf-8")
        (legacy / "skills").mkdir()
        (legacy / "skills" / "antigravity").write_text("host-owned\n", encoding="utf-8")

        result = json.loads(self.run_tool("repo-spec", "init").stdout)
        dest = self.workspace / ".agents"
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["constitution_dir"], ".agents")
        self.assertTrue((dest / "architecture.yaml").is_file())
        self.assertIn("legacy", (dest / "architecture.yaml").read_text())
        self.assertEqual((skills / "custom-note").read_text(), "keep-me\n")
        self.assertIn(".agents/skills/", result["kept_existing"])
        self.assertTrue(any(item["from"] == ".agent/architecture.yaml" for item in result["adopted"]))
        self.assertTrue((legacy / "architecture.yaml").is_file())
        self.assertIn(".agent/skills/", result["leftover_legacy_other"])
        self.assertFalse((self.workspace / ".agent" / "architecture.yaml").samefile(dest / "architecture.yaml"))

        again = json.loads(self.run_tool("repo-spec", "init").stdout)
        self.assertEqual((dest / "architecture.yaml").read_text().count("legacy"), 1)
        self.assertTrue(any(item["reason"] == "destination exists" for item in again["skipped_legacy"]))

        report = json.loads(self.run_tool("repo-spec", "reconcile").stdout)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["missing"], [])


if __name__ == "__main__":
    unittest.main()
