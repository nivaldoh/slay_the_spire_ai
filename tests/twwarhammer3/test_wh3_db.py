"""scripts/wh3_db.py decodes a db table with its RPFM schema version, exactly."""

import importlib.util
import struct

import pytest

from gameai.provenance import REPO_ROOT

SPEC = importlib.util.spec_from_file_location("wh3_db_script", REPO_ROOT / "scripts/wh3_db.py")
db = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(db)

SCHEMA = """(
    version: 5,
    definitions: {
        "demo_units_tables": [
            (
                version: 1,
                fields: [
                    (
                        name: "unit",
                        field_type: StringU8,
                    ),
                ],
            ),
            (
                version: 2,
                fields: [
                    (
                        name: "unit",
                        field_type: StringU8,
                    ),
                    (
                        name: "cost",
                        field_type: I32,
                    ),
                    (
                        name: "large",
                        field_type: Boolean,
                    ),
                    (
                        name: "mount",
                        field_type: OptionalStringU8,
                    ),
                ],
                localised_fields: [
                    (
                        name: "onscreen_name",
                        field_type: StringU16,
                    ),
                ],
            ),
        ],
    },
)"""


def text(value: str) -> bytes:
    return struct.pack("<H", len(value)) + value.encode()


def table(*rows: bytes) -> bytes:
    guid = "g1".encode("utf-16-le")
    return (b"\xfd\xfe\xfc\xff" + struct.pack("<H", 2) + guid + b"\xfc\xfd\xfe\xff"
            + struct.pack("<I", 2) + b"\x01" + struct.pack("<I", len(rows)) + b"".join(rows))


def test_rows_follow_the_file_version_and_skip_localised_fields():
    data = table(text("knights") + struct.pack("<i?", 1200, True) + b"\x01" + text("horse"),
                 text("rats") + struct.pack("<i?", 125, False) + b"\x00")
    assert db.rows(data, SCHEMA, "demo_units_tables") == [
        {"unit": "knights", "cost": 1200, "large": True, "mount": "horse"},
        {"unit": "rats", "cost": 125, "large": False, "mount": None}]


def test_a_layout_mismatch_is_refused_not_misread():
    data = table(text("rats") + struct.pack("<i?", 125, False) + b"\x00") + b"\x00"
    with pytest.raises(ValueError, match="1 bytes left over"):
        db.rows(data, SCHEMA, "demo_units_tables")
    with pytest.raises(ValueError, match="no demo_units_tables version 3"):
        db.fields(SCHEMA, "demo_units_tables", 3)
