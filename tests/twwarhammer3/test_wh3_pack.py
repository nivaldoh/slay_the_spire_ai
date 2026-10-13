import shutil
import struct
import subprocess

import pytest

from twwarhammer3.engine import pack


def test_pack_layout_matches_the_vanilla_header_and_index(tmp_path):
    files = {
        "script\\battle\\mod\\b.lua": b"out('b')",
        "script\\A": b"",
        "script\\_lib\\mod\\j.lua": b"j",
    }
    pack.write_pack(tmp_path / "x.pack", files)
    data = (tmp_path / "x.pack").read_bytes()
    magic, kind, dependencies, dependency_bytes, count, index_bytes, stamp = struct.unpack_from(
        "<4sIIIIII", data
    )
    assert (magic, kind, dependencies, dependency_bytes, count, stamp) == (b"PFH5", 3, 0, 0, 3, 0)
    index = data[28:28 + index_bytes]
    # Entries are sorted case-insensitively ("_" before "a"): size, a zero compression
    # byte, path, NUL.
    assert index.startswith(struct.pack("<I", 1) + b"\0" + b"script\\_lib\\mod\\j.lua\0")
    assert index.endswith(struct.pack("<I", 8) + b"\0" + b"script\\battle\\mod\\b.lua\0")
    assert data[28 + index_bytes:] == b"j" + b"" + b"out('b')"


def test_read_index_and_extract_round_trip(tmp_path):
    source = _tree(tmp_path / "src", {"script/battle/mod/x.lua": b"x", "script/y": b"yy"})
    files = pack.files_in(source)
    assert list(files) == ["script\\battle\\mod\\x.lua", "script\\y"]
    pack.write_pack(tmp_path / "x.pack", files)
    entries = pack.read_index(tmp_path / "x.pack")
    assert [(name, size, compressed) for name, _, size, compressed in entries] == [
        ("script\\battle\\mod\\x.lua", 1, False), ("script\\y", 2, False),
    ]
    assert pack.extract(tmp_path / "x.pack", "script\\y") == b"yy"
    with pytest.raises(KeyError):
        pack.extract(tmp_path / "x.pack", "script\\z")


def test_flagged_packs_are_refused(tmp_path):
    (tmp_path / "x.pack").write_bytes(struct.pack("<4sIIIIII", b"PFH5", 0x43, 0, 0, 0, 0, 0))
    with pytest.raises(ValueError, match="not a plain"):
        pack.read_index(tmp_path / "x.pack")


@pytest.mark.skipif(shutil.which("zstd") is None, reason="zstd CLI not installed")
def test_compressed_entries_are_decoded_like_patch_9_vanilla_packs(tmp_path):
    text = b"bm:out('vanilla')\n" * 40
    frame = subprocess.run(["zstd", "-c"], input=text, capture_output=True, check=True).stdout
    data = struct.pack("<I", len(text)) + frame
    index = struct.pack("<I", len(data)) + b"\x01" + b"script\\v.lua\0"
    header = struct.pack("<4sIIIIII", b"PFH5", 1, 0, 0, 1, len(index), 0)
    (tmp_path / "v.pack").write_bytes(header + index + data)
    assert pack.extract(tmp_path / "v.pack", "script\\v.lua") == text


def _tree(root, files):
    for name, data in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(data)
    return root
