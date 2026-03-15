from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from warcraft_core.identity import parse_wowhead_talent_calc_ref as parse_shared_wowhead_talent_calc_ref

from simc_cli.repo import RepoPaths

ACTOR_LINE_RE = re.compile(r'^([a-z_]+)\s*=\s*"?(.*?)"?$')
TALENT_DEBUG_RE = re.compile(
    r"adding (?P<tree>class|spec|hero|selection) talent (?P<name>.+?) "
    r"\(node=(?P<node>\d+) entry=(?P<entry>\d+) rank=(?P<rank>\d+)/(?P<max_rank>\d+)\)"
)

DEFAULT_RACE_BY_CLASS = {
    "deathknight": "human",
    "demonhunter": "night_elf",
    "druid": "night_elf",
    "evoker": "dracthyr",
    "hunter": "dwarf",
    "mage": "human",
    "monk": "pandaren",
    "paladin": "human",
    "priest": "human",
    "rogue": "human",
    "shaman": "orc",
    "warlock": "human",
    "warrior": "human",
}


@dataclass(slots=True)
class BuildSpec:
    actor_class: str | None = None
    spec: str | None = None
    talents: str | None = None
    class_talents: str | None = None
    spec_talents: str | None = None
    hero_talents: str | None = None
    source_kind: str | None = None
    source_notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DecodedTalent:
    tree: str
    name: str
    token: str
    rank: int
    max_rank: int


@dataclass(slots=True)
class BuildResolution:
    actor_class: str
    spec: str
    enabled_talents: set[str]
    talents_by_tree: dict[str, list[DecodedTalent]]
    source_kind: str | None
    generated_profile_text: str | None
    source_notes: list[str]


@dataclass(slots=True)
class BuildIdentity:
    actor_class: str | None
    spec: str | None
    confidence: str
    source: str
    candidate_count: int
    candidates: list[tuple[str, str]] = field(default_factory=list)
    source_notes: list[str] = field(default_factory=list)


def infer_actor_and_spec_from_apl(apl_path: str | Path) -> tuple[str | None, str | None]:
    stem = Path(apl_path).stem
    if "_" not in stem:
        return None, None
    actor_class, spec = stem.split("_", 1)
    return actor_class, spec


def tokenize_talent_name(name: str) -> str:
    text = name.lower().replace("'", "")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def _normalize_actor_class(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]+", "", value.lower())
    return normalized or None


