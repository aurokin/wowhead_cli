from __future__ import annotations

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


def test_create_worktree_creates_sibling_branch_from_master(tmp_path: Path) -> None:
    workspace_root = tmp_path / "warcraft_cli"
    master_root = workspace_root / "master"
    master_root.mkdir(parents=True)
    _init_repo(master_root)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "create_worktree.sh"
    script_copy = master_root / "scripts" / "create_worktree.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    result = subprocess.run(
        ["bash", str(script_copy), "feature-one"],
        cwd=master_root,
        check=True,
        capture_output=True,
        text=True,
    )

    feature_root = workspace_root / "feature-one"
    assert feature_root.is_dir()
    assert "Created worktree" in result.stdout

    branch_name = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=feature_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert branch_name == "feature-one"

    worktree_list = subprocess.run(
        ["git", "worktree", "list"],
        cwd=master_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert str(master_root) in worktree_list
    assert str(feature_root) in worktree_list


def test_create_worktree_refuses_non_master_without_override(tmp_path: Path) -> None:
    workspace_root = tmp_path / "warcraft_cli"
    branch_root = workspace_root / "feature-base"
    branch_root.mkdir(parents=True)
    _init_repo(branch_root)
    subprocess.run(["git", "checkout", "-b", "feature-base"], cwd=branch_root, check=True, capture_output=True, text=True)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "create_worktree.sh"
    script_copy = branch_root / "scripts" / "create_worktree.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    result = subprocess.run(
        ["bash", str(script_copy), "feature-two"],
        cwd=branch_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "reserved stable checkout 'master'" in result.stderr
    assert not (workspace_root / "feature-two").exists()


def test_create_worktree_refuses_existing_remote_branch(tmp_path: Path) -> None:
    workspace_root = tmp_path / "warcraft_cli"
    remote_root = tmp_path / "remote.git"
    master_root = workspace_root / "master"
    master_root.mkdir(parents=True)
    _init_repo(master_root)

    subprocess.run(["git", "init", "--bare", str(remote_root)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote_root)], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "push", "-u", "origin", "master"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "checkout", "-b", "feature-one"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "push", "-u", "origin", "feature-one"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "checkout", "master"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "branch", "-D", "feature-one"], cwd=master_root, check=True, capture_output=True, text=True)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "create_worktree.sh"
    script_copy = master_root / "scripts" / "create_worktree.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    result = subprocess.run(
        ["bash", str(script_copy), "feature-one"],
        cwd=master_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Remote branch already exists" in result.stderr
    assert not (workspace_root / "feature-one").exists()


def test_create_worktree_accepts_detected_main_as_stable_branch(tmp_path: Path) -> None:
    workspace_root = tmp_path / "warcraft_cli"
    main_root = workspace_root / "main"
    main_root.mkdir(parents=True)
    _init_repo(main_root, branch="main")

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "create_worktree.sh"
    script_copy = main_root / "scripts" / "create_worktree.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    result = subprocess.run(
        ["bash", str(script_copy), "feature-main-based"],
        cwd=main_root,
        check=True,
        capture_output=True,
        text=True,
    )

    feature_root = workspace_root / "feature-main-based"
    assert feature_root.is_dir()
    assert "Created worktree" in result.stdout


def test_create_worktree_allows_unknown_stable_branch_with_override(tmp_path: Path) -> None:
    workspace_root = tmp_path / "warcraft_cli"
    trunk_root = workspace_root / "trunk"
    trunk_root.mkdir(parents=True)
    _init_repo(trunk_root, branch="trunk")

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "create_worktree.sh"
    script_copy = trunk_root / "scripts" / "create_worktree.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    result = subprocess.run(
        ["bash", str(script_copy), "feature-trunk-based", "--allow-non-master"],
        cwd=trunk_root,
        check=True,
        capture_output=True,
        text=True,
    )

    feature_root = workspace_root / "feature-trunk-based"
    assert feature_root.is_dir()
    assert "Created worktree" in result.stdout


def test_create_worktree_refuses_existing_remote_branch_on_non_origin_remote(tmp_path: Path) -> None:
    workspace_root = tmp_path / "warcraft_cli"
    remote_root = tmp_path / "upstream.git"
    master_root = workspace_root / "master"
    master_root.mkdir(parents=True)
    _init_repo(master_root)

    subprocess.run(["git", "init", "--bare", str(remote_root)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "remote", "add", "upstream", str(remote_root)], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "push", "-u", "upstream", "master"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "checkout", "-b", "feature-two"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "push", "-u", "upstream", "feature-two"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "checkout", "master"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "branch", "-D", "feature-two"], cwd=master_root, check=True, capture_output=True, text=True)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "create_worktree.sh"
    script_copy = master_root / "scripts" / "create_worktree.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    result = subprocess.run(
        ["bash", str(script_copy), "feature-two"],
        cwd=master_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Remote branch already exists on upstream" in result.stderr
    assert not (workspace_root / "feature-two").exists()


def test_create_worktree_normalizes_slash_branch_name_to_sibling_dir(tmp_path: Path) -> None:
    workspace_root = tmp_path / "warcraft_cli"
    master_root = workspace_root / "master"
    master_root.mkdir(parents=True)
    _init_repo(master_root)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "create_worktree.sh"
    script_copy = master_root / "scripts" / "create_worktree.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    result = subprocess.run(
        ["bash", str(script_copy), "feature/cache"],
        cwd=master_root,
        check=True,
        capture_output=True,
        text=True,
    )

    feature_root = workspace_root / "feature--cache"
    assert feature_root.is_dir()
    assert "Created worktree" in result.stdout
