from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path


def test_retire_dev_deploy_keep_venv_skips_uninstall(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "retire_dev_deploy.sh"
    script_copy = repo_root / "scripts" / "retire_dev_deploy.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

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
        env={"HOME": str(tmp_path), "WARCRAFT_LOCAL_BIN_DIR": str(local_bin)},
    )

    assert "Kept repo-local venv" in result.stdout
    assert "No uninstall or archive work was performed." in result.stdout
    assert old_venv.exists()
    assert not pip_marker.exists()
