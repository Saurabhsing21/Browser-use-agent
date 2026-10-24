import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_env_is_gitignored():
    lines = (ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in lines


def test_no_key_in_tracked_files():
    out = subprocess.run(
        ["git", "grep", "-n", "sk-or-v1"], cwd=ROOT, capture_output=True, text=True
    )
    assert out.stdout == ""
