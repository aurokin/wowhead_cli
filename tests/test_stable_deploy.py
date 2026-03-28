from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-b", "master"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True, text=True)
    (path / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True, text=True)


def test_stable_deploy_refuses_dirty_worktree_without_override(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "stable_deploy.sh"
    script_copy = repo_root / "scripts" / "stable_deploy.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    (repo_root / "README.md").write_text("dirty\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(script_copy)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "clean worktree" in result.stderr
