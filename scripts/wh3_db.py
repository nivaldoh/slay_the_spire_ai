"""Read rows of a WH3 database table from the game's db.pack, read-only.

    uv run python scripts/wh3_db.py SCHEMA.ron main_units_tables [KEY ...]

SCHEMA.ron is RPFM's WH3 schema (rpfm-schemas, schema_wh3.ron), downloaded outside the
repository. Prints each row as JSON; with KEYs, only rows holding one of them as a field
value. Scenario design uses it for unit costs (main_units_tables multiplayer_cost) and
attributes (land_units_tables, melee_weapons_tables, unit_attributes_to_groups_junctions_
tables). Nothing it reads is written anywhere: game data stays out of the repository.
"""

import argparse
import json
import re
import struct
from pathlib import Path

from twwarhammer3.engine import pack, runtime

FIXED = {"Boolean": "<?", "F32": "<f", "F64": "<d", "I16": "<h", "I32": "<i", "I64": "<q",
         "ColourRGB": "<i"}


def fields(schema: str, table: str, version: int) -> list[tuple[str, str]]:
    """The stored fields of one table version; localised fields live in .loc files."""
    start = schema.index("[", schema.index(f'"{table}": ['))
    depth = 0
    for end in range(start, len(schema)):
        depth += {"[": 1, "]": -1}.get(schema[end], 0)
        if depth == 0:
            break
    for part in re.split(r"\(\s*version: ", schema[start:end])[1:]:
        if int(part.split(",", 1)[0]) == version:
            stored = part.split("localised_fields:")[0]
            return re.findall(r'name: "([^"]+)",\s*field_type: ([A-Za-z0-9_]+)', stored)
    raise ValueError(f"the schema has no {table} version {version}")


def rows(data: bytes, schema: str, table: str) -> list[dict]:
    offset, version = 0, 0
    if data[:4] == b"\xfd\xfe\xfc\xff":  # GUID
        offset = 6 + 2 * struct.unpack_from("<H", data, 4)[0]
    if data[offset:offset + 4] == b"\xfc\xfd\xfe\xff":
        version = struct.unpack_from("<I", data, offset + 4)[0]
        offset += 8
    count = struct.unpack_from("<I", data, offset + 1)[0]
    offset += 5
    layout, output = fields(schema, table, version), []
    for _ in range(count):
        row = {}
        for name, kind in layout:
            if kind in FIXED:
                row[name] = struct.unpack_from(FIXED[kind], data, offset)[0]
                offset += struct.calcsize(FIXED[kind])
                continue
            if kind.startswith("Optional"):
                offset += 1
                if not data[offset - 1]:
                    row[name] = None
                    continue
                kind = kind.removeprefix("Optional")
            if kind not in ("StringU8", "StringU16"):
                raise ValueError(f"{table}: field type {kind} is not supported")
            width = 1 if kind == "StringU8" else 2
            size = struct.unpack_from("<H", data, offset)[0] * width
            text = data[offset + 2:offset + 2 + size]
            row[name] = text.decode("utf-8" if width == 1 else "utf-16-le")
            offset += 2 + size
        output.append(row)
    if offset != len(data):
        raise ValueError(f"{table} version {version}: {len(data) - offset} bytes left over")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("schema", type=Path, help="RPFM schema_wh3.ron")
    parser.add_argument("table", help="for example main_units_tables")
    parser.add_argument("keys", nargs="*", help="only rows holding one of these values")
    args = parser.parse_args()
    data = pack.extract(runtime.GAME_DIR / "data/db.pack", f"db\\{args.table}\\data__")
    for row in rows(data, args.schema.read_text(), args.table):
        if not args.keys or set(args.keys) & set(row.values()):
            print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
