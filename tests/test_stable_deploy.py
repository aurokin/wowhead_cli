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


def _write_fake_stable_venv(path: Path) -> None:
    bin_dir = path / "bin"
    bin_dir.mkdir(parents=True)

    (bin_dir / "python").write_text(
        """#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
  if [[ "${FAKE_BOOTSTRAP_READY:-}" == "1" ]]; then
    exit 0
  fi
  exit 1
fi

if [[ "${1:-}" == "-" ]]; then
  if [[ "${FAKE_BOOTSTRAP_READY:-}" == "1" ]]; then
    cat >/dev/null
    exit 0
  fi
  cat >/dev/null
  exit 1
fi

if [[ "${1:-}" == "-m" && "${2:-}" == "pip" && "${3:-}" == "install" ]]; then
  echo "unexpected bootstrap install" >&2
  exit 97
fi

echo "unexpected python invocation: $*" >&2
exit 98
""",
        encoding="utf-8",
    )
    (bin_dir / "python").chmod(0o755)

    (bin_dir / "pip").write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" > "${FAKE_PIP_LOG:?}"
exit 0
""",
        encoding="utf-8",
    )
    (bin_dir / "pip").chmod(0o755)


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


def test_stable_deploy_skips_bootstrap_upgrade_when_runtime_ready(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    _write_minimal_package(repo_root)
    subprocess.run(["git", "add", "pyproject.toml"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "add-pyproject"], cwd=repo_root, check=True, capture_output=True, text=True)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "stable_deploy.sh"
    script_copy = repo_root / "scripts" / "stable_deploy.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    venv_dir = tmp_path / "stable-venv"
    _write_fake_stable_venv(venv_dir)
    pip_log = tmp_path / "pip.log"

    result = subprocess.run(
        [
            "bash",
            str(script_copy),
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
            "FAKE_BOOTSTRAP_READY": "1",
            "FAKE_PIP_LOG": str(pip_log),
        },
    )

    assert result.returncode == 0
    assert "Stable deploy complete." in result.stdout
    assert "--no-build-isolation --upgrade" in pip_log.read_text(encoding="utf-8")


def test_stable_deploy_uses_versioned_release_layout_by_default(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    _write_minimal_package(repo_root)
    subprocess.run(["git", "add", "pyproject.toml"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "add-pyproject"], cwd=repo_root, check=True, capture_output=True, text=True)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "stable_deploy.sh"
    script_copy = repo_root / "scripts" / "stable_deploy.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    install_root = tmp_path / "stable-root"
    local_bin_dir = tmp_path / "bin"
    result = subprocess.run(
        [
            "bash",
            str(script_copy),
            "--allow-dirty",
            "--no-export-skills",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "WARCRAFT_INSTALL_ROOT": str(install_root),
            "WARCRAFT_LOCAL_BIN_DIR": str(local_bin_dir),
            "WARCRAFT_BIN_NAMES": "warcraft",
            "WARCRAFT_STABLE_RELEASE_ID": "release-one",
        },
    )

    assert result.returncode == 0
    release_root = install_root / "install" / "releases" / "release-one"
    current_link = install_root / "install" / "current"
    wrapper_path = local_bin_dir / "warcraft"

    assert release_root.is_dir()
    assert current_link.is_symlink()
    assert current_link.resolve() == release_root.resolve()
    assert wrapper_path.read_text(encoding="utf-8").strip().endswith(
        f'exec "{current_link}/venv/bin/warcraft" "$@"'
    )


def test_stable_deploy_keeps_old_releases_and_repoints_current(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    _write_minimal_package(repo_root)
    subprocess.run(["git", "add", "pyproject.toml"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "add-pyproject"], cwd=repo_root, check=True, capture_output=True, text=True)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "stable_deploy.sh"
    script_copy = repo_root / "scripts" / "stable_deploy.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    install_root = tmp_path / "stable-root"
    common_env = {
        **os.environ,
        "WARCRAFT_INSTALL_ROOT": str(install_root),
        "WARCRAFT_LOCAL_BIN_DIR": str(tmp_path / "bin"),
        "WARCRAFT_BIN_NAMES": "warcraft",
    }

    first = subprocess.run(
        [
            "bash",
            str(script_copy),
            "--allow-dirty",
            "--no-export-skills",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env={**common_env, "WARCRAFT_STABLE_RELEASE_ID": "release-one"},
    )
    second = subprocess.run(
        [
            "bash",
            str(script_copy),
            "--allow-dirty",
            "--no-export-skills",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env={**common_env, "WARCRAFT_STABLE_RELEASE_ID": "release-two"},
    )

    assert first.returncode == 0
    assert second.returncode == 0
    current_link = install_root / "install" / "current"
    release_one = install_root / "install" / "releases" / "release-one"
    release_two = install_root / "install" / "releases" / "release-two"

    assert release_one.is_dir()
    assert release_two.is_dir()
    assert current_link.is_symlink()
    assert current_link.resolve() == release_two.resolve()
