from __future__ import annotations

from pathlib import Path

from simc_cli.sim import first_action_hits, first_action_time, summarize_first_casts


def test_first_action_time_extracts_first_matching_timestamp() -> None:
    log_text = "\n".join(
        [
            "0.100 schedules execute for Action 'rising_sun_kick'",
            "0.250 performs Action 'rising_sun_kick'",
            "0.400 performs Action 'blackout_kick'",
        ]
    )
    assert first_action_time(log_text, "rising_sun_kick") == 0.1
    assert first_action_time(log_text, "vivify") is None


def test_first_action_hits_extracts_scheduled_and_performed_times(tmp_path: Path) -> None:
    log_path = tmp_path / "combat.log"
    log_path.write_text(
        "\n".join(
            [
                "0.100 schedules execute for Action 'rising_sun_kick'",
                "0.250 performs Action 'rising_sun_kick'",
                "0.500 performs Action 'blackout_kick'",
            ]
        )
        + "\n"
    )
    hits = first_action_hits(log_path, ["rising_sun_kick", "blackout_kick"])
    assert hits[0].scheduled_at == 0.1
    assert hits[0].performed_at == 0.25
    assert hits[1].scheduled_at is None
    assert hits[1].performed_at == 0.5


def test_summarize_first_casts_handles_missing_times(tmp_path: Path) -> None:
    from simc_cli.sim import FirstCastResult

    results = [
        FirstCastResult(seed=1, time=0.4, log_path=tmp_path / "seed_1.log"),
        FirstCastResult(seed=2, time=None, log_path=tmp_path / "seed_2.log"),
        FirstCastResult(seed=3, time=0.7, log_path=tmp_path / "seed_3.log"),
    ]
    summary = summarize_first_casts(results)
    assert summary["samples"] == 3
    assert summary["found"] == 2
    assert summary["min"] == 0.4
    assert summary["max"] == 0.7
