#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
WARCRAFT_SKILL_DIR = REPO_ROOT / "skills" / "warcraft"
GENERATE_PROVIDER_SKILLS_SCRIPT = REPO_ROOT / "scripts" / "generate_provider_skills.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export the root warcraft skill plus generated provider skills into one stable skills directory."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Destination directory that will contain warcraft plus generated provider skill folders.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    tmp_dir = output_dir.parent / f".tmp-skills-{output_dir.name}"

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(WARCRAFT_SKILL_DIR, tmp_dir / "warcraft")

    subprocess.run(
        [sys.executable, str(GENERATE_PROVIDER_SKILLS_SCRIPT), "--output-dir", str(tmp_dir)],
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    if output_dir.exists():
        shutil.rmtree(output_dir)
    tmp_dir.rename(output_dir)
    print(output_dir)


if __name__ == "__main__":
    main()
