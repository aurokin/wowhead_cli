from __future__ import annotations

from warcraft_core.identity import (
    ability_identity_payload,
    build_identity_payload,
    build_reference_payload,
    build_reference_transport_packet_payload,
    class_spec_identity_payload,
    encounter_identity_payload,
    normalize_actor_class,
    normalize_spec_name,
    parse_wowhead_talent_calc_ref,
    refresh_talent_transport_packet,
    report_actor_identity_payload,
    talent_transport_packet_payload,
)


def test_class_spec_identity_distinguishes_normalized_inferred_and_ambiguous() -> None:
    normalized = class_spec_identity_payload(actor_class="Demon Hunter", spec="Havoc", canonical=False)
    assert normalized["status"] == "normalized"
    assert normalized["identity"] == {"actor_class": "demonhunter", "spec": "havoc"}

    inferred = class_spec_identity_payload(
        actor_class="Demon Hunter",
        spec="Havoc",
        inferred=True,
        confidence="high",
        source="simc_probe",
    )
    assert inferred["status"] == "inferred"
    assert inferred["confidence"] == "high"

    ambiguous = class_spec_identity_payload(
        actor_class="Monk",
        spec=None,
        candidates=[("Monk", "Mistweaver"), ("Demon Hunter", "Havoc")],
        confidence="low",
    )
    assert ambiguous["status"] == "ambiguous"
    assert ambiguous["candidate_count"] == 2


def test_encounter_and_ability_identity_only_become_canonical_with_stable_ids() -> None:
    encounter = encounter_identity_payload(encounter_id=3012, journal_id=9001, name="Dimensius, the All-Devouring")
    assert encounter["status"] == "canonical"
    assert encounter["identity"]["normalized_name"] == "dimensius-the-all-devouring"

    ability = ability_identity_payload(name="Avenging Wrath")
    assert ability["status"] == "normalized"
    assert ability["identity"]["normalized_name"] == "avenging_wrath"

    canonical_ability = ability_identity_payload(spell_id=31884, name="Avenging Wrath")
    assert canonical_ability["status"] == "canonical"


def test_report_actor_identity_is_only_canonical_inside_local_report_scope() -> None:
    scoped = report_actor_identity_payload(
        report_code="abcd1234",
        fight_id=3,
        actor_id=42,
        name="Auropower",
        actor_class="Paladin",
        spec="Retribution",
    )
    assert scoped["status"] == "canonical"
    assert scoped["identity"]["local_key"] == "abcd1234:3:42"

    unscoped = report_actor_identity_payload(
        report_code=None,
        fight_id=None,
        actor_id=None,
        name="Auropower",
        actor_class="Paladin",
        spec="Retribution",
    )
    assert unscoped["status"] == "normalized"


def test_build_identity_contract_never_claims_canonical_status() -> None:
    resolved = build_identity_payload(
        actor_class="Demon Hunter",
        spec="Havoc",
        confidence="high",
        source="simc_probe",
        candidates=[("Demon Hunter", "Havoc")],
        source_notes=["identified by SimC probe"],
    )
    assert resolved["status"] == "inferred"
    assert resolved["canonical"] is False
    assert resolved["class_spec_identity"]["status"] == "inferred"

    ambiguous = build_identity_payload(
        actor_class=None,
        spec=None,
        confidence="low",
        source="simc_probe",
        candidates=[("Monk", "Mistweaver"), ("Demon Hunter", "Havoc")],
    )
    assert ambiguous["status"] == "ambiguous"


def test_actor_class_and_spec_normalizers_stay_small_and_predictable() -> None:
    assert normalize_actor_class("Demon Hunter") == "demonhunter"
    assert normalize_spec_name("Beast Mastery") == "beast_mastery"


def test_parse_wowhead_talent_calc_ref_supports_prefixed_paths_and_relative_urls() -> None:
    payload = parse_wowhead_talent_calc_ref("/cata/talent-calc/hunter/beast-mastery/XYZ987")
    assert payload == {
        "actor_class": "hunter",
        "spec": "beast_mastery",
        "build_code": "XYZ987",
        "reference_url": "https://www.wowhead.com/cata/talent-calc/hunter/beast-mastery/XYZ987",
        "source_kind": "wowhead_talent_calc_url",
    }


