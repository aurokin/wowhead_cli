from __future__ import annotations

from warcraft_wiki_cli.page_parser import normalize_article_ref, parse_article_page


def test_normalize_article_ref_handles_wiki_paths() -> None:
    assert normalize_article_ref("/wiki/World_of_Warcraft_API") == "World of Warcraft API"


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
