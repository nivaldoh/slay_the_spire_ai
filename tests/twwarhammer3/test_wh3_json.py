"""WH3's JSON codec under Lua 5.1 and the game's UTF-8 string.sub override."""
import json

import pytest
from wh3_lua import MOD, runtime


def utf8_sub(text, start, end=None):
    """The game's documented character indices, unlike Lua's original byte indices."""
    if start < 0:
        start += len(text) + 1
    if end is None:
        end = len(text)
    elif end < 0:
        end += len(text) + 1
    return text[max(start, 1) - 1:end]


@pytest.mark.parametrize("game_string_sub", [False, True])
def test_json_preserves_nested_unicode_with_standard_or_game_string_sub(game_string_sub):
    lua = runtime()
    if game_string_sub:
        lua.globals().utf8_sub = utf8_sub
        lua.execute("string.sub_lua = string.sub; string.sub = utf8_sub")
        assert lua.eval("string.sub('éx', 2, 2)") == "x"
        assert lua.eval("string.byte(string.sub_lua('éx', 1, 1))") == 195
    assert lua.eval("#'éx'") == 3  # The parser's length and byte methods still count bytes.
    codec = lua.execute((MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())
    expected = {
        "captures": [{"name": "Königsplatz – 小型補給地点", "owner": 2, "progress": 0.625}],
        "armée": {"name": "Bâtiment clé", "escaped": 'tower "one"\\gate\nline',
                  "count": -17, "enabled": False},
        "tail": [3.5, True, "😀"],
    }
    # Both raw UTF-8 (the mod's encoder output) and JSON Unicode escapes have the same value.
    for ascii_only in (False, True):
        encoded = json.dumps(expected, ensure_ascii=ascii_only)
        assert json.loads(codec.encode(codec.decode(encoded))) == expected
