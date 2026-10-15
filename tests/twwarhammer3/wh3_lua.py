"""Run the WH3 mod's Lua in tests under lupa's Lua 5.1, the game's Lua version.

Battle-script tests load single top-level definitions by name, so moving or commenting other
parts of the script does not change what a test executes.
"""
from lupa import lua51

from gameai.provenance import REPO_ROOT

MOD = REPO_ROOT / "src/twwarhammer3/mod"
BATTLE = MOD / "script/battle/mod/twwarhammer3_battle.lua"


def runtime():
    """A fresh Lua state; a Lua function's several return values come back as a tuple."""
    return lua51.LuaRuntime(unpack_returned_tuples=True)


def battle_source(*names):
    """Each named top-level `local function NAME(` or `local NAME = {` of the battle script,
    from its first line to the next line that is exactly `end` or `}`."""
    lines = BATTLE.read_text().splitlines()
    chunks = []
    for name in names:
        starts = [i for i, line in enumerate(lines)
                  if line.startswith((f"local function {name}(", f"local {name} = {{"))]
        assert len(starts) == 1, f"{BATTLE.name} defines {name} {len(starts)} times"
        stop = next(i for i in range(starts[0], len(lines)) if lines[i] in ("end", "}"))
        chunks.append("\n".join(lines[starts[0]:stop + 1]))
    return "\n".join(chunks)


def load_battle(lua, *names):
    """Run the named definitions in `lua` as one chunk and return them in the same order.

    Later definitions see earlier ones as locals; every other name they use is a global the
    test defines.
    """
    return lua.execute(battle_source(*names) + "\nreturn " + ", ".join(names))
