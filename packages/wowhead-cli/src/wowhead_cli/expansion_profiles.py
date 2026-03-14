from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

WOWHEAD_ROOT = "https://www.wowhead.com"
NETHER_ROOT = "https://nether.wowhead.com"


@dataclass(frozen=True, slots=True)
class ExpansionProfile:
    key: str
    label: str
    path_prefix: str
    data_env: int
    aliases: tuple[str, ...]
    legacy_subdomains: tuple[str, ...]

    @property
    def wowhead_base(self) -> str:
        if self.path_prefix:
            return f"{WOWHEAD_ROOT}/{self.path_prefix}"
        return WOWHEAD_ROOT

    @property
    def nether_base(self) -> str:
        if self.path_prefix:
            return f"{NETHER_ROOT}/{self.path_prefix}"
        return NETHER_ROOT


_PROFILES: tuple[ExpansionProfile, ...] = (
    ExpansionProfile(
        key="retail",
        label="Retail / Default",
        path_prefix="",
        data_env=1,
        aliases=("default", "live", "wowhead"),
        legacy_subdomains=("wowhead.com", "www.wowhead.com"),
    ),
    ExpansionProfile(
        key="classic",
        label="Classic Era",
        path_prefix="classic",
        data_env=4,
        aliases=("vanilla",),
        legacy_subdomains=("classic.wowhead.com",),
    ),
    ExpansionProfile(
        key="tbc",
        label="Burning Crusade Classic",
        path_prefix="tbc",
        data_env=5,
        aliases=("burning-crusade", "bc"),
        legacy_subdomains=("tbc.wowhead.com",),
    ),
    ExpansionProfile(
        key="wotlk",
        label="Wrath of the Lich King Classic",
        path_prefix="wotlk",
        data_env=8,
        aliases=("wrath",),
        legacy_subdomains=("wotlk.wowhead.com", "wrath.wowhead.com"),
    ),
    ExpansionProfile(
        key="cata",
        label="Cataclysm Classic",
        path_prefix="cata",
        data_env=11,
        aliases=("cataclysm",),
        legacy_subdomains=("cata.wowhead.com", "cataclysm.wowhead.com"),
    ),
    ExpansionProfile(
        key="mop-classic",
        label="Mists of Pandaria Classic",
        path_prefix="mop-classic",
        data_env=15,
        aliases=("mop", "mists"),
        legacy_subdomains=("mists.wowhead.com", "mop.wowhead.com"),
    ),
    ExpansionProfile(
        key="ptr",
        label="Retail PTR",
        path_prefix="ptr",
        data_env=2,
        aliases=(),
        legacy_subdomains=("ptr.wowhead.com",),
    ),
    ExpansionProfile(
        key="beta",
        label="Retail Beta",
        path_prefix="beta",
        data_env=3,
        aliases=(),
        legacy_subdomains=("beta.wowhead.com",),
    ),
    ExpansionProfile(
        key="classic-ptr",
        label="Classic PTR",
        path_prefix="classic-ptr",
        data_env=14,
        aliases=("classicptr",),
        legacy_subdomains=("classicptr.wowhead.com",),
    ),
)

_BY_KEY = {profile.key: profile for profile in _PROFILES}
_ALIAS_TO_KEY: dict[str, str] = {}
for profile in _PROFILES:
    _ALIAS_TO_KEY[profile.key] = profile.key
    for alias in profile.aliases:
        _ALIAS_TO_KEY[alias] = profile.key


def list_profiles() -> tuple[ExpansionProfile, ...]:
    return _PROFILES


def normalize_expansion_key(value: str) -> str:
    return value.strip().lower().replace("_", "-")


def resolve_expansion(value: str | None) -> ExpansionProfile:
    if value is None or value.strip() == "":
        return _BY_KEY["retail"]
    normalized = normalize_expansion_key(value)
    key = _ALIAS_TO_KEY.get(normalized)
    if key is None:
        options = ", ".join(profile.key for profile in _PROFILES)
        raise ValueError(f"Unknown expansion {value!r}. Supported: {options}")
    return _BY_KEY[key]


def build_entity_url(profile: ExpansionProfile, entity_type: str, entity_id: int) -> str:
    return f"{profile.wowhead_base}/{entity_type}={entity_id}"


def build_guide_lookup_url(profile: ExpansionProfile, guide_id: int) -> str:
    return f"{profile.wowhead_base}/guide={guide_id}"


def build_search_url(profile: ExpansionProfile, query: str) -> str:
    return f"{profile.wowhead_base}/search?q={quote(query)}"


def build_search_suggestions_url(profile: ExpansionProfile) -> str:
    return f"{profile.wowhead_base}/search/suggestions-template"


def build_comment_replies_url(profile: ExpansionProfile) -> str:
    return f"{profile.wowhead_base}/comment/show-replies"


def build_tooltip_url(profile: ExpansionProfile, entity_type: str, entity_id: int) -> str:
    return f"{profile.nether_base}/tooltip/{entity_type}/{entity_id}"


def build_news_url(profile: ExpansionProfile, *, page: int = 1) -> str:
    url = f"{profile.wowhead_base}/news"
    if page > 1:
        return f"{url}?page={page}"
    return url


def build_blue_tracker_url(profile: ExpansionProfile, *, page: int = 1) -> str:
    url = f"{profile.wowhead_base}/blue-tracker"
    if page > 1:
        return f"{url}?page={page}"
    return url


def build_guide_category_url(profile: ExpansionProfile, category: str) -> str:
    slug = category.strip().strip("/")
    return f"{profile.wowhead_base}/guides/{quote(slug)}"
