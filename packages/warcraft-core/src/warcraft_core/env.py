from __future__ import annotations

import os
from pathlib import Path


def find_env_file(filename: str = ".env.local", *, start_dir: str | Path | None = None) -> Path | None:
    root = Path(start_dir or Path.cwd()).expanduser().resolve()
    for candidate_dir in (root, *root.parents):
        candidate = candidate_dir / filename
        if candidate.is_file():
            return candidate
    return None


def load_explicit_env_file(path: str | Path, *, override: bool = False) -> Path | None:
    candidate = Path(path).expanduser()
    if not candidate.is_file():
        return None
    for raw_line in candidate.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        if separator != "=":
            continue
        env_key = key.strip()
        if not env_key:
            continue
        if not override and env_key in os.environ:
            continue
        env_value = value.strip()
        if len(env_value) >= 2 and env_value[0] == env_value[-1] and env_value[0] in {"'", '"'}:
            env_value = env_value[1:-1]
        os.environ[env_key] = env_value
    return candidate


def load_env_file(
    filename: str = ".env.local",
    *,
    start_dir: str | Path | None = None,
    override: bool = False,
) -> Path | None:
    path = find_env_file(filename, start_dir=start_dir)
    if path is None:
        return None
    return load_explicit_env_file(path, override=override)