def _normalize_spec_name(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or None


def parse_wowhead_talent_calc_ref(ref: str) -> BuildSpec | None:
    parsed = parse_shared_wowhead_talent_calc_ref(ref)
    if parsed is None:
        return None

    source_notes = ["wowhead talent-calc url"]
    build_code = parsed["build_code"]
    if build_code:
        source_notes.append("wowhead build code")
    return BuildSpec(
        actor_class=parsed["actor_class"],
        spec=parsed["spec"],
        talents=build_code,
        source_kind="wowhead_talent_calc_url",
        source_notes=source_notes,
    )


def detect_build_text_source_kind(text: str) -> str | None:
    non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not non_empty_lines:
        return None
    if len(non_empty_lines) == 1 and parse_wowhead_talent_calc_ref(non_empty_lines[0]) is not None:
        return "wowhead_talent_calc_url"
    if len(non_empty_lines) == 1 and "=" not in non_empty_lines[0]:
        return "wow_talent_export"

    saw_actor_line = False
    saw_talents = False
    saw_split_talents = False
    for raw_line in non_empty_lines:
        line = raw_line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, _value = line.split("=", 1)
        key = key.strip()
        actor_match = ACTOR_LINE_RE.match(line)
        if actor_match and key in DEFAULT_RACE_BY_CLASS:
            saw_actor_line = True
            continue
        if key == "talents":
            saw_talents = True
        elif key in {"class_talents", "spec_talents", "hero_talents"}:
            saw_split_talents = True

    if saw_split_talents:
        return "simc_split_talents"
    if saw_actor_line or saw_talents:
        return "simc_profile"
    return "simc_build_text"


def extract_build_spec_from_text(text: str) -> BuildSpec:
    spec = BuildSpec()
    spec.source_kind = detect_build_text_source_kind(text)
    non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(non_empty_lines) == 1:
        wowhead_ref = parse_wowhead_talent_calc_ref(non_empty_lines[0])
        if wowhead_ref is not None:
            return wowhead_ref
    if len(non_empty_lines) == 1 and "=" not in non_empty_lines[0]:
        spec.talents = non_empty_lines[0]
        spec.source_notes.append("single-line talent export")
        return spec

    for raw_line in non_empty_lines:
        line = raw_line.split("#", 1)[0].strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"')
        actor_match = ACTOR_LINE_RE.match(line)
        if actor_match and key in DEFAULT_RACE_BY_CLASS:
            spec.actor_class = key
            spec.source_notes.append(f"actor line: {key}")
            continue
        if key == "spec":
            spec.spec = value
        elif key == "talents":
            spec.talents = value
        elif key == "class_talents":
            spec.class_talents = value
        elif key == "spec_talents":
            spec.spec_talents = value
        elif key == "hero_talents":
            spec.hero_talents = value
    if spec.talents:
        spec.source_notes.append("simc talents input")
    if spec.class_talents or spec.spec_talents or spec.hero_talents:
        spec.source_notes.append("split talent strings")
    return spec


def merge_build_specs(*specs: BuildSpec) -> BuildSpec:
    merged = BuildSpec()
    for spec in specs:
        if spec.actor_class:
            merged.actor_class = spec.actor_class
        if spec.spec:
            merged.spec = spec.spec
        if spec.talents:
            merged.talents = spec.talents
        if spec.class_talents:
            merged.class_talents = spec.class_talents
        if spec.spec_talents:
            merged.spec_talents = spec.spec_talents
        if spec.hero_talents:
            merged.hero_talents = spec.hero_talents
        if spec.source_kind:
            merged.source_kind = spec.source_kind
        merged.source_notes.extend(spec.source_notes)
    return merged


def supported_specs(repo: RepoPaths) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    for directory in (repo.apl_default, repo.apl_assisted):
        for path in sorted(directory.glob("*.simc")):
            actor_class, spec = infer_actor_and_spec_from_apl(path)
            if actor_class and spec and (actor_class, spec) not in candidates:
                candidates.append((actor_class, spec))
    return candidates


def build_profile_text(build_spec: BuildSpec) -> str:
    actor_class = build_spec.actor_class
    if not actor_class:
        raise ValueError("Build spec must include actor_class.")
    race = DEFAULT_RACE_BY_CLASS.get(actor_class, "human")
    lines = [
        f'{actor_class}="simc_decode"',
        "level=90",
        f"race={race}",
        f"spec={build_spec.spec}",
    ]
    if build_spec.talents:
        lines.append(f"talents={build_spec.talents}")
    if build_spec.class_talents:
        lines.append(f"class_talents={build_spec.class_talents}")
    if build_spec.spec_talents:
        lines.append(f"spec_talents={build_spec.spec_talents}")
    if build_spec.hero_talents:
        lines.append(f"hero_talents={build_spec.hero_talents}")
    return "\n".join(lines) + "\n"


def parse_debug_talents(output: str) -> dict[str, list[DecodedTalent]]:
    talents_by_tree: dict[str, list[DecodedTalent]] = {"class": [], "spec": [], "hero": [], "selection": []}
    for line in output.splitlines():
        match = TALENT_DEBUG_RE.search(line)
        if not match:
            continue
        tree = match.group("tree")
        name = match.group("name")
        if tree == "selection":
            continue
        talents_by_tree[tree].append(
            DecodedTalent(
                tree=tree,
                name=name,
                token=tokenize_talent_name(name),
                rank=int(match.group("rank")),
                max_rank=int(match.group("max_rank")),
            )
        )
    return talents_by_tree


def normalize_talents_input(value: str | None) -> str | None:
    if not value:
        return None
    stripped = value.strip()
    if stripped.startswith("talents="):
        return stripped.split("=", 1)[1].strip()
    wowhead_ref = parse_wowhead_talent_calc_ref(stripped)
    if wowhead_ref is not None and wowhead_ref.talents:
        return wowhead_ref.talents
    return stripped


def detect_talents_option_source_kind(
    *,
    talents: str | None,
    class_talents: str | None,
    spec_talents: str | None,
    hero_talents: str | None,
) -> str | None:
    if class_talents or spec_talents or hero_talents:
        return "simc_split_talents"
    if not talents:
        return None
    stripped = talents.strip()
    if parse_wowhead_talent_calc_ref(stripped) is not None:
        return "wowhead_talent_calc_url"
    if stripped.startswith("talents="):
        return "simc_profile"
    return "wow_talent_export"


def load_build_spec(
    *,
    apl_path: str | Path | None,
    profile_path: str | None,
    build_file: str | None,
    build_text: str | None,
    talents: str | None,
    class_talents: str | None,
    spec_talents: str | None,
    hero_talents: str | None,
    actor_class: str | None,
    spec_name: str | None,
) -> BuildSpec:
    inferred = BuildSpec()
    if apl_path:
        inferred_class, inferred_spec = infer_actor_and_spec_from_apl(apl_path)
        inferred.actor_class = inferred_class
        inferred.spec = inferred_spec
        if inferred.actor_class or inferred.spec:
            inferred.source_notes.append(f"inferred from apl: {Path(apl_path).stem}")

    from_talents_option = BuildSpec()
    if talents:
        from_talents_option = parse_wowhead_talent_calc_ref(talents) or BuildSpec()
        if from_talents_option.source_notes:
            from_talents_option.source_notes.append("command-line talents option")

    explicit = BuildSpec(
        actor_class=actor_class,
        spec=spec_name,
        talents=normalize_talents_input(talents),
        class_talents=class_talents,
        spec_talents=spec_talents,
        hero_talents=hero_talents,
        source_kind=detect_talents_option_source_kind(
            talents=talents,
            class_talents=class_talents,
            spec_talents=spec_talents,
            hero_talents=hero_talents,
        ),
        source_notes=["command-line build options"] if any([talents, class_talents, spec_talents, hero_talents, actor_class, spec_name]) else [],
    )

    from_profile = BuildSpec()
    if profile_path:
        resolved = Path(profile_path).expanduser().resolve()
        from_profile = extract_build_spec_from_text(resolved.read_text())
        from_profile.source_notes.append(f"profile: {resolved}")

    from_build_file = BuildSpec()
    if build_file:
        resolved = Path(build_file).expanduser().resolve()
        from_build_file = extract_build_spec_from_text(resolved.read_text())
        from_build_file.source_notes.append(f"build file: {resolved}")

    from_build_text = BuildSpec()
    if build_text:
        from_build_text = extract_build_spec_from_text(build_text)
        from_build_text.source_notes.append("inline build text")

    return merge_build_specs(inferred, from_profile, from_build_file, from_build_text, from_talents_option, explicit)


def identify_build(repo: RepoPaths, build_spec: BuildSpec) -> tuple[BuildSpec, BuildIdentity]:
    if build_spec.actor_class and build_spec.spec:
        source = "direct"
        confidence = "high"
        if build_spec.source_kind == "wowhead_talent_calc_url":
            source = "wowhead_talent_calc_url"
        elif any(note.startswith("inferred from apl:") for note in build_spec.source_notes):
            source = "apl_path"
        return (
            build_spec,
            BuildIdentity(
                actor_class=build_spec.actor_class,
                spec=build_spec.spec,
                confidence=confidence,
                source=source,
                candidate_count=1,
                candidates=[(build_spec.actor_class, build_spec.spec)],
                source_notes=build_spec.source_notes[:],
            ),
        )

    # Without talent data there is nothing reliable to probe.
    if not any([build_spec.talents, build_spec.class_talents, build_spec.spec_talents, build_spec.hero_talents]):
        return (
            build_spec,
            BuildIdentity(
                actor_class=build_spec.actor_class,
                spec=build_spec.spec,
                confidence="none",
                source="missing_build_data",
                candidate_count=0,
                source_notes=build_spec.source_notes[:],
            ),
        )

    candidate_specs = supported_specs(repo)
    if build_spec.actor_class:
        candidate_specs = [item for item in candidate_specs if item[0] == build_spec.actor_class]
    if build_spec.spec:
        candidate_specs = [item for item in candidate_specs if item[1] == build_spec.spec]

    matches: list[tuple[str, str]] = []
    for actor_class, spec in candidate_specs:
        probe_spec = BuildSpec(
            actor_class=actor_class,
            spec=spec,
            talents=build_spec.talents,
            class_talents=build_spec.class_talents,
            spec_talents=build_spec.spec_talents,
            hero_talents=build_spec.hero_talents,
            source_kind=build_spec.source_kind,
            source_notes=build_spec.source_notes[:],
        )
        try:
            resolution = decode_build(repo, probe_spec)
        except (FileNotFoundError, RuntimeError, ValueError):
            continue
        if resolution.enabled_talents:
            matches.append((actor_class, spec))

    if len(matches) == 1:
        actor_class, spec = matches[0]
        identified = merge_build_specs(build_spec, BuildSpec(actor_class=actor_class, spec=spec))
        identified.source_notes.append("identified by SimC probe")
        return (
            identified,
            BuildIdentity(
                actor_class=actor_class,
                spec=spec,
                confidence="high",
                source="simc_probe",
                candidate_count=len(matches),
                candidates=matches,
                source_notes=identified.source_notes[:],
            ),
        )

    return (
        build_spec,
        BuildIdentity(
            actor_class=build_spec.actor_class,
            spec=build_spec.spec,
            confidence="low" if matches else "none",
            source="simc_probe",
            candidate_count=len(matches),
            candidates=matches,
            source_notes=build_spec.source_notes[:],
        ),
    )


def decode_build(repo: RepoPaths, build_spec: BuildSpec) -> BuildResolution:
    if not build_spec.actor_class or not build_spec.spec:
        raise ValueError("Need both actor class and spec to decode talent strings.")
    if not any([build_spec.talents, build_spec.class_talents, build_spec.spec_talents, build_spec.hero_talents]):
        return BuildResolution(
            actor_class=build_spec.actor_class,
            spec=build_spec.spec,
            enabled_talents=set(),
            talents_by_tree={"class": [], "spec": [], "hero": [], "selection": []},
            source_kind=build_spec.source_kind,
            generated_profile_text=None,
            source_notes=build_spec.source_notes[:],
        )
    if not repo.build_simc.exists():
        raise FileNotFoundError(f"SimC binary not found: {repo.build_simc}")

    profile_text = build_profile_text(build_spec)
    temp_dir = Path(tempfile.mkdtemp(prefix="simc-cli-build-"))
    profile_path = temp_dir / "decode.simc"
    profile_path.write_text(profile_text)

    cmd = [
        str(repo.build_simc),
        str(profile_path),
        "iterations=1",
        "max_time=1",
        "vary_combat_length=0",
        "desired_targets=1",
        "fight_style=Patchwerk",
        "debug=1",
        "allow_experimental_specializations=1",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output = proc.stdout + proc.stderr
    talents_by_tree = parse_debug_talents(output)
    enabled_talents = {
        talent.token
        for talents in talents_by_tree.values()
        for talent in talents
        if talent.tree in {"class", "spec", "hero"} and talent.rank > 0
    }
    if not enabled_talents and proc.returncode != 0:
        raise RuntimeError(output.strip() or "Failed to decode build with simc")
    notes = build_spec.source_notes[:] + [f"decoded via {repo.build_simc}"]
    return BuildResolution(
        actor_class=build_spec.actor_class,
        spec=build_spec.spec,
        enabled_talents=enabled_talents,
        talents_by_tree=talents_by_tree,
        source_kind=build_spec.source_kind,
        generated_profile_text=profile_text,
        source_notes=notes,
    )
