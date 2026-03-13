from __future__ import annotations

import json
import os
import time
from typing import Any

import pytest
from typer.testing import CliRunner

from icy_veins_cli.main import app

pytestmark = pytest.mark.live

LIVE_ENABLED = os.getenv("WOWHEAD_LIVE_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}
runner = CliRunner()
SPEC_GUIDE_REF = "mistweaver-monk-pve-healing-guide"
CLASS_HUB_REF = "monk-guide"
ROLE_GUIDE_REF = "healing-guide"
EASY_MODE_REF = "fury-warrior-pve-dps-easy-mode"
LEVELING_REF = "mistweaver-monk-leveling-guide"
PVP_REF = "mistweaver-monk-pvp-guide"
SPEC_BUILDS_TALENTS_REF = "mistweaver-monk-pve-healing-spec-builds-talents"
ROTATION_REF = "mistweaver-monk-pve-healing-rotation-cooldowns-abilities"
STAT_PRIORITY_REF = "mistweaver-monk-pve-healing-stat-priority"
GEMS_ENCHANTS_CONSUMABLES_REF = "mistweaver-monk-pve-healing-gems-enchants-consumables"
SPELL_SUMMARY_REF = "mistweaver-monk-pve-healing-spell-summary"
RESOURCES_REF = "mistweaver-monk-resources"
MACROS_ADDONS_REF = "mistweaver-monk-pve-healing-macros-addons"
MYTHIC_PLUS_TIPS_REF = "mistweaver-monk-pve-healing-mythic-plus-tips"
SIMULATIONS_REF = "mistweaver-monk-pve-healing-simulations"
RAID_GUIDE_REF = "mistweaver-monk-pve-healing-nerub-ar-palace-raid-guide"
SPECIAL_EVENT_REF = "mistweaver-monk-mists-of-pandaria-remix-guide"


def _require_live() -> None:
    if not LIVE_ENABLED:
        pytest.skip("Set WOWHEAD_LIVE_TESTS=1 to run live Icy Veins tests.")


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
        f"Live Icy Veins command failed after {attempts} attempts.\n"
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


def test_live_icy_search_contract() -> None:
    _require_live()
    payload = _payload_for(["search", "mistweaver monk guide", "--limit", "5"])

    assert payload["count"] >= 1
    first = payload["results"][0]
    assert first["entity_type"] == "guide"
    assert first["id"] == SPEC_GUIDE_REF
    assert first["metadata"]["content_family"] == "spec_guide"
    assert first["follow_up"]["recommended_command"] == f"icy-veins guide {SPEC_GUIDE_REF}"


def test_live_icy_resolve_easy_mode_contract() -> None:
    _require_live()
    payload = _payload_for(["resolve", "fury warrior easy mode", "--limit", "5"])

    assert payload["resolved"] is True
    assert payload["match"]["id"] == EASY_MODE_REF
    assert payload["match"]["metadata"]["content_family"] == "easy_mode"
    assert payload["next_command"] == f"icy-veins guide {EASY_MODE_REF}"


def test_live_icy_spec_guide_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", SPEC_GUIDE_REF])

    assert payload["guide"]["slug"] == SPEC_GUIDE_REF
    assert payload["guide"]["content_family"] == "spec_guide"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1
    assert payload["navigation"]["count"] >= 2


def test_live_icy_class_hub_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", CLASS_HUB_REF])

    assert payload["guide"]["slug"] == CLASS_HUB_REF
    assert payload["guide"]["content_family"] == "class_hub"
    assert payload["guide"]["traversal_scope"] == "current_page"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_role_guide_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", ROLE_GUIDE_REF])

    assert payload["guide"]["slug"] == ROLE_GUIDE_REF
    assert payload["guide"]["content_family"] == "role_guide"
    assert payload["guide"]["traversal_scope"] == "current_page"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_raid_guide_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", RAID_GUIDE_REF])

    assert payload["guide"]["slug"] == RAID_GUIDE_REF
    assert payload["guide"]["content_family"] == "raid_guide"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_special_event_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", SPECIAL_EVENT_REF])

    assert payload["guide"]["slug"] == SPECIAL_EVENT_REF
    assert payload["guide"]["content_family"] == "special_event_guide"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_pvp_guide_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", PVP_REF])

    assert payload["guide"]["slug"] == PVP_REF
    assert payload["guide"]["content_family"] == "pvp"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_leveling_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", LEVELING_REF])

    assert payload["guide"]["slug"] == LEVELING_REF
    assert payload["guide"]["content_family"] == "leveling"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_spec_builds_talents_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", SPEC_BUILDS_TALENTS_REF])

    assert payload["guide"]["slug"] == SPEC_BUILDS_TALENTS_REF
    assert payload["guide"]["content_family"] == "spec_builds_talents"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_rotation_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", ROTATION_REF])

    assert payload["guide"]["slug"] == ROTATION_REF
    assert payload["guide"]["content_family"] == "rotation_guide"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_stat_priority_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", STAT_PRIORITY_REF])

    assert payload["guide"]["slug"] == STAT_PRIORITY_REF
    assert payload["guide"]["content_family"] == "stat_priority"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_gems_enchants_consumables_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", GEMS_ENCHANTS_CONSUMABLES_REF])

    assert payload["guide"]["slug"] == GEMS_ENCHANTS_CONSUMABLES_REF
    assert payload["guide"]["content_family"] == "gems_enchants_consumables"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_spell_summary_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", SPELL_SUMMARY_REF])

    assert payload["guide"]["slug"] == SPELL_SUMMARY_REF
    assert payload["guide"]["content_family"] == "spell_summary"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_resources_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", RESOURCES_REF])

    assert payload["guide"]["slug"] == RESOURCES_REF
    assert payload["guide"]["content_family"] == "resources"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_macros_addons_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", MACROS_ADDONS_REF])

    assert payload["guide"]["slug"] == MACROS_ADDONS_REF
    assert payload["guide"]["content_family"] == "macros_addons"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_mythic_plus_tips_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", MYTHIC_PLUS_TIPS_REF])

    assert payload["guide"]["slug"] == MYTHIC_PLUS_TIPS_REF
    assert payload["guide"]["content_family"] == "mythic_plus_tips"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_simulations_contract() -> None:
    _require_live()
    payload = _payload_for(["guide", SIMULATIONS_REF])

    assert payload["guide"]["slug"] == SIMULATIONS_REF
    assert payload["guide"]["content_family"] == "simulations"
    assert payload["guide"]["traversal_scope"] == "family_navigation"
    assert payload["article"]["section_count"] >= 1


def test_live_icy_class_hub_guide_full_stays_local() -> None:
    _require_live()
    payload = _payload_for(["guide-full", CLASS_HUB_REF])

    assert payload["guide"]["slug"] == CLASS_HUB_REF
    assert payload["guide"]["content_family"] == "class_hub"
    assert payload["guide"]["page_count"] == 1
    assert len(payload["pages"]) == 1
    assert payload["pages"][0]["guide"]["slug"] == CLASS_HUB_REF


def test_live_icy_invalid_ref_contract() -> None:
    _require_live()
    result = runner.invoke(app, ["guide", "news-roundup"])

    assert result.exit_code == 1
    payload = json.loads(result.stderr or result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "invalid_guide_ref"


def test_live_icy_unsupported_query_scope_hint() -> None:
    _require_live()
    payload = _payload_for(["search", "patch notes", "--limit", "5"])

    assert payload["count"] == 0
    assert payload["results"] == []
    assert payload["scope_hint"]["code"] == "patch_notes"
