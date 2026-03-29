from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path


def _copy_retire_script(repo_root: Path) -> Path:
    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "retire_dev_deploy.sh"
    script_copy = repo_root / "scripts" / "retire_dev_deploy.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)
    return script_copy


def test_retire_dev_deploy_keep_venv_skips_uninstall(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    script_copy = _copy_retire_script(repo_root)

    pip_marker = repo_root / "pip-invoked.txt"
    old_venv = repo_root / ".venv"
    old_venv_bin = old_venv / "bin"
    old_venv_bin.mkdir(parents=True)
    pip_script = old_venv_bin / "pip"
    pip_script.write_text(
        "#!/usr/bin/env bash\n"
        f"touch {pip_marker}\n",
        encoding="utf-8",
    )
    pip_script.chmod(pip_script.stat().st_mode | stat.S_IXUSR)

    local_bin = tmp_path / "local-bin"
    local_bin.mkdir()

    result = subprocess.run(
        ["bash", str(script_copy), "--keep-venv"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        env=os.environ | {"HOME": str(tmp_path), "WARCRAFT_LOCAL_BIN_DIR": str(local_bin)},
    )

    assert "Kept repo-local venv" in result.stdout
    assert "No uninstall or archive work was performed." in result.stdout
    assert old_venv.exists()
    assert not pip_marker.exists()


def test_retire_dev_deploy_archives_repo_local_venv_by_default(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    script_copy = _copy_retire_script(repo_root)

    old_venv = repo_root / ".venv"
    (old_venv / "bin").mkdir(parents=True)
    pip_script = old_venv / "bin" / "pip"
    pip_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    pip_script.chmod(pip_script.stat().st_mode | stat.S_IXUSR)

    local_bin = tmp_path / "local-bin"
    local_bin.mkdir()

    result = subprocess.run(
        ["bash", str(script_copy)],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        env=os.environ | {"HOME": str(tmp_path), "WARCRAFT_LOCAL_BIN_DIR": str(local_bin)},
    )

    assert "Archived retired repo-local venv" in result.stdout
    assert not old_venv.exists()
    archived = sorted(repo_root.glob(".venv.retired.*"))
    assert len(archived) == 1
    assert archived[0].is_dir()


def test_retire_dev_deploy_can_delete_repo_local_venv(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    script_copy = _copy_retire_script(repo_root)

    old_venv = repo_root / ".venv"
    (old_venv / "bin").mkdir(parents=True)
    pip_script = old_venv / "bin" / "pip"
    pip_script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    pip_script.chmod(pip_script.stat().st_mode | stat.S_IXUSR)

    local_bin = tmp_path / "local-bin"
    local_bin.mkdir()

    result = subprocess.run(
        ["bash", str(script_copy), "--delete-venv"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        env=os.environ | {"HOME": str(tmp_path), "WARCRAFT_LOCAL_BIN_DIR": str(local_bin)},
    )

    assert "Deleted retired repo-local venv" in result.stdout
    assert not old_venv.exists()
    assert not list(repo_root.glob(".venv.retired.*"))
