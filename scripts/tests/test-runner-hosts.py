"""Supervised host adapter contracts (no host process or network needed)."""
import importlib.util
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("runner_hosts", ROOT / "scripts/runner/hosts.py")
hosts = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(hosts)


def main() -> None:
    workspace = Path("/tmp/workspace")
    argv = hosts.command(host="codex", mode="confined", workspace=workspace, prompt="do work", model=None, effort="low")
    assert "-m" not in argv and "--approve-for-me" in argv and "--sandbox" not in argv
    events = hosts.parse_events("codex", '\n'.join([
        '{"type":"thread.started","thread_id":"session-1"}',
        '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"status\\":\\"completed\\"}"}}',
        '{"type":"turn.completed","usage":{"input_tokens":10,"cached_input_tokens":8,"cache_write_input_tokens":1,"output_tokens":2,"reasoning_output_tokens":1}}',
    ]))
    assert events["session_id"] == "session-1"
    failure = hosts.parse_events('codex', '{"type":"turn.failed","error":{"message":"invalid provider schema"}}')
    assert failure['is_error'] and failure['error']['message'] == 'invalid provider schema'
    assert events["text"] == '{"status":"completed"}'
    # Cached input is a subset of Codex's input_tokens; only the uncached part is recorded as input.
    assert events["usage"] == {"input": 2, "cache_read": 8, "cache_creation": 1, "output": 2, "thinking": 1}
    assert events["observed_token_total"] == 12
    codex_turn = '{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":2}}'
    assert hosts.parse_events("codex", codex_turn + "\n" + codex_turn)["observed_token_total"] is None
    assert hosts.parse_events("codex", '{"type":"turn.completed","usage":{"input_tokens":10}}')["observed_token_total"] is None
    quota = hosts.parse_events("codex", '{"type":"turn.failed","error":{"code":"usage_limit_reached",'
                              '"retry_at":"2099-01-01T00:00:00Z"}}')
    assert quota["quota_limited"] and quota["earliest_retry_at"] == "2099-01-01T00:00:00Z"
    quota_without_time = hosts.parse_events("claude", '{"is_error":true,"error":{"type":"rate_limit_error"}}')
    assert quota_without_time["quota_limited"] and quota_without_time["earliest_retry_at"] is None
    assert "quota_limited" not in failure
    usage_record = hosts.parse_events("codex", '{"type":"token_usage_record","payload":{"session_id":"s2","usage":{"input_tokens":31,"cached_input_tokens":16,"cache_write_input_tokens":7,"output_tokens":4,"reasoning_output_tokens":2}}}')
    assert usage_record["usage"] == {"input": 15, "cache_read": 16, "cache_creation": 7, "output": 4, "thinking": 2}
    assert usage_record["session_id"] == "s2"
    assert usage_record["observed_token_total"] is None
    claude = hosts.command(host="claude", mode="allowlist", workspace=workspace, prompt="work", model="sonnet",
                           effort="low", allowlist=["Bash(pytest)"])
    assert "--permission-mode" in claude and "acceptEdits" in claude and "--allowedTools" in claude
    capped = hosts.command(host="claude", mode="allowlist", workspace=workspace, prompt="work", model="sonnet",
                           effort="low", allowlist=["Bash(pytest)"], max_worker_usd=1.25)
    assert "--max-budget-usd" not in claude
    assert capped == [*claude[:-1], "--max-budget-usd", "1.25", claude[-1]]
    for host, mode in (("codex", "confined"), ("claude", "attended"), ("hermes", "confined")):
        try:
            hosts.command(host=host, mode=mode, workspace=workspace, prompt="work", model=None,
                          effort=None, max_worker_usd=1.25)
        except ValueError as exc:
            assert "requires Claude allowlist" in str(exc)
        else:
            raise AssertionError("unsupported adapter accepted the native USD budget")
    for amount in (0, -1, "1.25", True, float("nan"), float("inf"), 10**1000):
        try:
            hosts.command(host="claude", mode="allowlist", workspace=workspace, prompt="work", model=None,
                          effort=None, max_worker_usd=amount)
        except ValueError as exc:
            assert "positive finite" in str(exc)
        else:
            raise AssertionError(f"adapter accepted invalid budget {amount}")
    cursor = hosts.command(host="cursor", mode="confined", workspace=workspace, prompt="work", model="gpt-5",
                           effort=None)
    assert "--sandbox" in cursor and "enabled" in cursor and "--force" not in cursor and "--trust" in cursor
    # Payload shapes measured from the real CLIs.
    measured = hosts.parse_events("cursor", '{"result":"OK","usage":{"inputTokens":20760,"outputTokens":39,"cacheReadTokens":1152,"cacheWriteTokens":0}}')
    assert measured["usage"] == {"input": 20760, "output": 39, "cache_read": 1152, "cache_creation": 0}
    claude_result = hosts.parse_events("claude", '{"result":"OK","usage":{"input_tokens":10},"modelUsage":{"claude-haiku-4-5-20251001":{"inputTokens":10}}}')
    assert claude_result["model_id"] == "claude-haiku-4-5-20251001"
    assert claude_result["observed_token_total"] is None
    claude_terminal = ('{"type":"result","usage":{"input_tokens":3,"output_tokens":2,'
                       '"cache_creation_input_tokens":4,"cache_read_input_tokens":11}}')
    assert hosts.parse_events("claude", claude_terminal)["observed_token_total"] == 20
    claude_partial = claude_terminal.replace(',"cache_read_input_tokens":11', '')
    assert hosts.parse_events("claude", claude_partial)["observed_token_total"] is None
    for host, mode in (("codex", "confined"), ("claude", "allowlist"), ("cursor", "confined"), ("hermes", "attended")):
        with patch.object(hosts.os, "isatty", return_value=True):
            default_model = hosts.command(host=host, mode=mode, workspace=workspace, prompt="work",
                                          model="host default", effort=None, container_runtime_detected=True)
        assert "--model" not in default_model and "-m" not in default_model
    try:
        hosts.command(host="cursor", mode="confined", workspace=workspace, prompt="work", model="gpt-5-fast", effort=None)
    except ValueError as exc:
        assert "fast" in str(exc)
    else:
        raise AssertionError("Cursor fast models must be rejected")
    parsed = hosts.parse_events("claude", '{"type":"result","result":"{}","model":"sonnet","is_error":true,"permission_denials":[{"tool_name":"Bash"}]}')
    assert parsed["is_error"] and parsed["denied_actions"][0]["tool_name"] == "Bash"
    assert hosts.parse_events("claude", '{"structured_output":{"attempt_id":"a"},"result":"plain"}')['text'] == {"attempt_id": "a"}
    try:
        hosts.command(host="hermes", mode="confined", workspace=workspace, prompt="work", model=None, effort=None)
    except ValueError as exc:
        assert "container" in str(exc)
    else:
        raise AssertionError("Hermes unattended mode must be refused outside a declared container")
    declaration = workspace / ".adlc5/external-sandbox.json"
    declaration.parent.mkdir(parents=True, exist_ok=True)
    declaration.write_text('{"type":"container","declared_by":"user"}')
    assert not hosts.in_declared_container(workspace, runtime_detected=False)
    assert hosts.in_declared_container(workspace, runtime_detected=True)
    hermes = hosts.command(host="hermes", mode="confined", workspace=workspace, prompt="work", model="model-x",
                           effort="low", usage_file=Path("/tmp/usage.json"), container_runtime_detected=True)
    assert "-z" in hermes and "--usage-file" in hermes and "--force" not in hermes
    with patch.object(hosts.os, "isatty", return_value=True):
        attended = hosts.command(host="claude", mode="attended", workspace=workspace, prompt="work",
                                 model="sonnet", effort="low", session_id="attempt-id")
        hermes_attended = hosts.command(host="hermes", mode="attended", workspace=workspace, prompt="work",
                                        model="model-x", effort="low")
    assert "--session-id" in attended and attended[-1] == "work"
    assert "-q" in hermes_attended and "work" in hermes_attended


if __name__ == "__main__":
    main()
    print("runner host checks passed")
