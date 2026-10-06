"""Scope parser retains literal filenames and both sides of a staged rename."""
import importlib.util
import subprocess
import tempfile
from pathlib import Path

script = Path(__file__).resolve().parents[1] / 'verify-story.py'
spec = importlib.util.spec_from_file_location('verify_story', script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as temp:
    workspace = Path(temp)
    subprocess.run(['git', 'init', '-q', temp], check=True)
    (workspace / 'source file.txt').write_text('original')
    subprocess.run(['git', '-C', temp, 'add', '.'], check=True)
    subprocess.run(['git', '-C', temp, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'baseline'], check=True)
    (workspace / 'rogue -> app.py').write_text('undeclared')
    (workspace / 'space file.py').write_text('undeclared')
    assert module.changed_files(workspace) == ['rogue -> app.py', 'space file.py']
    subprocess.run(['git', '-C', temp, 'mv', 'source file.txt', 'destination file.txt'], check=True)
    changed = module.changed_files(workspace)
    assert 'source file.txt' in changed and 'destination file.txt' in changed
print('git filename scope checks passed')
