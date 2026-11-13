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


def codec():
    lua = runtime()
    return lua, lua.execute((MOD / "script/_lib/mod/twwarhammer3_json.lua").read_text())


# The refusals of rxi/json.lua 0.1.2, whose own test/test.lua checks that these raise. Here each
# names its reason: the mod logs that reason, and without its refusal each case below instead
# writes invalid JSON, silently drops values, or fails later with an unrelated Lua error
# (2026-11-13 refusal sweep and review). Lua 5.1's length of a table with a hole may count past
# it, so the sparse-array check alone lets {1, nil, 3, x = 1} through as [1].
ENCODE_REFUSALS = [
    ("local t = {}; t.self = t; return t", "circular reference"),
    ("return {[1] = 1, [3] = 3}", "invalid table: sparse array"),
    ("return {1, nil, 3, x = 1}", "invalid table: mixed or invalid key types"),
    ("return {x = 1, [2] = 2}", "invalid table: mixed or invalid key types"),
    ("return {[true] = 1}", "invalid table: mixed or invalid key types"),
    ("return {0 / 0}", "unexpected number value"),
    ("return {1 / 0}", "unexpected number value"),
    ("return {-1 / 0}", "unexpected number value"),
    ("return {1, function() end}", "unexpected type 'function'"),
]


@pytest.mark.parametrize("value,reason", ENCODE_REFUSALS, ids=[r for _, r in ENCODE_REFUSALS])
def test_the_encoder_refuses_what_json_cannot_hold_and_names_why(value, reason):
    lua, json_codec = codec()
    lua.globals().codec = json_codec
    ok, error = lua.execute(f"return pcall(codec.encode, (function() {value} end)())")
    assert ok is False and reason in str(error)


# Truncated files are what a reader can meet while the other side is still writing.
DECODE_REFUSALS = [
    ('{"orders": [1, 2', "expected ']' or ','"),
    ('{"a": 1', "expected '}' or ','"),
    ('{"a" 1}', "expected ':' after key"),
    ("[1] x", "trailing garbage"),
    ("nul", "invalid literal 'nul'"),
    ("@", "unexpected character '@'"),
    ('"\\udbff\\uffff"', "invalid unicode codepoint"),
]


@pytest.mark.parametrize("text,reason", DECODE_REFUSALS, ids=[r for _, r in DECODE_REFUSALS])
def test_the_decoder_refuses_malformed_or_truncated_text_and_names_why(text, reason):
    lua, json_codec = codec()
    lua.globals().codec, lua.globals().text = json_codec, text
    ok, error = lua.execute("return pcall(codec.decode, text)")
    assert ok is False and reason in str(error)


@pytest.mark.parametrize("value,kind", [("nil", "nil"), ("5", "number")])
def test_the_decoder_takes_only_a_string(value, kind):
    lua, json_codec = codec()
    lua.globals().codec = json_codec
    ok, error = lua.execute(f"return pcall(codec.decode, {value})")
    assert ok is False and f"expected argument of type string, got {kind}" in str(error)


def test_a_table_shared_twice_is_not_a_circular_reference():
    """Wrong version (2026-11-13 review): the encoder keeps an object on its stack after encoding
    it, so a table met again elsewhere is refused as circular."""
    lua, json_codec = codec()
    lua.globals().codec = json_codec
    text = lua.execute("local s = {a = 1}; return codec.encode({x = s, y = {s}})")
    assert json.loads(text) == {"x": {"a": 1}, "y": [{"a": 1}]}
