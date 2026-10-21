"""Actual Lua menu consumers against files and scheduled callbacks, without a game.

These check request isolation and step sequencing, not native UI effects or timings.
"""
import json

import pytest
from wh3_lua import BATTLE, MOD, runtime

from twwarhammer3.engine.mailbox import Mailbox


class MenuDriver:
    def __init__(self, directory, mode):
        self.directory, self.mode = directory, mode
        Mailbox(directory, job="current").write_session({
            "enabled": True, "menu": True, "autostart": False,
        })
        self.lua = runtime()
        self.lua.globals().test_bridge = str(directory) + "/"
        self.lua.execute('''
            -- Keep real file IO, translating only the game's fixed bridge directory.
            local open, remove, rename = io.open, os.remove, os.rename
            local prefix = "C:/wh3-agent/bridge/"
            local function path(name)
                if string.sub(name, 1, #prefix) == prefix then
                    return test_bridge .. string.sub(name, #prefix + 1)
                end
                return name
            end
            io.open = function(name, mode) return open(path(name), mode) end
            os.remove = function(name) return remove(path(name)) end
            os.rename = function(a, b) return rename(path(a), path(b)) end
            callbacks, calls, visible = {}, {}, false
            local function schedule(_, fn, _, name) callbacks[name] = fn end
            tm = {repeat_real_callback = schedule}
            bm = {
                battle = {time_elapsed_ms = function() return 0 end},
                register_phase_change_callback = function() end,
                repeat_real_callback = schedule,
            }
            local root = {
                Visible = function() return true end,
                Id = function() return "root" end,
                CurrentState = function() return "active" end,
                GetStateText = function() return "" end,
                ChildCount = function() return 0 end,
            }
            core = {get_ui_root = function() return root end}
            function find_uicomponent(_, ...)
                if select(-1, ...) ~= "button" then return nil end
                return {
                    VisibleFromRoot = function() return visible end,
                    SimulateLClick = function() calls[#calls + 1] = "click" end,
                }
            end
            common = {
                get_context_value = function(_, _, expression) return expression == "true" end,
                call_context_command = function(_, _, command)
                    calls[#calls + 1] = command
                    if command == "Reject()" then error("game refused command") end
                end,
            }
        ''')
        for name in ("twwarhammer3_json.lua", "twwarhammer3_ui.lua"):
            self.lua.execute((MOD / "script/_lib/mod" / name).read_text())
        source = (MOD / "script/frontend/mod/twwarhammer3_frontend.lua"
                  if mode == "frontend" else BATTLE)
        self.lua.execute(source.read_text())
        self.callback = self.lua.globals().callbacks[
            "twwarhammer3_menu" if mode == "frontend" else "twwarhammer3_poll"]
        assert self.callback is not None, self.log

    def send(self, steps, *, job="current", request="request-a"):
        (self.directory / "menu.json").write_text(json.dumps({
            "schema": 1, "job": job, "request": request, "steps": steps,
        }))

    def tick(self, count=1):
        for _ in range(count):
            self.callback()

    @property
    def calls(self):
        return list(self.lua.globals().calls.values())

    @property
    def log(self):
        name = "menu.log" if self.mode == "frontend" else "mod.log"
        return (self.directory / name).read_text()



@pytest.mark.parametrize("session, polls", [
    (None, False),
    ({"enabled": True, "menu": False}, False),
    ({"enabled": True, "menu": True}, True),
])
def test_frontend_polls_for_menus_only_when_a_job_asks(tmp_path, session, polls):
    # Every ordinary game launch loads the frontend script; only a job's menu session may
    # make it poll for menu requests.
    if session:
        Mailbox(tmp_path, job="current").write_session({**session, "autostart": False})
    lua = runtime()
    lua.globals().test_bridge = str(tmp_path) + "/"
    lua.execute('''
        local open, prefix = io.open, "C:/wh3-agent/bridge/"
        io.open = function(name, mode)
            if string.sub(name, 1, #prefix) == prefix then
                name = test_bridge .. string.sub(name, #prefix + 1)
            end
            return open(name, mode)
        end
        callbacks = {}
        tm = {repeat_real_callback = function(_, fn, _, name) callbacks[name] = fn end}
    ''')
    for name in ("twwarhammer3_json.lua", "twwarhammer3_ui.lua"):
        lua.execute((MOD / "script/_lib/mod" / name).read_text())
    lua.execute((MOD / "script/frontend/mod/twwarhammer3_frontend.lua").read_text())
    assert list(lua.globals().callbacks.keys()) == (["twwarhammer3_menu"] if polls else [])

def command(name, **fields):
    return {"context": "CcoFrontendRoot", "command": name, **fields}


@pytest.mark.parametrize("mode", ["frontend", "battle"])
def test_menu_consumers_reject_foreign_jobs_and_complete_current_requests(tmp_path, mode):
    driver = MenuDriver(tmp_path, mode)
    driver.send([command("Foreign()")], job="foreign", request="foreign-request")
    driver.tick(4)
    assert driver.calls == [], "a different job must never drive the UI"
    assert not (tmp_path / "menu.json").exists()
    driver.send([command("Current()")], request="current-request")
    driver.tick(4)
    assert driver.calls == ["Current()"]
    assert "menu current-request: done" in driver.log
    assert "menu foreign-request: done" not in driver.log


