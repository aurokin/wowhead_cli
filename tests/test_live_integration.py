from __future__ import annotations

import json
import os
import time
from typing import Any

import pytest
from typer.testing import CliRunner

from wowhead_cli.expansion_profiles import resolve_expansion
from wowhead_cli.main import app

pytestmark = pytest.mark.live

LIVE_ENABLED = os.getenv("WOWHEAD_LIVE_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}
runner = CliRunner()
ENTITY_DISCOVERY_QUERIES: dict[str, str] = {
    "quest": "defias in dustwallow",
    "npc": "defias ringleader",
    "spell": "thunderfury",
}


def _require_live() -> None:
    if not LIVE_ENABLED:
        pytest.skip("Set WOWHEAD_LIVE_TESTS=1 to run live integration tests.")


def _invoke_live(args: list[str], *, attempts: int = 3) -> Any:
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
        f"Live command failed after {attempts} attempts.\n"
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


def _discover_entity_id(*, expansion_key: str, entity_type: str, query: str) -> int:
    payload = _payload_for(["--expansion", expansion_key, "search", query, "--limit", "10"])
    results = payload.get("results")
    assert isinstance(results, list)
    for row in results:
        if not isinstance(row, dict):
            continue
        if row.get("entity_type") != entity_type:
            continue
        candidate_id = row.get("id")
        if isinstance(candidate_id, int):
            return candidate_id
    pytest.fail(
        f"Could not discover {entity_type!r} via query {query!r} "
        f"for expansion={expansion_key}. results={results}"
    )


@pytest.mark.parametrize("expansion_key", ["retail", "classic", "wotlk", "cata", "mop-classic", "ptr"])
def test_live_search_contract(expansion_key: str) -> None:
    _require_live()
    profile = resolve_expansion(expansion_key)
    payload = _payload_for(["--expansion", expansion_key, "search", "thunderfury", "--limit", "3"])

    assert payload["expansion"] == expansion_key
    assert payload["search_url"].startswith(f"{profile.wowhead_base}/search?q=")
    assert payload["count"] == len(payload["results"])
    assert payload["count"] > 0
    for row in payload["results"]:
        assert isinstance(row.get("id"), int)
        url = row.get("url")
        if isinstance(url, str):
            assert url.startswith(f"{profile.wowhead_base}/")


@pytest.mark.parametrize("expansion_key", ["retail", "classic", "wotlk", "cata", "mop-classic", "ptr"])
def test_live_entity_contract(expansion_key: str) -> None:
    _require_live()
    profile = resolve_expansion(expansion_key)
    payload = _payload_for(["--expansion", expansion_key, "entity", "item", "19019"])

    assert payload["expansion"] == expansion_key
    assert payload["entity"]["page_url"].startswith(f"{profile.wowhead_base}/item=19019")
    assert payload["citations"]["comments"].startswith(payload["entity"]["page_url"] + "#comments")
    tooltip = payload["tooltip"]
    assert isinstance(payload["entity"].get("name"), str)
    assert isinstance(tooltip.get("icon"), str)
    assert isinstance(tooltip.get("text"), str)
    assert isinstance(tooltip.get("summary"), str)


@pytest.mark.parametrize(
    ("entity_type", "entity_id", "page_prefix"),
    [
        ("faction", 529, "https://www.wowhead.com/faction=529"),
        ("pet", 39, "https://www.wowhead.com/pet=39"),
        ("recipe", 2549, "https://www.wowhead.com/spell=2549"),
        ("mount", 460, "https://www.wowhead.com/item=84101"),
        ("battle-pet", 39, "https://www.wowhead.com/npc=2671"),
    ],
)
def test_live_special_entity_route_contract(entity_type: str, entity_id: int, page_prefix: str) -> None:
    _require_live()
    payload = _payload_for(["entity", entity_type, str(entity_id), "--no-include-comments", "--linked-entity-preview-limit", "0"])

    assert payload["entity"]["type"] == entity_type
    assert payload["entity"]["id"] == entity_id
    assert payload["entity"]["page_url"].startswith(page_prefix)
    tooltip = payload.get("tooltip")
    assert isinstance(tooltip, dict)
    assert isinstance(tooltip.get("text"), str)


@pytest.mark.parametrize("expansion_key", ["retail", "wotlk", "ptr"])
def test_live_entity_page_contract(expansion_key: str) -> None:
    _require_live()
    payload = _payload_for(["--expansion", expansion_key, "entity-page", "item", "19019", "--max-links", "10"])

    assert payload["expansion"] == expansion_key
    assert payload["normalize_canonical_to_expansion"] is False
    assert payload["entity"]["page_url"].startswith(f"{resolve_expansion(expansion_key).wowhead_base}/item=19019")
    assert payload["citations"]["page"] == payload["entity"]["page_url"]
    assert payload["citations"]["comments"] == f'{payload["entity"]["page_url"]}#comments'
    assert payload["linked_entities"]["count"] == len(payload["linked_entities"]["items"])
    assert payload["linked_entities"]["count"] > 0


def test_live_ptr_canonical_normalization_contract() -> None:
    _require_live()
    default_payload = _payload_for(["--expansion", "ptr", "entity-page", "item", "19019", "--max-links", "1"])
    normalized_payload = _payload_for(
        [
            "--expansion",
            "ptr",
            "--normalize-canonical-to-expansion",
            "entity-page",
            "item",
            "19019",
            "--max-links",
            "1",
        ]
    )

    assert default_payload["normalize_canonical_to_expansion"] is False
    assert normalized_payload["normalize_canonical_to_expansion"] is True
    assert normalized_payload["entity"]["page_url"].startswith("https://www.wowhead.com/ptr/item=19019")


@pytest.mark.parametrize("expansion_key", ["retail", "cata", "ptr"])
def test_live_comments_contract(expansion_key: str) -> None:
    _require_live()
    payload = _payload_for(
        [
            "--expansion",
            expansion_key,
            "comments",
            "item",
            "19019",
            "--limit",
            "2",
            "--sort",
            "newest",
            "--hydrate-missing-replies",
        ]
    )

    assert payload["expansion"] == expansion_key
    assert payload["counts"]["returned_comments"] == len(payload["comments"])
    assert payload["counts"]["returned_comments"] > 0
    first = payload["comments"][0]
    assert "#comments:id=" in first["citation_url"]
    assert first["source_url"] == payload["entity"]["page_url"]


@pytest.mark.parametrize("expansion_key", ["retail", "wotlk", "cata"])
def test_live_compare_contract(expansion_key: str) -> None:
    _require_live()
    profile = resolve_expansion(expansion_key)
    payload = _payload_for(
        [
            "--expansion",
            expansion_key,
            "compare",
            "item:19019",
            "item:19351",
            "--comment-sample",
            "0",
            "--max-links-per-entity",
            "10",
        ]
    )

    assert payload["expansion"] == expansion_key
    assert len(payload["entities"]) == 2
    fields = payload["comparison"]["fields"]
    for key in ["name", "quality", "icon", "title"]:
        assert key in fields
        assert isinstance(fields[key]["all_equal"], bool)
    links = payload["comparison"]["linked_entities"]
    assert links["shared_count_total"] >= links["shared_count_returned"]
    for page_url in payload["citations"]["entity_pages"]:
        assert page_url.startswith(f"{profile.wowhead_base}/")


@pytest.mark.parametrize(
    ("entity_type", "query"),
    [
        ("quest", ENTITY_DISCOVERY_QUERIES["quest"]),
        ("npc", ENTITY_DISCOVERY_QUERIES["npc"]),
        ("spell", ENTITY_DISCOVERY_QUERIES["spell"]),
    ],
)
def test_live_discovered_entity_type_command_flow(entity_type: str, query: str) -> None:
    _require_live()
    expansion_key = "retail"
    profile = resolve_expansion(expansion_key)
    entity_id = _discover_entity_id(expansion_key=expansion_key, entity_type=entity_type, query=query)

    entity_payload = _payload_for(["--expansion", expansion_key, "entity", entity_type, str(entity_id)])
    assert entity_payload["expansion"] == expansion_key
    assert entity_payload["entity"]["type"] == entity_type
    assert entity_payload["entity"]["id"] == entity_id
    assert entity_payload["entity"]["page_url"].startswith(f"{profile.wowhead_base}/{entity_type}={entity_id}")

    page_payload = _payload_for(
        ["--expansion", expansion_key, "entity-page", entity_type, str(entity_id), "--max-links", "10"]
    )
    assert page_payload["entity"]["type"] == entity_type
    assert page_payload["entity"]["id"] == entity_id
    assert page_payload["linked_entities"]["count"] == len(page_payload["linked_entities"]["items"])
    assert page_payload["linked_entities"]["count"] > 0
    assert page_payload["citations"]["page"] == page_payload["entity"]["page_url"]

    comments_payload = _payload_for(
        ["--expansion", expansion_key, "comments", entity_type, str(entity_id), "--limit", "2", "--sort", "newest"]
    )
    returned_comments = comments_payload["counts"]["returned_comments"]
    comments = comments_payload["comments"]
    assert returned_comments == len(comments)
    assert comments_payload["citations"]["comments"] == f'{comments_payload["entity"]["page_url"]}#comments'
    if returned_comments > 0:
        first = comments[0]
        assert "#comments:id=" in first["citation_url"]
        assert first["source_url"] == comments_payload["entity"]["page_url"]
    else:
        assert comments == []


def test_live_compare_contract_for_discovered_mixed_entity_types() -> None:
    _require_live()
    expansion_key = "retail"
    profile = resolve_expansion(expansion_key)
    quest_id = _discover_entity_id(
        expansion_key=expansion_key,
        entity_type="quest",
        query=ENTITY_DISCOVERY_QUERIES["quest"],
    )
    npc_id = _discover_entity_id(
        expansion_key=expansion_key,
        entity_type="npc",
        query=ENTITY_DISCOVERY_QUERIES["npc"],
    )
    spell_id = _discover_entity_id(
        expansion_key=expansion_key,
        entity_type="spell",
        query=ENTITY_DISCOVERY_QUERIES["spell"],
    )
    payload = _payload_for(
        [
            "--expansion",
            expansion_key,
            "compare",
            f"quest:{quest_id}",
            f"npc:{npc_id}",
            f"spell:{spell_id}",
            "--comment-sample",
            "1",
            "--max-links-per-entity",
            "10",
        ]
    )

    assert payload["expansion"] == expansion_key
    assert len(payload["entities"]) == 3
    fields = payload["comparison"]["fields"]
    for key in ["name", "quality", "icon", "title"]:
        assert key in fields
        assert isinstance(fields[key]["all_equal"], bool)
    links = payload["comparison"]["linked_entities"]
    assert links["shared_count_total"] >= links["shared_count_returned"]
    assert len(payload["citations"]["entity_pages"]) == 3
    for page_url in payload["citations"]["entity_pages"]:
        assert page_url.startswith(f"{profile.wowhead_base}/")
