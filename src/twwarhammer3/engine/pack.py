"""PFH5 pack files: build the mod pack, list and extract vanilla packs.

Layout (little-endian): ``PFH5``, u32 type (3 = mod), u32 dependency count, u32
dependency index bytes, u32 file count, u32 file index bytes, u32 timestamp; the
dependency index (NUL-terminated pack names); the file index, one ``u32 size, u8
compressed, path, NUL`` entry per file with backslash paths; then the file data in
index order. Patch 9.0 vanilla entries are zstd frames prefixed by their u32
uncompressed size; the mod pack is written uncompressed (flag 0).
"""

import os
import shutil
import struct
import subprocess
from pathlib import Path

MAGIC = b"PFH5"
MOD = 3
HEADER = struct.Struct("<4sIIIIII")


def files_in(root: Path) -> dict[str, bytes]:
    """Every file under ``root`` keyed by its backslash path inside the pack."""
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            files[path.relative_to(root).as_posix().replace("/", "\\")] = path.read_bytes()
    return files


def write_pack(path: Path, files: dict[str, bytes], *, pack_type: int = MOD) -> None:
    """Write an uncompressed pack atomically; a fixed timestamp keeps its hash reproducible."""
    names = sorted(files, key=str.lower)
    index = b"".join(
        struct.pack("<I", len(files[name])) + b"\0" + name.encode() + b"\0" for name in names
    )
    header = HEADER.pack(MAGIC, pack_type, 0, 0, len(names), len(index), 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(header + index + b"".join(files[name] for name in names))
    os.replace(temporary, path)


def read_index(path: Path) -> list[tuple[str, int, int, bool]]:
    """(name, offset, size, compressed) for every entry of a flag-free PFH5 pack."""
    with path.open("rb") as pack:
        magic, pack_type, _, dependencies, count, index_size, _ = HEADER.unpack(
            pack.read(HEADER.size)
        )
        if magic != MAGIC or pack_type & ~0xF:
            raise ValueError(f"{path}: not a plain PFH5 pack (type {pack_type:#x})")
        pack.seek(dependencies, os.SEEK_CUR)
        index = pack.read(index_size)
    entries, position, offset = [], 0, HEADER.size + dependencies + index_size
    for _ in range(count):
        size = struct.unpack_from("<I", index, position)[0]
        compressed = index[position + 4] != 0
        end = index.index(b"\0", position + 5)
        entries.append((index[position + 5:end].decode(), offset, size, compressed))
        position, offset = end + 1, offset + size
    return entries


def extract(path: Path, name: str) -> bytes:
    """One entry's bytes, decompressing with the ``zstd`` CLI when the pack compressed it."""
    for entry, offset, size, compressed in read_index(path):
        if entry == name:
            break
    else:
        raise KeyError(f"{name} is not in {path}")
    with path.open("rb") as pack:
        pack.seek(offset)
        data = pack.read(size)
    if not compressed:
        return data
    if shutil.which("zstd") is None:
        raise RuntimeError("zstd is needed to read compressed pack entries")
    decoded = subprocess.run(["zstd", "-d", "-c"], input=data[4:], capture_output=True, check=True)
    return decoded.stdout