def test_build_reference_payload_only_accepts_explicit_wowhead_talent_calc_urls() -> None:
    payload = build_reference_payload(
        ref="https://www.wowhead.com/talent-calc/druid/balance/ABC123",
        provider="method",
        source="guide_embedded_link",
        source_url="https://www.method.gg/guides/balance-druid",
        label="Raid Build",
        notes=["embedded guide link"],
    )
    assert payload is not None
    assert payload["reference_type"] == "wowhead_talent_calc_url"
    assert payload["build_code"] == "ABC123"
    assert payload["build_identity"]["status"] == "inferred"
    assert payload["build_identity"]["class_spec_identity"]["identity"] == {"actor_class": "druid", "spec": "balance"}
    assert build_reference_payload(ref="https://www.wowhead.com/spell=116670", provider="method", source="guide_embedded_link") is None


def test_build_reference_transport_packet_payload_marks_explicit_refs_as_exact() -> None:
    payload = build_reference_transport_packet_payload(
        ref="https://www.wowhead.com/talent-calc/druid/balance/ABC123",
        provider="warcraft",
        source="guide_build_reference_handoff",
        source_url="https://www.method.gg/guides/balance-druid",
        source_urls=["https://www.method.gg/guides/balance-druid"],
        label="Raid Build",
        notes=["explicit guide build ref"],
        scope={"type": "guide_build_reference_handoff"},
    )
    assert payload is not None
    assert payload["transport_status"] == "exact"
    assert payload["transport_forms"]["wowhead_talent_calc_url"] == "https://www.wowhead.com/talent-calc/druid/balance/ABC123"
    assert payload["raw_evidence"]["reference_type"] == "wowhead_talent_calc_url"
    assert payload["scope"] == {"type": "guide_build_reference_handoff"}


def test_talent_transport_packet_distinguishes_exact_validated_and_raw_only() -> None:
    exact = talent_transport_packet_payload(
        actor_class="Druid",
        spec="Balance",
        confidence="high",
        source="wowhead_talent_calc_url",
        transport_forms={"wowhead_talent_calc_url": "https://www.wowhead.com/talent-calc/druid/balance/ABC123"},
        source_notes=["explicit wowhead ref"],
    )
    assert exact["transport_status"] == "exact"
    assert exact["build_identity"]["status"] == "inferred"

    validated = talent_transport_packet_payload(
        actor_class="Druid",
        spec="Balance",
        confidence="high",
        source="warcraftlogs_talent_tree",
        transport_forms={
            "simc_split_talents": {
                "class_talents": "103324:1",
                "spec_talents": "109839:1",
                "hero_talents": "117176:1",
            }
        },
        raw_evidence={"talent_tree_entries": [{"entry": 103324, "rank": 1}]},
        validation={"status": "validated"},
    )
    assert validated["transport_status"] == "validated"

    raw_only = talent_transport_packet_payload(
        actor_class="Druid",
        spec="Balance",
        confidence="medium",
        source="warcraftlogs_talent_tree",
        raw_evidence={"talent_tree_entries": [{"entry": 103324, "rank": 1}]},
    )
    assert raw_only["transport_status"] == "raw_only"


def test_refresh_talent_transport_packet_preserves_scope_and_upgrades_status() -> None:
    packet = talent_transport_packet_payload(
        actor_class="Druid",
        spec="Balance",
        confidence="high",
        source="warcraftlogs_talent_tree",
        provider="warcraftlogs",
        raw_evidence={"talent_tree_entries": [{"entry": 103324, "node_id": 82244, "rank": 1}]},
        validation={"status": "not_validated"},
        scope={"type": "report_fight_actor", "report_code": "abcd1234", "fight_id": 1, "actor_id": 9},
    )

    refreshed = refresh_talent_transport_packet(
        packet,
        transport_forms={
            "simc_split_talents": {
                "class_talents": "103324:1",
                "spec_talents": "109839:1",
            }
        },
        validation={"status": "validated", "source": "simc_trait_data_round_trip"},
    )

    assert refreshed["transport_status"] == "validated"
    assert refreshed["scope"] == packet["scope"]
    assert refreshed["source"] == packet["source"]
    assert refreshed["raw_evidence"] == packet["raw_evidence"]
