"""Every script packed into the game must compile as Lua 5.1, the game's Lua version."""
import pytest
from wh3_lua import MOD, runtime


@pytest.mark.parametrize("path", sorted(MOD.rglob("*.lua")), ids=lambda path: path.name)
def test_mod_script_compiles_as_lua51(path):
    compile_lua = runtime().eval("function(source, name) assert(loadstring(source, name)) end")
    compile_lua(path.read_text(), "=" + path.name)  # raises with the file, line and error
