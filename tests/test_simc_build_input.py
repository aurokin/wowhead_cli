from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

from simc_cli.build_input import (
    BuildSpec,
    build_profile_text,
    detect_build_text_source_kind,
    detect_talents_option_source_kind,
    decode_build,
    extract_build_spec_from_text,
    infer_actor_and_spec_from_apl,
    merge_build_specs,
    normalize_talents_input,
    parse_debug_talents,
    tokenize_talent_name,
)
from simc_cli.repo import RepoPaths

FIXTURES = Path("/home/auro/code/simc_exp/tests/fixtures")


def test_tokenize_talent_name_normalizes_text() -> None:
    assert tokenize_talent_name("Devourer's Bite") == "devourers_bite"
    assert tokenize_talent_name("Tip the Scales") == "tip_the_scales"


def test_extract_build_spec_from_plain_hash() -> None:
    spec = extract_build_spec_from_text("ABC123")
    assert spec.talents == "ABC123"
    assert spec.source_kind == "wow_talent_export"
    assert "single-line talent export" in spec.source_notes


def test_extract_build_spec_from_profile_lines() -> None:
    text = """
    demonhunter="example"
    spec=devourer
    talents=ABC123
    class_talents=class-string
    hero_talents=hero-string
    """
    spec = extract_build_spec_from_text(text)
    assert spec.actor_class == "demonhunter"
    assert spec.spec == "devourer"
    assert spec.talents == "ABC123"
    assert spec.class_talents == "class-string"
    assert spec.hero_talents == "hero-string"
    assert spec.source_kind == "simc_split_talents"


def test_merge_build_specs_prefers_later_values() -> None:
    left = BuildSpec(actor_class="evoker", spec="devastation", talents="left")
    right = BuildSpec(talents="right", hero_talents="hero")
    merged = merge_build_specs(left, right)
    assert merged.actor_class == "evoker"
    assert merged.spec == "devastation"
    assert merged.talents == "right"
    assert merged.hero_talents == "hero"


def test_infer_actor_and_spec_from_apl() -> None:
    actor_class, spec = infer_actor_and_spec_from_apl("ActionPriorityLists/default/evoker_devastation.simc")
    assert actor_class == "evoker"
    assert spec == "devastation"


def test_normalize_talents_input() -> None:
    assert normalize_talents_input("talents=ABC123") == "ABC123"
    assert normalize_talents_input("ABC123") == "ABC123"
    assert normalize_talents_input(None) is None


def test_detect_build_text_source_kind() -> None:
    assert detect_build_text_source_kind("ABC123") == "wow_talent_export"
    assert detect_build_text_source_kind('warlock="probe"\nspec=demonology\ntalents=ABC123\n') == "simc_profile"
    assert detect_build_text_source_kind("class_talents=AAA\nspec_talents=BBB\nhero_talents=CCC\n") == "simc_split_talents"


def test_detect_talents_option_source_kind() -> None:
    assert (
        detect_talents_option_source_kind(
            talents="ABC123",
            class_talents=None,
            spec_talents=None,
            hero_talents=None,
        )
        == "wow_talent_export"
    )
    assert (
        detect_talents_option_source_kind(
            talents="talents=ABC123",
            class_talents=None,
            spec_talents=None,
            hero_talents=None,
        )
        == "simc_profile"
    )
    assert (
        detect_talents_option_source_kind(
            talents=None,
            class_talents="AAA",
            spec_talents="BBB",
            hero_talents="CCC",
        )
        == "simc_split_talents"
    )


def test_parse_debug_talents_ignores_selection_tree() -> None:
    output = (FIXTURES / "dh_decode_debug.txt").read_text()
    talents = parse_debug_talents(output)
    assert [talent.token for talent in talents["class"]] == ["voidblade"]
    assert [talent.token for talent in talents["spec"]] == ["void_ray", "devourers_bite"]
    assert [talent.token for talent in talents["hero"]] == ["voidsurge"]
    assert talents["selection"] == []


def test_build_profile_text_contains_expected_lines() -> None:
    text = build_profile_text(BuildSpec(actor_class="evoker", spec="devastation", talents="ABC123"))
    assert 'evoker="simc_decode"' in text
    assert "race=dracthyr" in text
    assert "talents=ABC123" in text


def test_decode_build_uses_debug_output(tmp_path: Path) -> None:
    binary = tmp_path / "simc"
    binary.write_text("")
    repo = RepoPaths(
        root=tmp_path,
        apl_default=tmp_path,
        apl_assisted=tmp_path,
        class_modules=tmp_path,
        spell_dump=tmp_path,
        build_dir=tmp_path,
        build_simc=binary,
    )
    fake_output = (FIXTURES / "dh_decode_debug.txt").read_text()

    with patch("simc_cli.build_input.subprocess.run") as mocked_run:
        mocked_run.return_value = subprocess.CompletedProcess([], 0, stdout=fake_output, stderr="")
        result = decode_build(repo, BuildSpec(actor_class="demonhunter", spec="devourer", talents="ABC123"))

    assert result.actor_class == "demonhunter"
    assert result.spec == "devourer"
    assert result.source_kind is None
    assert 'demonhunter="simc_decode"' in (result.generated_profile_text or "")
    assert "voidblade" in result.enabled_talents
    assert "devourers_bite" in result.enabled_talents
    assert any("decoded via" in note for note in result.source_notes)
