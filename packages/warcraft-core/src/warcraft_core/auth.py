from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from warcraft_core.paths import provider_state_path


def load_provider_auth_state(provider: str, *, path: str | Path | None = None) -> dict[str, Any] | None:
    state_path = Path(path).expanduser() if path is not None else provider_state_path(provider)
    if not state_path.is_file():
        return None
    payload = json.loads(state_path.read_text())
    if not isinstance(payload, dict):
        return None
    return payload


def provider_auth_status(provider: str, *, path: str | Path | None = None, now: float | None = None) -> dict[str, Any]:
    state_path = Path(path).expanduser() if path is not None else provider_state_path(provider)
    summary: dict[str, Any] = {
        "path": str(state_path),
        "exists": state_path.is_file(),
        "readable": False,
        "valid_json": False,
        "auth_mode": None,
        "has_access_token": False,
        "has_refresh_token": False,
        "expires_at": None,
        "expired": None,
    }
    if not state_path.is_file():
        return summary
    try:
        payload = json.loads(state_path.read_text())
    except (OSError, json.JSONDecodeError):
        return summary
    summary["readable"] = True
    if not isinstance(payload, dict):
        return summary
    summary["valid_json"] = True
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    auth_mode = payload.get("auth_mode")
    expires_at = payload.get("expires_at")
    now_value = time.time() if now is None else now
    summary["auth_mode"] = auth_mode.strip() if isinstance(auth_mode, str) and auth_mode.strip() else None
    summary["has_access_token"] = isinstance(access_token, str) and bool(access_token.strip())
    summary["has_refresh_token"] = isinstance(refresh_token, str) and bool(refresh_token.strip())
    if isinstance(expires_at, (int, float)):
        summary["expires_at"] = float(expires_at)
        summary["expired"] = now_value >= float(expires_at)
    return summary
