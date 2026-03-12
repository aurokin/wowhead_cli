from __future__ import annotations

import subprocess
from pathlib import Path

from simc_cli.repo import RepoPaths


def _fuzzy_glob(base: Path, needle: str, pattern: str = "*") -> list[Path]:
    compact = needle.replace("_", "").replace("-", "")
    matches: list[Path] = []
    for path in base.rglob(pattern):
        normalized = path.stem.lower().replace("_", "").replace("-", "")
        if compact in normalized:
            matches.append(path)
    return sorted(matches)


def _rg_files(needle: str, base: Path, pattern: str) -> list[Path]:
    proc = subprocess.run(["rg", "-l", "-i", needle, str(base), "-g", pattern], capture_output=True, text=True, check=False)
    return sorted(Path(line) for line in proc.stdout.splitlines() if line.strip())


def spec_file_search(paths: RepoPaths, query: str | None) -> dict[str, list[Path]]:
    if not query:
        return {
            "default_apl": sorted(paths.apl_default.glob("*.simc")),
            "assisted_apl": sorted(paths.apl_assisted.glob("*.simc")),
            "cpp": [],
            "hpp": [],
            "spell_dump": [],
        }
    q = query.lower()
    results = {
        "default_apl": sorted(p for p in paths.apl_default.glob("*.simc") if q in p.stem.lower()),
        "assisted_apl": sorted(p for p in paths.apl_assisted.glob("*.simc") if q in p.stem.lower()),
        "cpp": sorted(p for p in paths.class_modules.rglob("*.cpp") if q in p.name.lower()) or _rg_files(q, paths.class_modules, "*.cpp"),
        "hpp": sorted(p for p in paths.class_modules.rglob("*.hpp") if q in p.name.lower()) or _rg_files(q, paths.class_modules, "*.hpp"),
        "spell_dump": sorted(p for p in paths.spell_dump.glob("*.txt") if q in p.name.lower()) or _rg_files(q, paths.spell_dump, "*.txt"),
    }
    if not any(results.values()):
        results["default_apl"] = _fuzzy_glob(paths.apl_default, q, "*.simc")
        results["assisted_apl"] = _fuzzy_glob(paths.apl_assisted, q, "*.simc")
        results["cpp"] = _fuzzy_glob(paths.class_modules, q, "*.cpp")
        results["hpp"] = _fuzzy_glob(paths.class_modules, q, "*.hpp")
        results["spell_dump"] = _fuzzy_glob(paths.spell_dump, q, "*.txt")
    return results
