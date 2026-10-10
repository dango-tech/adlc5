"""Codex runner adapter contract checks (no host process or network needed)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("runner_hosts", ROOT / "scripts/runner/hosts.py")
hosts = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(hosts)


def main() -> None:
    argv = hosts.command(workspace=Path("/tmp/workspace"), prompt="do work", model=None, effort="low")
    assert "-m" not in argv and "workspace-write" in argv
    events = hosts.parse_events('\n'.join([
        '{"type":"thread.started","thread_id":"session-1"}',
        '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"status\\":\\"completed\\"}"}}',
        '{"type":"turn.completed","usage":{"input_tokens":10,"cached_input_tokens":8,"cache_write_input_tokens":1,"output_tokens":2,"reasoning_output_tokens":1}}',
    ]))
    assert events["session_id"] == "session-1"
    assert events["text"] == '{"status":"completed"}'
    assert events["usage"] == {"input": 10, "cache_read": 8, "cache_creation": 1, "output": 2, "thinking": 1}
    usage_record = hosts.parse_events('{"type":"token_usage_record","payload":{"session_id":"s2","usage":{"input_tokens":31,"cached_input_tokens":16,"cache_write_input_tokens":7,"output_tokens":4,"reasoning_output_tokens":2}}}')
    assert usage_record["usage"] == {"input": 31, "cache_read": 16, "cache_creation": 7, "output": 4, "thinking": 2}
    assert usage_record["session_id"] == "s2"


if __name__ == "__main__":
    main()
    print("runner host checks passed")
