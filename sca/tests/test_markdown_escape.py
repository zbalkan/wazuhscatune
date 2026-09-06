from sca.internal.guide import escape_markdown


def test_markdown_structure_characters_are_escaped():
    value = '# heading\n---\n- item\n> quote\n*em* _em_ `code`'
    escaped = escape_markdown(value)

    assert '\\# heading' in escaped
    assert '\\-\\-\\-' in escaped
    assert '\\- item' in escaped
    assert '&gt; quote' in escaped
    assert '\\*em\\*' in escaped
    assert '\\_em\\_' in escaped
    assert '\\`code\\`' in escaped
