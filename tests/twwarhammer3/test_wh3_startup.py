import hashlib
import struct

import pytest

from twwarhammer3.engine import pack, startup


def test_movie_pack_overrides_only_splashes_and_all_localized_warnings(tmp_path):
    files = startup.movie_files()
    expected = {f"movies\\startup_movie_{index:02d}.ca_vp8" for index in range(1, 6)}
    expected |= {f"movies\\epilepsy_warning\\epilepsy_warning_{lang}.ca_vp8"
                 for lang in ("br", "cn", "cz", "de", "en", "es", "fr", "it", "kr", "pl",
                              "ru", "tr", "zh")}
    path = tmp_path / startup.PACK_NAME
    pack.write_pack(path, files, pack_type=pack.MOVIE)
    data = path.read_bytes()
    assert struct.unpack_from("<4sIIIII", data)[:5] == (b"PFH5", 4, 0, 0, 18)
    assert {entry[0] for entry in pack.read_index(path)} == expected
    for name in expected:
        blank = pack.extract(path, name)
        assert len(blank) == 595
        assert blank.startswith(b"CAMV")
        assert hashlib.sha256(blank).hexdigest() == (
            "1d7b8c23b63552d82bf90b6ee3855db1df8d695a807250a4d98ca3519bdd0b53"
        )
    other = tmp_path / "other.pack"
    pack.write_pack(other, dict(reversed(list(files.items()))), pack_type=pack.MOVIE)
    assert other.read_bytes() == data


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_preference_change_preserves_every_other_byte_and_is_idempotent(tmp_path, newline):
    path = tmp_path / "preferences.script.txt"
    original = newline.join([
        b"# fe_game_intro_video_enabled true; not a setting",
        b"gfx_unit_size 2; # keep \xff #",
        b"\tfe_game_intro_video_enabled\ttrue  ; # keep this comment #",
        b"battle_ai_stats_modifier 1.1;", b"",
    ])
    path.write_bytes(original)
    startup.disable_cinematic(path)
    expected = original.replace(b"\ttrue  ;", b"\tfalse  ;")
    assert path.read_bytes() == expected
    stamp = path.stat().st_mtime_ns
    startup.disable_cinematic(path)
    assert path.read_bytes() == expected
    assert path.stat().st_mtime_ns == stamp


@pytest.mark.parametrize("original,expected", [
    (b"", b"fe_game_intro_video_enabled false;\n"),
    (b"gfx_unit_size 2;", b"gfx_unit_size 2;\nfe_game_intro_video_enabled false;\n"),
    (b"gfx_unit_size 2;\r\n", b"gfx_unit_size 2;\r\nfe_game_intro_video_enabled false;\r\n"),
    (b"fe_game_intro_video_enabled false;\nfe_game_intro_video_enabled true;",
     b"fe_game_intro_video_enabled false;\nfe_game_intro_video_enabled false;"),
])
def test_missing_and_duplicate_settings(tmp_path, original, expected):
    path = tmp_path / "preferences.script.txt"
    path.write_bytes(original)
    startup.disable_cinematic(path)
    assert path.read_bytes() == expected


def test_missing_profile_is_not_created(tmp_path):
    path = tmp_path / "preferences.script.txt"
    with pytest.raises(FileNotFoundError):
        startup.install(tmp_path, path)
    assert not path.exists()
    assert not (tmp_path / "data" / startup.PACK_NAME).exists()
