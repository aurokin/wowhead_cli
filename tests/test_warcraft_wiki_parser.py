from __future__ import annotations

from warcraft_wiki_cli.page_parser import classify_article_family, normalize_article_ref, parse_article_page


def test_normalize_article_ref_handles_wiki_paths() -> None:
    assert normalize_article_ref("/wiki/World_of_Warcraft_API") == "World of Warcraft API"


def test_classify_article_family_handles_programming_and_system_titles() -> None:
    assert classify_article_family("API CreateFrame") == "api_function"
    assert classify_article_family("UIHANDLER OnKeyDown") == "ui_handler"
    assert classify_article_family("API change summaries") == "api_changes"
    assert classify_article_family("World of Warcraft API") == "framework_page"
    assert classify_article_family("Widget API") == "framework_page"
    assert classify_article_family("Create a WoW AddOn in 15 Minutes") == "howto_programming"
    assert classify_article_family("XML schema") == "xml_schema"
    assert classify_article_family("Patch 2.2.0/API changes") == "api_changes"
    assert classify_article_family("Renown") == "system_reference"
    assert classify_article_family("Druid") == "class_reference"
    assert classify_article_family("Profession") == "profession_reference"
    assert classify_article_family("Zone scaling") == "zone_reference"


def test_parse_article_page_uses_mw_parser_output_root() -> None:
    payload = {
        "parse": {
            "title": "World of Warcraft API",
            "displaytitle": "<span class='mw-page-title-main'>World of Warcraft API</span>",
            "sections": [
                {"line": "API systems", "anchor": "API_systems"},
                {"line": "Object APIs", "anchor": "Object_APIs"},
            ],
            "text": {
                "*": """
                <div class="mw-parser-output">
                  <p>Intro copy.</p>
                  <h2><span class="mw-headline" id="API_systems">API systems</span></h2>
                  <p>FrameXML reference.</p>
                  <h2><span class="mw-headline" id="Object_APIs">Object APIs</span></h2>
                  <p><a href="/wiki/UIOBJECT_Frame">UIOBJECT Frame</a></p>
                </div>
                """
            },
        }
    }

    parsed = parse_article_page(payload, source_title="World of Warcraft API")

    assert parsed["article"]["title"] == "World of Warcraft API"
    assert parsed["article_content"]["headings"][0]["title"] == "API systems"
    assert len(parsed["article_content"]["sections"]) >= 2
    assert parsed["linked_entities"][0]["id"] == "UIOBJECT Frame"


def test_parse_article_page_extracts_programming_reference_and_filters_edit_links() -> None:
    payload = {
        "parse": {
            "title": "API CreateFrame",
            "displaytitle": "<span class='mw-page-title-main'>CreateFrame</span>",
            "sections": [
                {"line": "Arguments", "anchor": "Arguments"},
                {"line": "Returns", "anchor": "Returns"},
                {"line": "Example", "anchor": "Example"},
            ],
            "text": {
                "*": """
                <div class="mw-parser-output">
                  <div class="nomobile">Main Menu WoW API Lua API FrameXML API</div>
                  <div>Game Types mainline Links GitHub search Globe Wowprogramming</div>
                  <p>Creates a Frame object.</p>
                  <div class="mw-highlight">frame = CreateFrame(frameType)</div>
                  <h2><span class="mw-headline" id="Arguments">Arguments</span><span class="mw-editsection"><a href="/wiki/API_CreateFrame?action=edit&section=1">edit</a></span></h2>
                  <p>frameType string</p>
                  <h2><span class="mw-headline" id="Returns">Returns</span></h2>
                  <p>frame Frame</p>
                  <h2><span class="mw-headline" id="Example">Example</span></h2>
                  <p><a href="/wiki/API_CreateFramePool">CreateFramePool</a></p>
                </div>
                """
            },
        }
    }

    parsed = parse_article_page(payload, source_title="API CreateFrame")

    assert parsed["article"]["content_family"] == "api_function"
    assert parsed["reference"]["content_family"] == "api_function"
    assert parsed["reference"]["programming_reference"] is True
    assert parsed["reference"]["signature"] == "frame = CreateFrame(frameType)"
    assert parsed["reference"]["arguments"] == "frameType string"
    assert parsed["reference"]["returns"] == "frame Frame"
    assert "Main Menu" not in parsed["article_content"]["text"]
    assert "Wowprogramming" not in parsed["article_content"]["text"]
    assert all("action=edit" not in row["url"] for row in parsed["linked_entities"])


