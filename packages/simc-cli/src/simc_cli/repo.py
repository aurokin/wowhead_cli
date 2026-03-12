from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REPO = Path("/home/auro/code/simc")


@dataclass(slots=True)
class RepoPaths:
    root: Path
    apl_default: Path
    apl_assisted: Path
    class_modules: Path
    spell_dump: Path
    build_dir: Path
    build_simc: Path


def default_repo_root() -> Path:
    configured = os.environ.get("SIMC_REPO_ROOT")
    return Path(configured).expanduser() if configured else DEFAULT_REPO


def discover_repo(root: str | Path | None = None) -> RepoPaths:
    repo_root = Path(root).expanduser() if root else default_repo_root()
    repo_root = repo_root.resolve()
    return RepoPaths(
        root=repo_root,
        apl_default=repo_root / "ActionPriorityLists" / "default",
        apl_assisted=repo_root / "ActionPriorityLists" / "assisted_combat",
        class_modules=repo_root / "engine" / "class_modules",
        spell_dump=repo_root / "SpellDataDump",
        build_dir=repo_root / "build",
        build_simc=repo_root / "build" / "simc",
    )


def validate_repo(paths: RepoPaths) -> list[str]:
    missing: list[str] = []
    for label, path in (
        ("repo root", paths.root),
        ("default APL dir", paths.apl_default),
        ("assisted APL dir", paths.apl_assisted),
        ("class modules dir", paths.class_modules),
        ("spell dump dir", paths.spell_dump),
    ):
        if not path.exists():
            missing.append(f"{label}: {path}")
    return missing


def validate_build(paths: RepoPaths) -> list[str]:
    missing: list[str] = []
    for label, path in (
        ("build dir", paths.build_dir),
        ("simc binary", paths.build_simc),
    ):
        if not path.exists():
            missing.append(f"{label}: {path}")
    return missing