def test_frontend_skips_cached_branches_without_spending_callbacks_on_them(tmp_path):
    driver = MenuDriver(tmp_path, "frontend")
    skipped = [command("Cached()", when="false") for _ in range(20)]
    driver.send(skipped + [command("First()"), command("Second()")])
    driver.tick()  # Receive the request.
    assert driver.calls == []
    driver.tick()
    assert driver.calls == ["First()"]
    driver.tick()
    assert driver.calls == ["First()", "Second()"], "one action per callback"
    driver.tick()
    assert "menu request-a: done" in driver.log
    assert "\ndone\n" in driver.log


def test_frontend_preserves_explicit_waits_and_visible_component_retries(tmp_path):
    driver = MenuDriver(tmp_path, "frontend")
    driver.send([{"wait_ms": 1000},
                 {"find": ["button"], "click": True, "timeout_ms": 1000},
                 command("After()")])
    driver.tick(4)  # Receive, set the wait, then two 500 ms waiting callbacks.
    assert driver.calls == []
    driver.tick(2)  # A present but invisible component must retry, not click.
    assert driver.calls == []
    driver.lua.globals().visible = True
    driver.tick()
    assert driver.calls == ["click"]
    driver.tick()
    assert driver.calls == ["click", "After()"]
    driver.tick()
    assert "menu request-a: done" in driver.log


def test_frontend_retries_context_readbacks_and_stops_at_the_timeout(tmp_path):
    driver = MenuDriver(tmp_path, "frontend")
    driver.lua.execute('''
        readback, reads = false, 0
        common.get_context_value = function()
            reads = reads + 1
            return readback
        end
    ''')
    steps = [{"context": "CcoFrontendRoot", "expression": "Ready", "expect": True,
              "timeout_ms": 1000, "required": True}, command("After()")]
    driver.send(steps)
    driver.tick(3)  # Receive, then two unsuccessful 500 ms readbacks.
    assert driver.lua.globals().reads == 2 and driver.calls == []
    assert "failed" not in driver.log
    driver.lua.globals().readback = True
    driver.tick(3)
    assert driver.lua.globals().reads == 3 and driver.calls == ["After()"]
    assert "menu request-a: done" in driver.log
    driver.lua.globals().readback = False
    driver.send(steps, request="never-ready")
    driver.tick(5)
    assert driver.lua.globals().reads == 6 and driver.calls == ["After()"]
    assert "menu never-ready: failed" in driver.log


@pytest.mark.parametrize("mode", ["frontend", "battle"])
@pytest.mark.parametrize("required", [True, False], ids=["required", "optional"])
def test_menu_errors_report_failure_and_only_required_errors_stop_steps(tmp_path, mode, required):
    driver = MenuDriver(tmp_path, mode)
    driver.send([command("Reject()", required=required), command("After()")])
    driver.tick(5)
    assert driver.calls == (["Reject()"] if required else ["Reject()", "After()"])
    assert "menu request-a: failed" in driver.log
    assert "menu request-a: done" not in driver.log
    if mode == "frontend":
        assert ("\nfailed\n" if required else "\ndone\n") in driver.log
    # A failed sequence must not poison completion reporting for the next request.
    driver.send([command("Recovery()")], request="request-b")
    driver.tick(4)
    assert driver.calls[-1] == "Recovery()"
    assert "menu request-b: done" in driver.log


@pytest.mark.parametrize("modifier", [{"wait_ms": 1000}, {"timeout_ms": 1000},
                                      {"when": "false"}])
def test_battle_rejects_frontend_only_modifiers_before_running_any_steps(tmp_path, modifier):
    driver = MenuDriver(tmp_path, "battle")
    driver.send([command("Before()"), command("Unsupported()", **modifier),
                 command("After()")])
    driver.tick()
    assert driver.calls == [], "reject the sequence before its first side effect"
    assert "menu request-a: failed" in driver.log


@pytest.mark.parametrize("mode", ["frontend", "battle"])
def test_invalid_ui_actions_cannot_report_success_or_run_required_successors(tmp_path, mode):
    driver = MenuDriver(tmp_path, mode)
    invalid = [({}, "unknown step"),
               ({"lua": "return ("}, "lua:"),
               ({"find": ["absent"], "click": True}, "not found: absent"),
               ({"dump": "tree.txt", "find": ["absent"]}, "dump root not found"),
               ({"dump": "missing-parent/tree.txt", "depth": 0},
                "cannot write missing-parent/tree.txt")]
    for index, (step, error) in enumerate(invalid):
        request = f"invalid-{index}"
        driver.send([{**step, "required": True}, command("MustNotRun()")], request=request)
        driver.tick(4)
        assert driver.calls == [], (request, driver.log)
        assert f"menu {request}: failed" in driver.log
        assert f"menu {request}: done" not in driver.log
        assert error in driver.log
