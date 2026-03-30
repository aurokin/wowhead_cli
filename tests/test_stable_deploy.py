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


def _copy_stable_script(script_name: str, repo_root: Path) -> Path:
    repo_script = Path(__file__).resolve().parent.parent / "scripts" / script_name
    script_copy = repo_root / "scripts" / script_name
    script_copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)
    return script_copy


def test_stable_deploy_refuses_dirty_worktree_without_override(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    script_copy = _copy_stable_script("stable_deploy.sh", repo_root)

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

    script_copy = _copy_stable_script("stable_deploy.sh", repo_root)

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

    script_copy = _copy_stable_script("stable_deploy.sh", repo_root)

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

    script_copy = _copy_stable_script("stable_deploy.sh", repo_root)

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

    script_copy = _copy_stable_script("stable_deploy.sh", repo_root)

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

    script_copy = _copy_stable_script("stable_deploy.sh", repo_root)

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


def test_stable_deploy_rejects_invalid_release_ids(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    _write_minimal_package(repo_root)
    subprocess.run(["git", "add", "pyproject.toml"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "add-pyproject"], cwd=repo_root, check=True, capture_output=True, text=True)

    script_copy = _copy_stable_script("stable_deploy.sh", repo_root)

    install_root = tmp_path / "stable-root"
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
            "WARCRAFT_INSTALL_ROOT": str(install_root),
            "WARCRAFT_STABLE_RELEASE_ID": "../outside",
        },
    )

    assert result.returncode == 2
    assert "Invalid stable release id" in result.stderr
    assert not (install_root / "install" / "releases").exists()


def test_stable_deploy_rejected_preflight_does_not_leave_tmp_release_dir(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=repo_root, check=True, capture_output=True, text=True)
    _write_minimal_package(repo_root)
    subprocess.run(["git", "add", "pyproject.toml"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "add-pyproject"], cwd=repo_root, check=True, capture_output=True, text=True)

    script_copy = _copy_stable_script("stable_deploy.sh", repo_root)

    install_root = tmp_path / "stable-root"
    result = subprocess.run(
        ["bash", str(script_copy)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "WARCRAFT_INSTALL_ROOT": str(install_root)},
    )

    assert result.returncode == 1
    assert "Stable deploys must run from the stable branch" in result.stderr
    releases_dir = install_root / "install" / "releases"
    assert not releases_dir.exists() or not list(releases_dir.glob(".tmp-*"))


