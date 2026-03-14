from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner
from warcraftlogs_cli.client import load_warcraftlogs_auth_config
from warcraftlogs_cli.main import app

runner = CliRunner()


def _payload_for(args: list[str]) -> dict[str, object]:
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    return json.loads(result.stdout)


def _require_warcraftlogs_auth() -> None:
    if not load_warcraftlogs_auth_config().configured:
        pytest.skip("Warcraft Logs credentials are not configured.")


@pytest.mark.live
def test_live_warcraftlogs_regions_contract() -> None:
    _require_warcraftlogs_auth()
    payload = _payload_for(["regions"])

    assert payload["provider"] == "warcraftlogs"
    assert payload["count"] >= 1
    assert any(region["slug"] == "us" for region in payload["regions"])


@pytest.mark.live
def test_live_warcraftlogs_server_contract() -> None:
    _require_warcraftlogs_auth()
    payload = _payload_for(["server", "us", "illidan"])

    assert payload["provider"] == "warcraftlogs"
    assert payload["server"]["slug"] == "illidan"
    assert payload["server"]["region"]["slug"] == "us"


@pytest.mark.live
def test_live_warcraftlogs_guild_contract() -> None:
    _require_warcraftlogs_auth()
    payload = _payload_for(["guild", "us", "illidan", "Liquid"])

    assert payload["provider"] == "warcraftlogs"
    assert payload["guild"]["name"] == "Liquid"
    assert payload["guild"]["server"]["slug"] == "illidan"
