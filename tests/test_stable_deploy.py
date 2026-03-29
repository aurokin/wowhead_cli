from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path


def _init_repo(path: Path, *, branch: str = "master") -> None:
    subprocess.run(["git", "init", "-b", branch], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True, capture_output=True, text=True)
    (path / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True, text=True)


def _write_minimal_package(path: Path) -> None:
    (path / "pyproject.toml").write_text(
        """
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "warcraft-stable-deploy-test"
version = "0.0.0"
        """.strip()
        + "\n",
        encoding="utf-8",
    )


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


def test_stable_deploy_refuses_untracked_files_without_override(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "stable_deploy.sh"
    script_copy = repo_root / "scripts" / "stable_deploy.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    (repo_root / "local-only.txt").write_text("untracked\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(script_copy)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "clean worktree" in result.stderr


def test_stable_deploy_accepts_detected_main_as_stable_branch(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root, branch="main")

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "stable_deploy.sh"
    script_copy = repo_root / "scripts" / "stable_deploy.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    (repo_root / "local-only.txt").write_text("untracked\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(script_copy)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "clean worktree" in result.stderr
    assert "stable branch" not in result.stderr


def test_stable_deploy_allows_unknown_stable_branch_with_override(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root, branch="trunk")
    _write_minimal_package(repo_root)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "stable_deploy.sh"
    script_copy = repo_root / "scripts" / "stable_deploy.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    (repo_root / "local-only.txt").write_text("untracked\n", encoding="utf-8")

    venv_dir = tmp_path / "stable-venv"
    result = subprocess.run(
        [
            "bash",
            str(script_copy),
            "--allow-non-master",
            "--allow-dirty",
            "--no-link-bin",
            "--no-export-skills",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "WARCRAFT_STABLE_VENV_DIR": str(venv_dir),
        },
    )

    assert result.returncode == 0
    assert "Stable deploy complete." in result.stdout


def test_stable_deploy_refuses_ambiguous_local_master_main_without_override(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "checkout", "master"], cwd=repo_root, check=True, capture_output=True, text=True)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "stable_deploy.sh"
    script_copy = repo_root / "scripts" / "stable_deploy.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    result = subprocess.run(
        ["bash", str(script_copy)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Could not determine the stable branch" in result.stderr