def test_stable_deploy_failed_install_cleans_tmp_release_dir(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    _write_minimal_package(repo_root)
    subprocess.run(["git", "add", "pyproject.toml"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "add-pyproject"], cwd=repo_root, check=True, capture_output=True, text=True)

    script_copy = _copy_stable_script("stable_deploy.sh", repo_root)

    install_root = tmp_path / "stable-root"
    result = subprocess.run(
        [
            "bash",
            str(script_copy),
            "--allow-dirty",
            "--no-link-bin",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "WARCRAFT_INSTALL_ROOT": str(install_root),
            "WARCRAFT_STABLE_RELEASE_ID": "release-fail",
        },
    )

    assert result.returncode == 2
    releases_dir = install_root / "install" / "releases"
    assert not list(releases_dir.glob(".tmp-release-fail-*"))
    assert not (releases_dir / "release-fail").exists()


def test_stable_rollback_repoints_current_to_an_older_release(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    script_copy = _copy_stable_script("stable_rollback.sh", repo_root)

    install_root = tmp_path / "stable-root"
    releases_dir = install_root / "install" / "releases"
    old_release = releases_dir / "20260329010101-old1111"
    new_release = releases_dir / "20260329020202-new2222"
    (old_release / "venv").mkdir(parents=True)
    (new_release / "venv").mkdir(parents=True)

    current_link = install_root / "install" / "current"
    current_link.parent.mkdir(parents=True, exist_ok=True)
    current_link.symlink_to(new_release)

    result = subprocess.run(
        ["bash", str(script_copy), old_release.name],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        env=os.environ | {"WARCRAFT_INSTALL_ROOT": str(install_root)},
    )

    assert "Stable rollback complete." in result.stdout
    assert current_link.is_symlink()
    assert current_link.resolve() == old_release.resolve()


def test_stable_rollback_lists_known_releases_when_target_is_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    script_copy = _copy_stable_script("stable_rollback.sh", repo_root)

    install_root = tmp_path / "stable-root"
    releases_dir = install_root / "install" / "releases"
    known_release = releases_dir / "20260329030303-known3333"
    (known_release / "venv").mkdir(parents=True)

    result = subprocess.run(
        ["bash", str(script_copy), "missing-release"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env=os.environ | {"WARCRAFT_INSTALL_ROOT": str(install_root)},
    )

    assert result.returncode == 1
    assert "Stable release not found" in result.stderr
    assert known_release.name in result.stderr


def test_stable_rollback_rejects_invalid_release_ids(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    script_copy = _copy_stable_script("stable_rollback.sh", repo_root)

    install_root = tmp_path / "stable-root"
    releases_dir = install_root / "install" / "releases"
    valid_release = releases_dir / "20260329040404-known4444"
    outside_release = install_root / "install" / "outside"
    (valid_release / "venv").mkdir(parents=True)
    (outside_release / "venv").mkdir(parents=True)

    current_link = install_root / "install" / "current"
    current_link.parent.mkdir(parents=True, exist_ok=True)
    current_link.symlink_to(valid_release)

    result = subprocess.run(
        ["bash", str(script_copy), "../outside"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env=os.environ | {"WARCRAFT_INSTALL_ROOT": str(install_root)},
    )

    assert result.returncode == 2
    assert "Invalid stable release id" in result.stderr
    assert current_link.resolve() == valid_release.resolve()


def test_stable_rollback_rejects_release_paths_that_resolve_outside_releases_dir(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    script_copy = _copy_stable_script("stable_rollback.sh", repo_root)

    install_root = tmp_path / "stable-root"
    releases_dir = install_root / "install" / "releases"
    current_release = releases_dir / "20260329050505-current5555"
    outside_release = install_root / "outside-release"
    (current_release / "venv").mkdir(parents=True)
    (outside_release / "venv").mkdir(parents=True)
    (releases_dir / "20260329060606-symlink6666").parent.mkdir(parents=True, exist_ok=True)
    (releases_dir / "20260329060606-symlink6666").symlink_to(outside_release, target_is_directory=True)

    current_link = install_root / "install" / "current"
    current_link.parent.mkdir(parents=True, exist_ok=True)
    current_link.symlink_to(current_release)

    result = subprocess.run(
        ["bash", str(script_copy), "20260329060606-symlink6666"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env=os.environ | {"WARCRAFT_INSTALL_ROOT": str(install_root)},
    )

    assert result.returncode == 1
    assert "must resolve under" in result.stderr
    assert current_link.resolve() == current_release.resolve()


def test_stable_deploy_uses_versioned_release_layout_by_default(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    _write_minimal_package(repo_root)
    subprocess.run(["git", "add", "pyproject.toml"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "add-pyproject"], cwd=repo_root, check=True, capture_output=True, text=True)

    script_copy = _copy_stable_script("stable_deploy.sh", repo_root)

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


def test_stable_deploy_preserves_existing_skills_when_export_is_skipped(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)
    _write_minimal_package(repo_root)
    subprocess.run(["git", "add", "pyproject.toml"], cwd=repo_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "commit", "-m", "add-pyproject"], cwd=repo_root, check=True, capture_output=True, text=True)

    script_copy = _copy_stable_script("stable_deploy.sh", repo_root)

    install_root = tmp_path / "stable-root"
    releases_dir = install_root / "install" / "releases"
    previous_release = releases_dir / "release-one"
    previous_skills = previous_release / "skills"
    previous_skills.mkdir(parents=True)
    (previous_skills / "SKILL.md").write_text("stable skill\n", encoding="utf-8")

    current_link = install_root / "install" / "current"
    current_link.parent.mkdir(parents=True, exist_ok=True)
    current_link.symlink_to(previous_release)

    skills_link = install_root / "skills"
    skills_link.parent.mkdir(parents=True, exist_ok=True)
    skills_link.symlink_to(current_link / "skills")

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
            "WARCRAFT_INSTALL_ROOT": str(install_root),
            "WARCRAFT_STABLE_RELEASE_ID": "release-two",
        },
    )

    assert result.returncode == 0
    release_two = releases_dir / "release-two"
    assert current_link.resolve() == release_two.resolve()
    assert (release_two / "skills").is_symlink()
    assert (release_two / "skills").resolve() == previous_skills.resolve()
    assert skills_link.resolve() == previous_skills.resolve()
