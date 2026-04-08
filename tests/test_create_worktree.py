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


def test_create_worktree_refuses_remote_lookup_failures(tmp_path: Path) -> None:
    workspace_root = tmp_path / "warcraft_cli"
    master_root = workspace_root / "master"
    master_root.mkdir(parents=True)
    _init_repo(master_root)

    missing_remote = tmp_path / "missing.git"
    subprocess.run(["git", "remote", "add", "upstream", str(missing_remote)], cwd=master_root, check=True, capture_output=True, text=True)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "create_worktree.sh"
    script_copy = master_root / "scripts" / "create_worktree.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    result = subprocess.run(
        ["bash", str(script_copy), "feature-transport-check"],
        cwd=master_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Failed to query remote 'upstream'" in result.stderr
    assert not (workspace_root / "feature-transport-check").exists()


def test_create_worktree_ignores_non_exact_remote_tail_match(tmp_path: Path) -> None:
    workspace_root = tmp_path / "warcraft_cli"
    remote_root = tmp_path / "upstream.git"
    master_root = workspace_root / "master"
    master_root.mkdir(parents=True)
    _init_repo(master_root)

    subprocess.run(["git", "init", "--bare", str(remote_root)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "remote", "add", "upstream", str(remote_root)], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "push", "-u", "upstream", "master"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "checkout", "-b", "topic/feature-one"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "push", "-u", "upstream", "topic/feature-one"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "checkout", "master"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "branch", "-D", "topic/feature-one"], cwd=master_root, check=True, capture_output=True, text=True)

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


def test_create_worktree_refuses_ambiguous_local_master_main_without_override(tmp_path: Path) -> None:
    workspace_root = tmp_path / "warcraft_cli"
    master_root = workspace_root / "master"
    master_root.mkdir(parents=True)
    _init_repo(master_root)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=master_root, check=True, capture_output=True, text=True)
    subprocess.run(["git", "checkout", "master"], cwd=master_root, check=True, capture_output=True, text=True)

    repo_script = Path(__file__).resolve().parent.parent / "scripts" / "create_worktree.sh"
    script_copy = master_root / "scripts" / "create_worktree.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(repo_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    result = subprocess.run(
        ["bash", str(script_copy), "feature-ambiguous"],
        cwd=master_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Could not determine the stable branch" in result.stderr


def test_create_worktree_env_ignores_inherited_runtime_dir(tmp_path: Path) -> None:
    workspace_root = tmp_path / "warcraft_cli"
    master_root = workspace_root / "master"
    master_root.mkdir(parents=True)
    _init_repo(master_root)

    repo_scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
    for script_name in ("create_worktree.sh", "setup_worktree_env.sh"):
        source_path = repo_scripts_dir / script_name
        target_path = master_root / "scripts" / script_name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        target_path.chmod(target_path.stat().st_mode | stat.S_IXUSR)

    subprocess.run(
        ["git", "add", "scripts/create_worktree.sh", "scripts/setup_worktree_env.sh"],
        cwd=master_root,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "add worktree scripts"],
        cwd=master_root,
        check=True,
        capture_output=True,
        text=True,
    )

    inherited_runtime_root = tmp_path / "other-worktree" / ".warcraft" / "runtime"
    env = dict(os.environ, WARCRAFT_WORKTREE_RUNTIME_DIR=str(inherited_runtime_root))

    result = subprocess.run(
        ["bash", str(master_root / "scripts" / "create_worktree.sh"), "feature-env"],
        cwd=master_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    feature_root = workspace_root / "feature-env"
    env_path = feature_root / ".warcraft" / "worktree-env.sh"
    expected_runtime_root = feature_root / ".warcraft" / "runtime"
    env_contents = env_path.read_text(encoding="utf-8")

    assert env_path.is_file()
    assert "Initialized worktree env" in result.stdout
    assert f'export WARCRAFT_WORKTREE_RUNTIME_DIR="{expected_runtime_root}"' in env_contents
    assert str(inherited_runtime_root) not in env_contents


def test_worktree_env_shell_activation_routes_cli_to_worktree_runtime(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    setup_script = Path(__file__).resolve().parent.parent / "scripts" / "setup_worktree_env.sh"
    script_copy = repo_root / "scripts" / "setup_worktree_env.sh"
    script_copy.parent.mkdir(parents=True)
    shutil.copy2(setup_script, script_copy)
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)

    paths_source = Path(__file__).resolve().parent.parent / "packages" / "warcraft-core" / "src" / "warcraft_core" / "paths.py"
    module_dir = repo_root / "packages" / "warcraft-core" / "src" / "warcraft_core"
    module_dir.mkdir(parents=True)
    shutil.copy2(paths_source, module_dir / "paths.py")
    (module_dir / "__init__.py").write_text("", encoding="utf-8")

    cli_path = repo_root / ".venv" / "bin" / "warcraft"
    cli_path.parent.mkdir(parents=True)
    cli_path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
PYTHONPATH="${WARCRAFT_WORKTREE_ROOT}/packages/warcraft-core/src" python3 - <<'PY'
import os
from warcraft_core.paths import cache_root, data_root
print(f"warcraft={os.environ['WARCRAFT_WORKTREE_ROOT']}/.venv/bin/warcraft")
print(f"data={data_root()}")
print(f"cache={cache_root()}")
PY
""",
        encoding="utf-8",
    )
    cli_path.chmod(0o755)

    subprocess.run(
        ["bash", str(script_copy)],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    env_path = repo_root / ".warcraft" / "worktree-env.sh"
    result = subprocess.run(
        [
            "bash",
            "-lc",
            f'source "{env_path}" && command -v warcraft && warcraft',
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    expected_runtime_root = (repo_root / ".warcraft" / "runtime").resolve()
    expected_cli = repo_root / ".venv" / "bin" / "warcraft"
    stdout_lines = result.stdout.strip().splitlines()

    assert stdout_lines[0] == str(expected_cli)
    assert stdout_lines[1] == f"warcraft={expected_cli}"
    assert stdout_lines[2] == f"data={expected_runtime_root / 'data'}"
    assert stdout_lines[3] == f"cache={expected_runtime_root / 'cache'}"
