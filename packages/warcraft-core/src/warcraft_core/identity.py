from __future__ import annotations

import re
from typing import Literal
from urllib.parse import urljoin, urlparse, urlunparse

from warcraft_core.wow_normalization import normalized_text

IdentityStatus = Literal["unknown", "normalized", "canonical", "inferred", "ambiguous"]
IdentityConfidence = Literal["none", "low", "medium", "high"]
WOWHEAD_TALENT_CALC_SEGMENT = "talent-calc"


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _clean_notes(notes: list[str] | tuple[str, ...] | None) -> list[str]:
    if not notes:
        return []
    cleaned: list[str] = []
    for note in notes:
        text = _clean_text(note)
        if text:
            cleaned.append(text)
    return cleaned


def normalize_actor_class(value: str | None) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    normalized = re.sub(r"[^a-z0-9]+", "", text.lower())
    return normalized or None


def normalize_spec_name(value: str | None) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    normalized = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return normalized or None


def normalize_encounter_name(value: str | None) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    normalized = normalized_text(text)
    return normalized.replace(" ", "-") if normalized else None


def normalize_ability_name(value: str | None) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    normalized = normalized_text(text)
    return normalized.replace(" ", "_") if normalized else None


def parse_wowhead_talent_calc_ref(ref: str) -> dict[str, str | None] | None:
    candidate = _clean_text(ref)
    if candidate is None:
        return None
    parsed = urlparse(candidate)
    if parsed.scheme and parsed.netloc:
        if "wowhead.com" not in parsed.netloc:
            return None
        reference_url = urlunparse(parsed._replace(query="", fragment=""))
    else:
        reference_url = urljoin("https://www.wowhead.com", candidate if candidate.startswith("/") else f"/{candidate}")
        parsed = urlparse(reference_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    try:
        talent_calc_index = path_parts.index(WOWHEAD_TALENT_CALC_SEGMENT)
    except ValueError:
        return None
    if len(path_parts) < talent_calc_index + 3:
        return None
    actor_class = normalize_actor_class(path_parts[talent_calc_index + 1])
    spec = normalize_spec_name(path_parts[talent_calc_index + 2])
    build_code = path_parts[talent_calc_index + 3] if len(path_parts) > talent_calc_index + 3 else None
    if not actor_class or not spec:
        return None
    return {
        "actor_class": actor_class,
        "spec": spec,
        "build_code": _clean_text(build_code),
        "reference_url": reference_url,
        "source_kind": "wowhead_talent_calc_url",
    }


def class_spec_identity_payload(
    *,
    actor_class: str | None,
    spec: str | None,
    provider: str | None = None,
    source: str | None = None,
    confidence: IdentityConfidence = "none",
    canonical: bool = False,
    inferred: bool = False,
    candidates: list[tuple[str | None, str | None]] | None = None,
    notes: list[str] | tuple[str, ...] | None = None,
) -> dict[str, object]:
    normalized_actor_class = normalize_actor_class(actor_class)
    normalized_spec = normalize_spec_name(spec)
    candidate_rows = [
        {
            "actor_class": normalize_actor_class(candidate_actor_class),
            "spec": normalize_spec_name(candidate_spec),
        }
        for candidate_actor_class, candidate_spec in (candidates or [])
    ]
    cleaned_notes = _clean_notes(notes)
    if canonical and normalized_actor_class and normalized_spec:
        status: IdentityStatus = "canonical"
    elif inferred and normalized_actor_class and normalized_spec:
        status = "inferred"
    elif len(candidate_rows) > 1 and not (normalized_actor_class and normalized_spec):
        status = "ambiguous"
    elif normalized_actor_class or normalized_spec:
        status = "normalized"
    else:
        status = "unknown"
    payload: dict[str, object] = {
        "kind": "class_spec_identity",
        "status": status,
        "confidence": confidence,
        "identity": {
            "actor_class": normalized_actor_class,
            "spec": normalized_spec,
        },
        "candidate_count": len(candidate_rows),
        "candidates": candidate_rows,
        "notes": cleaned_notes,
    }
    if provider is not None or source is not None:
        payload["source"] = {"provider": provider, "source": source}
    return payload


def encounter_identity_payload(
    *,
    encounter_id: int | None,
    journal_id: int | None = None,
    name: str | None = None,
    zone_id: int | None = None,
    provider: str | None = None,
    source: str | None = None,
    notes: list[str] | tuple[str, ...] | None = None,
) -> dict[str, object]:
    normalized_name = normalize_encounter_name(name)
    status: IdentityStatus = "canonical" if encounter_id is not None or journal_id is not None else ("normalized" if normalized_name else "unknown")
    payload: dict[str, object] = {
        "kind": "encounter_identity",
        "status": status,
        "identity": {
            "encounter_id": encounter_id,
            "journal_id": journal_id,
            "zone_id": zone_id,
            "normalized_name": normalized_name,
        },
        "notes": _clean_notes(notes),
    }
    if provider is not None or source is not None:
        payload["source"] = {"provider": provider, "source": source}
    return payload


def ability_identity_payload(
    *,
    spell_id: int | None = None,
    game_id: int | None = None,
    name: str | None = None,
    provider: str | None = None,
    source: str | None = None,
    notes: list[str] | tuple[str, ...] | None = None,
) -> dict[str, object]:
    normalized_name = normalize_ability_name(name)
    status: IdentityStatus = "canonical" if spell_id is not None or game_id is not None else ("normalized" if normalized_name else "unknown")
    payload: dict[str, object] = {
        "kind": "ability_identity",
        "status": status,
        "identity": {
            "spell_id": spell_id,
            "game_id": game_id,
            "normalized_name": normalized_name,
        },
        "notes": _clean_notes(notes),
    }
    if provider is not None or source is not None:
        payload["source"] = {"provider": provider, "source": source}
    return payload


def report_actor_identity_payload(
    *,
    report_code: str | None,
    fight_id: int | None,
    actor_id: int | None,
    name: str | None = None,
    actor_class: str | None = None,
    spec: str | None = None,
    provider: str | None = None,
    source: str | None = None,
    notes: list[str] | tuple[str, ...] | None = None,
) -> dict[str, object]:
    local_key = f"{report_code}:{fight_id}:{actor_id}" if report_code and fight_id is not None and actor_id is not None else None
    status: IdentityStatus = "canonical" if local_key is not None else ("normalized" if any((name, actor_class, spec)) else "unknown")
    payload: dict[str, object] = {
        "kind": "report_actor_identity",
        "status": status,
        "scope": {
            "type": "report_fight",
            "report_code": report_code,
            "fight_id": fight_id,
        },
        "identity": {
            "actor_id": actor_id,
            "local_key": local_key,
            "name": _clean_text(name),
            "actor_class": normalize_actor_class(actor_class),
            "spec": normalize_spec_name(spec),
        },
        "notes": _clean_notes(notes),
    }
    if provider is not None or source is not None:
        payload["source"] = {"provider": provider, "source": source}
    return payload


def build_identity_payload(
    *,
    actor_class: str | None,
    spec: str | None,
    confidence: IdentityConfidence,
    source: str,
    candidates: list[tuple[str | None, str | None]] | None = None,
    source_notes: list[str] | tuple[str, ...] | None = None,
) -> dict[str, object]:
    normalized_actor_class = normalize_actor_class(actor_class)
    normalized_spec = normalize_spec_name(spec)
    candidate_rows = [
        {
            "actor_class": normalize_actor_class(candidate_actor_class),
            "spec": normalize_spec_name(candidate_spec),
        }
        for candidate_actor_class, candidate_spec in (candidates or [])
    ]
    if normalized_actor_class and normalized_spec:
        status: IdentityStatus = "inferred"
    elif len(candidate_rows) > 1:
        status = "ambiguous"
    else:
        status = "unknown"
    return {
        "kind": "build_identity",
        "status": status,
        "confidence": confidence,
        "canonical": False,
        "source": source,
        "class_spec_identity": class_spec_identity_payload(
            actor_class=normalized_actor_class,
            spec=normalized_spec,
            source=source,
            confidence=confidence,
            inferred=bool(normalized_actor_class and normalized_spec),
            candidates=[(row["actor_class"], row["spec"]) for row in candidate_rows],
            notes=source_notes,
        ),
        "candidate_count": len(candidate_rows),
        "candidates": candidate_rows,
        "source_notes": _clean_notes(source_notes),
    }


def build_reference_payload(
    *,
    ref: str,
    provider: str | None = None,
    source: str | None = None,
    source_url: str | None = None,
    label: str | None = None,
    notes: list[str] | tuple[str, ...] | None = None,
) -> dict[str, object] | None:
    parsed = parse_wowhead_talent_calc_ref(ref)
    if parsed is None:
        return None
    source_notes = ["class/spec came from the explicit Wowhead talent-calc URL path"]
    if parsed["build_code"] is not None:
        source_notes.append("wowhead build code")
    source_notes.extend(_clean_notes(notes))
    payload: dict[str, object] = {
        "kind": "build_reference",
        "reference_type": "wowhead_talent_calc_url",
        "url": parsed["reference_url"],
        "label": _clean_text(label),
        "build_code": parsed["build_code"],
        "source_url": source_url,
        "build_identity": build_identity_payload(
            actor_class=parsed["actor_class"],
            spec=parsed["spec"],
            confidence="high",
            source="wowhead_talent_calc_url",
            source_notes=source_notes,
        ),
    }
    if provider is not None or source is not None:
        payload["source"] = {"provider": provider, "source": source}
    return payload
