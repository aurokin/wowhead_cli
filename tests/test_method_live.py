from __future__ import annotations

import json
import os
import time
from typing import Any

import pytest
from typer.testing import CliRunner

from method_cli.main import app

pytestmark = pytest.mark.live

LIVE_ENABLED = os.getenv("WOWHEAD_LIVE_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}
runner = CliRunner()
GUIDE_REF = "mistweaver-monk"
SECONDARY_GUIDE_REF = "midnight-alchemy-profession-guide"
TERTIARY_GUIDE_REF = "harati-renown-reputation-guide"


def _require_live() -> None:
    if not LIVE_ENABLED:
        pytest.skip("Set WOWHEAD_LIVE_TESTS=1 to run live Method tests.")


def _invoke_live(args: list[str], *, attempts: int = 3):
    last_result = None
    for attempt in range(1, attempts + 1):
        result = runner.invoke(app, args)
        if result.exit_code == 0:
            return result
        last_result = result
        if attempt < attempts:
            time.sleep(float(attempt))
    assert last_result is not None
    pytest.fail(
        f"Live Method command failed after {attempts} attempts.\n"
        f"args={args}\n"
        f"exit_code={last_result.exit_code}\n"
        f"output={last_result.output[:2000]}"
    )


def _payload_for(args: list[str]) -> dict[str, Any]:
    result = _invoke_live(args)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"Command did not produce JSON.\nargs={args}\nstdout={result.stdout[:2000]}\n{exc}")
    assert payload.get("ok") is not False
    return payload


def test_live_method_search_contract() -> None:
    _require_live()
    payload = _payload_for(["search", "mistweaver monk guide", "--limit", "5"])

    assert payload["search_query"] == "mistweaver monk"
    assert payload["count"] >= 1
    first = payload["results"][0]
    assert first["entity_type"] == "guide"
    assert first["id"] == GUIDE_REF
    assert first["follow_up"]["recommended_command"] == f"method guide {GUIDE_REF}"


def test_live_method_unsupported_query_scope_hint() -> None:
    _require_live()
    payload = _payload_for(["search", "tier list", "--limit", "5"])

    assert payload["count"] == 0
    assert payload["results"] == []
    assert payload["scope_hint"]["code"] == "tier_list"


def test_live_method_resolve_contract() -> None:
    _require_live()
    payload = _payload_for(["resolve", "mistweaver monk"])

    assert payload["resolved"] is True
    assert payload["match"]["id"] == GUIDE_REF
    assert payload["next_command"] == f"method guide {GUIDE_REF}"


def test_live_method_guide_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", GUIDE_REF])

    assert payload["guide"]["slug"] == GUIDE_REF
    assert payload["guide"]["page_url"].startswith("https://www.method.gg/guides/mistweaver-monk")
    assert payload["navigation"]["count"] >= 2
    assert payload["article"]["section_count"] >= 1
    assert payload["linked_entities"]["count"] > 0


def test_live_method_guide_full_contract() -> None:
    _require_live()
    payload = _payload_for(["guide-full", GUIDE_REF])

    assert payload["guide"]["slug"] == GUIDE_REF
    assert payload["guide"]["page_count"] >= 2
    assert len(payload["pages"]) == payload["guide"]["page_count"]
    assert len(payload["citations"]["pages"]) == payload["guide"]["page_count"]
    assert payload["linked_entities"]["count"] >= len(payload["linked_entities"]["items"])


def test_live_method_unsupported_surface_contract() -> None:
    _require_live()
    result = runner.invoke(app, ["guide", "tier-list"])

    assert result.exit_code == 1
    payload = json.loads(result.stderr or result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "unsupported_guide_surface"


def test_live_method_secondary_supported_family_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", SECONDARY_GUIDE_REF])

    assert payload["guide"]["slug"] == SECONDARY_GUIDE_REF
    assert payload["guide"]["content_family"] == "profession_guide"
    assert payload["guide"]["supported_surface"] is True
    assert payload["guide"]["author"] == "Roguery"
    assert payload["guide"]["last_updated"] == "5th March 2026"
    assert payload["article"]["section_count"] >= 1


def test_live_method_reputation_family_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", TERTIARY_GUIDE_REF])

    assert payload["guide"]["slug"] == TERTIARY_GUIDE_REF
    assert payload["guide"]["content_family"] == "reputation_guide"
    assert payload["guide"]["supported_surface"] is True
    assert payload["guide"]["author"] == "Roguery"
    assert payload["guide"]["last_updated"] == "26th February 2026"
    assert payload["linked_entities"]["count"] >= 1