def test_parse_article_page_extracts_non_programming_reference_metadata() -> None:
    payload = {
        "parse": {
            "title": "Druid",
            "displaytitle": "<span class='mw-page-title-main'>Druid</span>",
            "sections": [
                {"line": "Class overview", "anchor": "Class_overview"},
                {"line": "Patch changes", "anchor": "Patch_changes"},
                {"line": "See also", "anchor": "See_also"},
                {"line": "References", "anchor": "References"},
            ],
            "text": {
                "*": """
                <div class="mw-parser-output">
                  <p>Druids are shapeshifting hybrids.</p>
                  <h2><span class="mw-headline" id="Class_overview">Class overview</span></h2>
                  <p>Versatile class overview.</p>
                  <h2><span class="mw-headline" id="Patch_changes">Patch changes</span></h2>
                  <p>Patch 10.0.0 adjusted forms.</p>
                  <h2><span class="mw-headline" id="See_also">See also</span></h2>
                  <p>Druid abilities</p>
                  <h2><span class="mw-headline" id="References">References</span></h2>
                  <p>Chronicle.</p>
                </div>
                """
            },
        }
    }

    parsed = parse_article_page(payload, source_title="Druid")

    assert parsed["article"]["content_family"] == "class_reference"
    assert parsed["reference"]["content_family"] == "class_reference"
    assert parsed["reference"]["summary"].startswith("Druids are shapeshifting hybrids.")
    assert parsed["reference"]["patch_changes"] == "Patch 10.0.0 adjusted forms."
    assert parsed["reference"]["see_also"] == "Druid abilities"
    assert parsed["reference"]["references"] == "Chronicle."


def test_parse_article_page_refines_general_family_to_faction_reference() -> None:
    payload = {
        "parse": {
            "title": "Argent Dawn",
            "displaytitle": "<span class='mw-page-title-main'>Argent Dawn</span>",
            "sections": [
                {"line": "History", "anchor": "History"},
                {"line": "Members", "anchor": "Members"},
                {"line": "Reputation", "anchor": "Reputation"},
                {"line": "Patch changes", "anchor": "Patch_changes"},
            ],
            "text": {
                "*": """
                <div class="mw-parser-output">
                  <p>The Argent Dawn is a holy order.</p>
                  <h2><span class="mw-headline" id="History">History</span></h2>
                  <p>Founded to fight the Scourge.</p>
                  <h2><span class="mw-headline" id="Members">Members</span></h2>
                  <p>Tirion Fordring.</p>
                  <h2><span class="mw-headline" id="Reputation">Reputation</span></h2>
                  <p>Faction rewards and standing.</p>
                  <h2><span class="mw-headline" id="Patch_changes">Patch changes</span></h2>
                  <p>Patch 3.0.2 updated reputation.</p>
                </div>
                """
            },
        }
    }

    parsed = parse_article_page(payload, source_title="Argent Dawn")

    assert parsed["article"]["content_family"] == "faction_reference"
    assert parsed["reference"]["content_family"] == "faction_reference"
    assert parsed["reference"]["summary"].startswith("The Argent Dawn is a holy order.")


def test_parse_article_page_refines_general_family_to_lore_reference() -> None:
    payload = {
        "parse": {
            "title": "Jaina Proudmoore",
            "displaytitle": "<span class='mw-page-title-main'>Jaina Proudmoore</span>",
            "sections": [
                {"line": "Biography", "anchor": "Biography"},
                {"line": "Patch changes", "anchor": "Patch_changes"},
            ],
            "text": {
                "*": """
                <div class="mw-parser-output">
                  <p>Jaina Proudmoore is a powerful sorceress.</p>
                  <h2><span class="mw-headline" id="Biography">Biography</span></h2>
                  <p>Leader of the Kirin Tor.</p>
                  <h2><span class="mw-headline" id="Patch_changes">Patch changes</span></h2>
                  <p>Patch 8.1.0 updated her model.</p>
                </div>
                """
            },
        }
    }

    parsed = parse_article_page(payload, source_title="Jaina Proudmoore")

    assert parsed["article"]["content_family"] == "lore_reference"
    assert parsed["reference"]["content_family"] == "lore_reference"
    assert parsed["reference"]["patch_changes"] == "Patch 8.1.0 updated her model."


def test_parse_article_page_refines_general_family_to_zone_reference_and_strips_comments() -> None:
    payload = {
        "parse": {
            "title": "Elwynn Forest",
            "displaytitle": "<span class='mw-page-title-main'>Elwynn Forest</span>",
            "sections": [
                {"line": "Geography", "anchor": "Geography"},
                {"line": "Maps and subregions", "anchor": "Maps_and_subregions"},
                {"line": "Quest and travel hubs", "anchor": "Quest_and_travel_hubs"},
                {"line": "Patch changes", "anchor": "Patch_changes"},
            ],
            "text": {
                "*": """
                <div class="mw-parser-output">
                  <table class="infobox"><tr><td>Zone infobox content</td></tr></table>
                  <p>Elwynn Forest is a human starting zone.</p>
                  <h2><span class="mw-headline" id="Geography">Geography</span></h2>
                  <p>Forests and rivers.</p>
                  <h2><span class="mw-headline" id="Maps_and_subregions">Maps and subregions</span></h2>
                  <p>Goldshire and Northshire.</p>
                  <h2><span class="mw-headline" id="Quest_and_travel_hubs">Quest and travel hubs</span></h2>
                  <p>Goldshire questing hub.</p>
                  <h2><span class="mw-headline" id="Patch_changes">Patch changes</span></h2>
                  <p>Patch 7.3.5 added scaling.</p>
                </div>
                <!-- Saved in parser cache with key something -->
                """
            },
        }
    }

    parsed = parse_article_page(payload, source_title="Elwynn Forest")

    assert parsed["article"]["content_family"] == "zone_reference"
    assert parsed["reference"]["content_family"] == "zone_reference"
    assert "Zone infobox content" not in parsed["article_content"]["text"]
    assert "Saved in parser cache" not in parsed["article_content"]["text"]
