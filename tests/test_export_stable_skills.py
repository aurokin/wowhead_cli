from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_export_stable_skills_exports_root_and_generated_provider_skills(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "export_stable_skills.py"
    output_dir = tmp_path / "stable-skills"

    result = subprocess.run(
        [sys.executable, str(script), "--output-dir", str(output_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )

    assert str(output_dir) in result.stdout

    warcraft_skill = (output_dir / "warcraft" / "SKILL.md").read_text(encoding="utf-8")
    wowhead_skill = (output_dir / "wowhead" / "SKILL.md").read_text(encoding="utf-8")
    warcraft_reference = (output_dir / "warcraft" / "references" / "simc.md").read_text(encoding="utf-8")

    assert "name: warcraft" in warcraft_skill
    assert "Use `warcraft` first" in warcraft_skill
    assert "name: wowhead" in wowhead_skill
    assert "# Wowhead" in wowhead_skill
    assert "# SimulationCraft" in warcraft_reference
