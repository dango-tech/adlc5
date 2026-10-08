#!/usr/bin/env python3
"""Claude Code plugin package contract: archive, MCP stdio, bootstrap, hooks, relocation.

Everything runs against the *built archive extracted outside the source clone* plus
disposable consumer repositories. Live Claude sessions are qualified separately.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parents[2]
BASH = "/bin/bash" if Path("/bin/bash").exists() else "bash"


def run(cmd, cwd=None, env=None, stdin=None, check=False):
    base = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "ADLC5"))}
    base.update(env or {})
    return subprocess.run(cmd, cwd=cwd, env=base, input=stdin, capture_output=True, text=True, timeout=120, check=check)


def tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if "__pycache__" in p.parts:
            continue
        h.update(str(p.relative_to(root)).encode())
        if p.is_file():  # directories count too: a stray mkdir inside the package is a write
            h.update(p.read_bytes())
    return h.hexdigest()


def git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q", str(path)], check=True)
    run(["git", "-C", str(path), "config", "user.email", "t@example.com"], check=True)
    run(["git", "-C", str(path), "config", "user.name", "t"], check=True)
    return path


class PluginTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="adlc5-claude-plugin-")).resolve()  # macOS /var -> /private/var
        cls.dist = cls.tmp / "dist"
        out = run([sys.executable, str(SRC / "scripts/package-plugin.py"), "--out", str(cls.dist)], check=True)
        cls.info = json.loads(out.stdout)
        # Install location with spaces, like a real package cache path.
        cls.pkg = cls.tmp / "cache dir" / "adlc5" / cls.info["version"]
        cls.pkg.parent.mkdir(parents=True)
        with tarfile.open(cls.info["tar"]) as tar:
            tar.extractall(cls.tmp / "x", **({"filter": "data"} if hasattr(tarfile, "data_filter") else {}))
        shutil.move(str(cls.tmp / "x" / f"adlc5-{cls.info['version']}"), cls.pkg)
        cls.pkg_digest = tree_digest(cls.pkg)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def consumer(self, name="consumer repo") -> Path:
        return git_repo(self.tmp / f"{name}-{len(list(self.tmp.iterdir()))}")

    # --- package -----------------------------------------------------------

    def test_versions_agree(self):
        version = (SRC / "core/VERSION").read_text().strip()
        for rel in (".claude-plugin/plugin.json", ".cursor-plugin/plugin.json", "platform/codex-plugin/plugin.json"):
            self.assertEqual(json.loads((SRC / rel).read_text())["version"], version, rel)
        self.assertIn(f'framework_version: "{version}"', (SRC / "core/skill-registry.yaml").read_text())

    def test_archive_contents_and_modes(self):
        names = {p.relative_to(self.pkg).as_posix() for p in self.pkg.rglob("*") if p.is_file()}
        for required in ("bin/adlc5", "bin/adlc5-run", "hooks/claude.json", ".mcp.json", "scripts/adlc5-mcp.py",
                         "skills/implement/SKILL.md", "skills/adlc5-setup/SKILL.md", "core/gates.yaml", ".adlc5-package.json"):
            self.assertIn(required, names)
        for banned in ("CLAUDE.md", "AGENTS.md", "config.yaml", ".gitignore"):
            self.assertNotIn(banned, names)
        for name in names:
            self.assertFalse(name.startswith((".git/", ".adlc5/", ".agents/", ".agent-cache/", "docs/plans/", "dogfood/", "scripts/tests/")), name)
        for exe in ("bin/adlc5", "bin/adlc5-run", "scripts/adlc5", "scripts/init-workspace.sh", ".claude/hooks/engagement-gate.sh"):
            self.assertTrue(os.access(self.pkg / exe, os.X_OK), exe)
        self.assertFalse([p for p in self.pkg.rglob("*") if p.is_symlink()])

    def test_archive_is_deterministic_and_zip_matches(self):
        second = self.tmp / "dist2"
        info = json.loads(run([sys.executable, str(SRC / "scripts/package-plugin.py"), "--out", str(second)], check=True).stdout)
        for key in ("tar", "zip"):
            self.assertEqual(Path(self.info[key]).read_bytes(), Path(info[key]).read_bytes(), key)
        with zipfile.ZipFile(self.info["zip"]) as z:
            self.assertEqual(len(z.namelist()), self.info["files"])
            self.assertIn(".claude-plugin/plugin.json", z.namelist())

    def test_packager_refuses_output_inside_source_tree(self):
        r = run([sys.executable, str(SRC / "scripts/package-plugin.py"), "--out", str(SRC / "dist")])
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((SRC / "dist").exists())

    def test_skill_identity_comes_from_frontmatter(self):
        text = (self.pkg / "skills/implement/SKILL.md").read_text()
        self.assertIn("name: adlc5-implement", text)

    def test_hooks_file_shape(self):
        data = json.loads((self.pkg / "hooks/claude.json").read_text())
        self.assertEqual(set(data["hooks"]), {"SessionStart", "UserPromptSubmit", "PreToolUse", "Stop"})
        raw = (self.pkg / "hooks/claude.json").read_text()
        self.assertNotIn("CLAUDE_PROJECT_DIR", raw)  # runtime comes from the package, not the workspace
        self.assertFalse((self.pkg / "hooks/hooks.json").exists())  # nothing auto-discovered besides claude.json

    # --- kernel / bin ------------------------------------------------------

    def test_bin_runs_from_spaced_path_and_symlink(self):
        link = self.tmp / "linked adlc5"
        link.symlink_to(self.pkg / "bin/adlc5")
        for exe in (self.pkg / "bin/adlc5", link):
            r = run([str(exe), "version"], cwd=self.tmp)
            self.assertEqual(r.stdout.strip(), f"adlc5 {self.info['version']}", r.stderr)

    def test_kernel_targets_consumer_cwd_not_package(self):
        repo = self.consumer()
        adlc5 = str(self.pkg / "bin/adlc5")
        run([BASH, str(self.pkg / "scripts/init-feature.sh"), "--feature", "demo", "--workspace", str(repo)], check=True)
        gate = run([adlc5, "gate", "--feature", "demo", "--gate", "specify-complete", "--workspace", "."], cwd=repo)
        self.assertNotIn("delivery state missing", gate.stdout)  # relative workspace resolved against the consumer
        state = run([adlc5, "state", "get", "--feature", "demo", "--workspace", "."], cwd=repo)
        self.assertEqual(json.loads(state.stdout)["feature"], "demo")
        self.assertEqual(tree_digest(self.pkg), self.pkg_digest, "package contents changed")

    def test_workspace_inside_package_or_missing_is_rejected(self):
        adlc5 = str(self.pkg / "bin/adlc5")
        for bad in (str(self.pkg), str(self.pkg / "core"), str(self.tmp / "does-not-exist")):
            r = run([adlc5, "state", "get", "--feature", "x", "--workspace", bad], cwd=self.tmp)
            self.assertEqual(r.returncode, 2, bad)
        r = run([adlc5, "state", "get", "--feature", "x"], cwd=self.pkg)  # default workspace = cwd = package
        self.assertEqual(r.returncode, 2)
        self.assertEqual(run([BASH, str(self.pkg / "scripts/init-feature.sh"), "--feature", "x", "--workspace", str(self.pkg)]).returncode, 2)
        self.assertEqual(run([BASH, str(self.pkg / "scripts/init-workspace.sh"), "--project", str(self.pkg / "sub")]).returncode, 1)
        self.assertEqual(run([BASH, str(self.pkg / "scripts/plugin-setup.sh"), "--project", str(self.pkg)]).returncode, 2)
        self.assertEqual(tree_digest(self.pkg), self.pkg_digest)

    def test_symlinked_package_or_project_path_cannot_bypass_the_guard(self):
        via_link = self.tmp / "pkg-link"
        via_link.symlink_to(self.pkg)
        before = tree_digest(self.pkg)
        targets = (via_link / "sub", self.pkg / "sub")  # project reached through the link and physically
        for exe, extra in (("scripts/init-workspace.sh", "--project"), ("scripts/init-feature.sh", "--workspace")):
            for target in targets:
                for root in (via_link, self.pkg):  # package invoked through the link and physically
                    r = run([BASH, str(root / exe), extra, str(target)] + (["--feature", "x"] if "feature" in exe else []))
                    self.assertNotEqual(r.returncode, 0, (exe, root, target))
        self.assertEqual(run([BASH, str(via_link / "scripts/plugin-setup.sh"), "--project", str(self.pkg)]).returncode, 2)
        self.assertEqual(tree_digest(self.pkg), before, "a refused call still wrote into the package")
        self.assertFalse((self.pkg / "sub").exists())

    def test_adlc5_run_launcher(self):
        run_sh = str(self.pkg / "bin/adlc5-run")
        self.assertEqual(run([run_sh, "resolve-model.sh", "--help"]).returncode, 0)
        self.assertEqual(run([run_sh, "../etc/passwd"]).returncode, 2)
        self.assertEqual(run([run_sh, "nope.sh"]).returncode, 2)

    # --- MCP ---------------------------------------------------------------

    def mcp(self, messages, cwd=None, env=None, raw=False):
        payload = "\n".join(m if isinstance(m, str) else json.dumps(m) for m in messages) + "\n"
        r = run([sys.executable, str(self.pkg / "scripts/adlc5-mcp.py")], cwd=cwd, env=env, stdin=payload)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = [json.loads(line) for line in r.stdout.splitlines()]  # stdout must be protocol-only
        return lines

    def test_mcp_stdio_handshake_and_calls_on_one_process(self):
        repo = self.consumer()
        run([BASH, str(self.pkg / "scripts/init-feature.sh"), "--feature", "demo", "--workspace", str(repo)], check=True)
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}
        replies = self.mcp([
            init,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "adlc5_version", "arguments": {}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "adlc5_state_get", "arguments": {"feature": "demo"}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "adlc5_state_get", "arguments": {"feature": "demo", "workspace": str(repo)}}},
            {"jsonrpc": "2.0", "id": 6, "method": "ping"},
        ], cwd=repo)
        by_id = {r["id"]: r for r in replies}
        self.assertEqual(len(replies), 6)  # the notification gets no reply
        self.assertEqual(by_id[1]["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(by_id[1]["result"]["serverInfo"]["version"], self.info["version"])
        self.assertEqual(len(by_id[2]["result"]["tools"]), 13)
        call = json.loads(by_id[3]["result"]["content"][0]["text"])
        self.assertEqual(call["stdout"].strip(), f"adlc5 {self.info['version']}")
        cli = run([str(self.pkg / "bin/adlc5"), "state", "get", "--feature", "demo", "--workspace", str(repo)])
        for rid in (4, 5):  # default workspace (server cwd) and explicit workspace both match the CLI
            result = by_id[rid]["result"]
            self.assertFalse(result["isError"])
            self.assertEqual(json.loads(json.loads(result["content"][0]["text"])["stdout"]), json.loads(cli.stdout))
        self.assertEqual(by_id[6]["result"], {})
        self.assertEqual(tree_digest(self.pkg), self.pkg_digest)

    def test_mcp_negative_cases_keep_server_alive(self):
        repo = self.consumer()
        call = lambda i, name, args: {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args}}
        replies = self.mcp([
            "not json",
            {"jsonrpc": "2.0", "id": 1, "method": "no/such"},
            call(2, "no_such_tool", {}),
            call(3, "adlc5_gate", {}),                                   # missing required
            call(4, "adlc5_gate", {"feature": "x", "bogus": 1}),         # unknown argument
            call(5, "adlc5_gate", {"feature": 7}),                       # wrong type
            call(6, "adlc5_gate", {"feature": "../escape"}),             # unsafe feature label
            call(7, "adlc5_evidence", {"feature": "x", "action": "rm"}),  # enum
            call(8, "adlc5_state_get", {"feature": "x", "workspace": str(self.pkg)}),   # inside package
            call(9, "adlc5_state_get", {"feature": "x", "workspace": str(self.tmp / "missing")}),
            {"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "adlc5_version", "arguments": []}},
            {"jsonrpc": "2.0", "id": 11, "method": "ping"},
        ], cwd=repo)
        by_id = {r.get("id"): r for r in replies}
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertEqual(by_id[1]["error"]["code"], -32601)
        self.assertEqual(by_id[2]["error"]["code"], -32602)
        for rid in (3, 4, 5, 6, 7, 8, 9):
            self.assertTrue(by_id[rid]["result"]["isError"], rid)
        self.assertEqual(by_id[10]["error"]["code"], -32602)
        self.assertEqual(by_id[11]["result"], {})
        self.assertFalse((repo / ".adlc5").exists())
        self.assertEqual(tree_digest(self.pkg), self.pkg_digest)

    def test_mcp_relative_file_argument_resolves_against_workspace(self):
        repo = self.consumer()
        (repo / "spec.md").write_text("# Spec\n\nWhat: a thing.\n")
        replies = self.mcp([{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                             "params": {"name": "adlc5_clarity", "arguments": {"file_path": "spec.md"}}}], cwd=repo)
        out = json.loads(replies[0]["result"]["content"][0]["text"])
        self.assertNotIn("No such file", out["stderr"] + out["stdout"])
        self.assertEqual(out["exit_code"], 0, out)

    def test_mcp_children_cannot_read_the_protocol_stream(self):
        # A fake kernel that drains stdin: if the server let children inherit its stdin,
        # it would swallow queued protocol messages.
        fake = self.tmp / "fake-kernel.py"
        fake.write_text("import sys; print(len(sys.stdin.read()))\n")
        probe = (
            "import importlib.util, sys; from pathlib import Path\n"
            f"spec = importlib.util.spec_from_file_location('mcp', {str(self.pkg / 'scripts/adlc5-mcp.py')!r})\n"
            "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)\n"
            f"mod.ADLC5 = Path({str(fake)!r})\n"
            f"print(mod.invoke_adlc5(['x'], cwd=Path({str(self.tmp)!r}))['stdout'].strip())\n"
        )
        r = run([sys.executable, "-c", probe], stdin="queued protocol bytes")
        self.assertEqual(r.stdout.strip(), "0", r.stderr)

    # --- bootstrap ---------------------------------------------------------

    def setup_script(self, repo, *args, env=None):
        return run([BASH, str(self.pkg / "scripts/plugin-setup.sh"), "--project", str(repo), *args], env=env)

    def test_setup_fresh_repeat_and_customized(self):
        repo = self.consumer()
        check = self.setup_script(repo, "--check")
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertFalse((repo / ".adlc5").exists(), "--check must not write")
        first = self.setup_script(repo)
        self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
        for rel in (".adlc5/workspace.json", ".adlc5/config.yaml", "AGENTS.md", ".agents/architecture.yaml"):
            self.assertTrue((repo / rel).exists(), rel)
        self.assertFalse((repo / ".cursor").exists(), "Claude setup must not scaffold Cursor artifacts")
        self.assertFalse((repo / ".agents/skills").exists(), "plugin setup must not link skills")
        binding = json.loads((repo / ".adlc5/workspace.json").read_text())
        self.assertEqual(Path(binding["adlc5_root"]).resolve(), self.pkg.resolve())
        # customize, add feature state, repeat
        (repo / "AGENTS.md").write_text("# mine\n")
        cfg = repo / ".adlc5/config.yaml"
        cfg.write_text(cfg.read_text() + "\nmy_custom_key: keep-me\n")
        run([BASH, str(self.pkg / "scripts/init-feature.sh"), "--feature", "demo", "--workspace", str(repo)], check=True)
        state_before = (repo / ".adlc5/demo/state.json").read_text()
        again = self.setup_script(repo)
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual((repo / "AGENTS.md").read_text(), "# mine\n")
        self.assertIn("my_custom_key: keep-me", cfg.read_text())
        self.assertEqual((repo / ".adlc5/demo/state.json").read_text(), state_before)
        self.assertEqual(tree_digest(self.pkg), self.pkg_digest)

    def test_setup_reports_missing_prerequisite(self):
        repo = self.consumer()
        bindir = self.tmp / "nojq-bin"
        bindir.mkdir(exist_ok=True)
        for tool in ("git", "python3", "dirname", "tr", "cat", "sed", "env"):
            found = shutil.which(tool)
            if found and not (bindir / tool).exists():
                (bindir / tool).symlink_to(found)
        r = run([BASH, str(self.pkg / "scripts/plugin-setup.sh"), "--project", str(repo), "--check"], env={"PATH": str(bindir)})
        self.assertEqual(r.returncode, 1)
        self.assertIn("jq", r.stderr)

    def test_setup_detects_classic_duplicates_without_deleting(self):
        repo = self.consumer()
        home = self.tmp / "home-dup"
        (home / ".claude/skills").mkdir(parents=True)
        (home / ".claude/skills/adlc5-specify").symlink_to(SRC / "skills/specify")
        (repo / ".claude").mkdir()
        settings = repo / ".claude/settings.json"
        settings.write_text(json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "x/claude-usage.sh stop"}]}]}}))
        r = self.setup_script(repo, "--check", env={"HOME": str(home)})
        self.assertIn("DUPLICATE (hooks)", r.stdout)
        self.assertIn("DUPLICATE (skills)", r.stdout)
        self.assertTrue(settings.exists() and (home / ".claude/skills/adlc5-specify").is_symlink())

    def test_linked_worktree_shares_static_layer_but_not_feature_state(self):
        main = self.consumer("wt-main")
        (main / "f.txt").write_text("x")
        run(["git", "-C", str(main), "add", "."], check=True)
        run(["git", "-C", str(main), "commit", "-qm", "init"], check=True)
        wt = self.tmp / "wt-linked"
        run(["git", "-C", str(main), "worktree", "add", "-q", str(wt)], check=True)
        self.assertEqual(self.setup_script(main).returncode, 0)
        r = self.setup_script(wt)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((wt / ".adlc5/config.yaml").is_symlink(), "static config shared via common git dir")
        run([BASH, str(self.pkg / "scripts/init-feature.sh"), "--feature", "only-here", "--workspace", str(wt)], check=True)
        self.assertTrue((wt / ".adlc5/only-here/state.json").exists())
        self.assertFalse((main / ".adlc5/only-here").exists(), "feature state is per worktree")

    def test_relocated_package_rebinds_only_the_runtime_path(self):
        repo = self.consumer()
        old = self.tmp / "cache-old" / "adlc5" / "4.0.9"
        shutil.copytree(self.pkg, old)
        run([BASH, str(old / "scripts/plugin-setup.sh"), "--project", str(repo)], check=True)
        cfg = repo / ".adlc5/config.yaml"
        cfg.write_text(cfg.read_text() + "my_custom_key: keep-me\n")
        shutil.rmtree(old)  # plugin cache cleaned up after the update
        r = self.setup_script(repo)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(Path(json.loads((repo / ".adlc5/workspace.json").read_text())["adlc5_root"]).resolve(), self.pkg.resolve())
        text = cfg.read_text()
        self.assertIn(f"adlc5_root: {self.pkg}", text.replace("'", "").replace('"', ""))
        self.assertIn("my_custom_key: keep-me", text)

    def test_two_hosts_with_different_roots_do_not_rebind_each_other(self):
        repo = self.consumer()
        other = self.tmp / "other host cache" / "adlc5"
        shutil.copytree(self.pkg, other)
        run([BASH, str(other / "scripts/plugin-setup.sh"), "--project", str(repo)], check=True)
        before = (repo / ".adlc5/workspace.json").read_text()
        self.assertEqual(self.setup_script(repo).returncode, 0)  # a second host's setup
        self.assertEqual((repo / ".adlc5/workspace.json").read_text(), before)

    def test_uninstall_preserves_consumer_state(self):
        repo = self.consumer()
        pkg2 = self.tmp / "ephemeral" / "adlc5"
        shutil.copytree(self.pkg, pkg2)
        run([BASH, str(pkg2 / "scripts/plugin-setup.sh"), "--project", str(repo)], check=True)
        run([BASH, str(pkg2 / "scripts/init-feature.sh"), "--feature", "demo", "--workspace", str(repo)], check=True)
        before = tree_digest(repo / ".adlc5")
        shutil.rmtree(pkg2)
        self.assertEqual(tree_digest(repo / ".adlc5"), before)

    def test_init_workspace_classic_defaults_unchanged(self):
        repo = self.consumer()
        r = run([BASH, str(SRC / "scripts/init-workspace.sh"), "--project", str(repo), "--no-skills"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((repo / ".cursor/agents").is_dir(), "classic init still installs council agents by default")

    # --- hooks -------------------------------------------------------------

    def hook(self, script, env, payload, args=()):
        return run([BASH, str(self.pkg / ".claude/hooks" / script), *args], env=env, stdin=json.dumps(payload))

    def test_session_start_hook_reports_runtime_and_exports_root(self):
        repo = self.consumer()
        envfile = self.tmp / "claude-env"
        r = run([sys.executable, str(self.pkg / "scripts/plugin-session-start.py")],
                env={"CLAUDE_PROJECT_DIR": str(repo), "CLAUDE_ENV_FILE": str(envfile)}, stdin=json.dumps({"cwd": str(repo)}))
        out = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(out["hookEventName"], "SessionStart")
        self.assertIn(str(self.pkg), out["additionalContext"])
        self.assertIn("adlc5-setup", out["additionalContext"])  # uninitialized repo pointer
        self.assertIn("ADLC5_ROOT=", envfile.read_text())
        self.assertIn("'", envfile.read_text())  # path with a space is shell-quoted

    def touch_and_gate(self, repo, env, session, count=4):
        last = None
        for i in range(count):
            f = repo / "src" / f"{session}-{i}.py"
            f.parent.mkdir(exist_ok=True)
            f.write_text("x = 1\n")
            last = self.hook("engagement-gate.sh", env, {"session_id": session, "cwd": str(repo), "tool_name": "Write",
                                                         "tool_input": {"file_path": str(f)}}, ("pre-tool-use",))
            self.assertEqual(last.returncode, 0)
        return json.loads(last.stdout)

    def test_engagement_hook_uses_plugin_runtime_and_warns_without_granting_permission(self):
        repo = self.consumer()
        self.setup_script(repo)
        env = {"CLAUDE_PROJECT_DIR": str(repo), "CLAUDE_PLUGIN_ROOT": str(self.pkg), "HOME": str(self.tmp / "home-gate")}
        quiet = self.touch_and_gate(repo, env, "s-quiet", count=2)
        self.assertEqual(quiet, {})  # below threshold: no output at all
        out = self.touch_and_gate(repo, env, "s-warn")["hookSpecificOutput"]
        self.assertIn("ADLC5", out["additionalContext"])
        self.assertNotIn("permissionDecision", out)  # warn must not bypass the user's permission prompt
        denied = self.touch_and_gate(repo, {**env, "ADLC5_ENGAGEMENT_GATE": "enforce"}, "s-enforce")["hookSpecificOutput"]
        self.assertEqual(denied["permissionDecision"], "deny")
        off = self.touch_and_gate(repo, {**env, "ADLC5_ENGAGEMENT_GATE": "off"}, "s-off")
        self.assertEqual(off, {})

    def test_hook_runtime_selection_prefers_plugin_root_over_stale_binding(self):
        repo = self.consumer()
        self.setup_script(repo)
        ws = repo / ".adlc5/workspace.json"
        data = json.loads(ws.read_text())
        data["adlc5_root"] = str(self.tmp / "obsolete-cache")  # stale binding
        ws.write_text(json.dumps(data))
        probe = f'source "{self.pkg}/.claude/hooks/_adlc5-root.sh"; adlc5_resolve_root "{repo}"'
        with_env = run([BASH, "-c", probe], env={"CLAUDE_PLUGIN_ROOT": str(self.pkg)})
        self.assertEqual(with_env.stdout, str(self.pkg))
        classic = run([BASH, "-c", probe])  # no plugin env: classic wrapper falls back to the binding
        self.assertEqual(classic.stdout, str(self.tmp / "obsolete-cache"))

    def test_usage_hook_binds_feature_with_plugin_runtime(self):
        repo = self.consumer()
        self.setup_script(repo)
        run([BASH, str(self.pkg / "scripts/init-feature.sh"), "--feature", "demo", "--workspace", str(repo)], check=True)
        env = {"CLAUDE_PROJECT_DIR": str(repo), "CLAUDE_PLUGIN_ROOT": str(self.pkg), "HOME": str(self.tmp / "home-usage")}
        r = self.hook("claude-usage.sh", env, {"session_id": "s1", "cwd": str(repo), "prompt": "@adlc5 for demo"}, ("user-prompt-submit",))
        self.assertEqual(r.returncode, 0)
        bindings = list((repo / ".adlc5").rglob("claude-usage-bindings.jsonl"))
        self.assertTrue(bindings, "usage hook did not record a binding via the plugin runtime")
        self.assertIn('"demo"', bindings[0].read_text())
        # Without a plugin root or workspace binding the wrapper fails open and records nothing new.
        bare = self.consumer()
        self.assertEqual(self.hook("claude-usage.sh", {"CLAUDE_PROJECT_DIR": str(bare)}, {"session_id": "s", "prompt": "x"}, ("stop",)).returncode, 0)

    # --- Claude CLI validator (when installed) -----------------------------

    @unittest.skipUnless(shutil.which("claude"), "claude CLI not installed")
    def test_claude_validator_accepts_the_package(self):
        r = run(["claude", "plugin", "validate", str(self.pkg)])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Validation failed", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=1)
