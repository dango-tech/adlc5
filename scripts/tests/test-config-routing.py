"""Model routing uses explicit user layers and ignores shipped/legacy model IDs."""
import importlib.util
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("model_routing", ROOT / "scripts/lib/model_routing.py")
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(module)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        home = Path(temp) / "home"
        workspace = Path(temp) / "repo"
        workspace.mkdir()
        (workspace / ".adlc5").mkdir()
        with patch.dict(os.environ, {"HOME": str(home)}):
            master = home / ".adlc5/config.yaml"
            master.parent.mkdir(parents=True)
            master.write_text('{"default_host":"codex","persona_mode":{"verifier_different_model":true},"platform_profiles":{"codex":{"execution":{"model":"chosen-model","effort":"low"}}}}')
            configured = module.resolve_model(root=ROOT, tier="execution", platform=None, workspace=workspace)
            assert configured["model_id"] == "chosen-model" and configured["effort"] == "low"
            assert configured["verifier_different_model"] is True
            legacy = workspace / ".adlc5/config.yaml"
            legacy.write_text('{"model_profiles":{"execution":"stale-model"}}')
            ignored = module.resolve_model(root=ROOT, tier="execution", platform="unknown", workspace=workspace)
            assert ignored["model_id"] == "host default" and "Legacy model settings are ignored" in ignored["notice"]
            fast = module.resolve_model(root=ROOT, tier="fast", platform="codex", workspace=workspace)
            assert fast["tier"] == "execution" and "fast tier was removed" in fast["notice"]
            assert ignored["model_id"] == "host default"  # legacy flat IDs never become executable defaults


if __name__ == "__main__":
    main()
    print("config routing checks passed")
