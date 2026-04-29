from jupyter_ai_acp_bridge.mention_resolver import resolve_mentions


def test_plain_text_returns_single_text_block():
    blocks = resolve_mentions("hello world", persona_names={"jupyternaut"})
    assert blocks == [{"type": "text", "text": "hello world"}]


def test_persona_mention_left_as_plain_text():
    blocks = resolve_mentions("@jupyternaut summarize", persona_names={"jupyternaut"})
    assert blocks == [{"type": "text", "text": "@jupyternaut summarize"}]


def test_filepath_mention_becomes_resource_link():
    blocks = resolve_mentions(
        "look at @README.md please",
        persona_names=set(),
        cwd="/tmp/proj",
        file_resolver=lambda p: f"/tmp/proj/{p}" if p == "README.md" else None,
    )
    # expect: text "look at ", ResourceLink, text " please"
    assert len(blocks) == 3
    assert blocks[0] == {"type": "text", "text": "look at "}
    assert blocks[1] == {
        "type": "resource_link",
        "uri": "file:///tmp/proj/README.md",
        "name": "README.md",
    }
    assert blocks[2] == {"type": "text", "text": " please"}


def test_unresolved_at_word_left_as_text():
    blocks = resolve_mentions(
        "what is @nonexistent",
        persona_names=set(),
        cwd="/tmp",
        file_resolver=lambda p: None,
    )
    assert blocks == [{"type": "text", "text": "what is @nonexistent"}]
