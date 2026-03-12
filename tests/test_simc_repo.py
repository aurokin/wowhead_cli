from __future__ import annotations

from pathlib import Path

from simc_cli.repo import discover_repo, validate_build, validate_repo


def _make_repo(root: Path, *, with_binary: bool = True) -> None:
    (root / "ActionPriorityLists" / "default").mkdir(parents=True)
    (root / "ActionPriorityLists" / "assisted_combat").mkdir(parents=True)
    (root / "engine" / "class_modules").mkdir(parents=True)
    (root / "SpellDataDump").mkdir(parents=True)
    (root / "build").mkdir(parents=True)
    if with_binary:
        binary = root / "build" / "simc"
        binary.write_text("")
        binary.chmod(0o755)


def test_discover_repo_uses_override_path(tmp_path: Path) -> None:
    _make_repo(tmp_path)
    paths = discover_repo(tmp_path)
    assert paths.root == tmp_path.resolve()
    assert paths.apl_default.exists()
    assert paths.build_simc.exists()


def test_validate_repo_reports_missing_paths(tmp_path: Path) -> None:
    paths = discover_repo(tmp_path)
    issues = validate_repo(paths)
    assert issues
    assert any("default APL dir" in issue for issue in issues)


def test_validate_build_reports_missing_binary(tmp_path: Path) -> None:
    _make_repo(tmp_path, with_binary=False)
    paths = discover_repo(tmp_path)
    issues = validate_build(paths)
    assert any("simc binary" in issue for issue in issues)
