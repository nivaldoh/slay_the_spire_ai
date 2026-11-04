"""Direct operation guards: bookkeeping and refusals, not ABI correctness or replication.

Reference: the plan's rule that a repeated request never repeats the engine action, that
requested and submitted stay separate, and the checks of native 0x1bfa108 and
IsDeploymentPhase 0x1e8933c (runs/wh3-mp-overnight-20261104/notes.md). A live reference and
the other client's readback decide whether the call does what the button does.
"""

import io
import json
import shutil
import subprocess
import threading

from twwarhammer3.engine import multiplayer_adapter as adapter
from twwarhammer3.engine import multiplayer_probe as probe


def agent_check(checks):
    node = shutil.which("node")
    assert node is not None, "Node.js is required to check the multiplayer adapter"
    result = subprocess.run([node, "-", str(adapter.AGENT), checks], text=True, capture_output=True,
                            input=r'''
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const source = fs.readFileSync(process.argv[2], 'utf8');
const signatures = new Map([...source.matchAll(/\['(0x[0-9a-f]+)', '([0-9a-f]+)'\]/g)]
    .map(m => [Number(m[1]), m[2]]));
const pointers = new Map(), words = new Map(), messages = [], calls = [];
const hooks = new Map(), exportsBox = {};
let bad = null, now = 1000, side = () => {}, tick = null;
class Pointer {
    constructor(value) { this.value = Number(value); }
    add(n) { return new Pointer(this.value + Number(n)); }
    equals(p) { return this.value === p.value; }
    isNull() { return this.value === 0; }
    toString() { return '0x' + this.value.toString(16); }
    readByteArray(n) {
        const bytes = bad === this.value ? '00'.repeat(n) : signatures.get(this.value);
        return Uint8Array.from(Buffer.from(bytes, 'hex')).buffer;
    }
    readPointer() {
        assert.ok(pointers.has(this.value), 'unmapped pointer ' + this.toString());
        return new Pointer(pointers.get(this.value));
    }
    readU32() {
        assert.ok(words.has(this.value), 'unmapped word ' + this);
        return words.get(this.value);
    }
    readU8() { return this.readU32() & 0xff; }
}
const ptr = x => new Pointer(x);
const session = ptr(0x6000000), env = ptr(0x6100000), ui = ptr(0x6200000), setup = ptr(0x6300000);
const stream = ptr(0x6400000);
function battle() {
    pointers.set(session.value, 0x3ab9b38);
    pointers.set(session.add(0x20).value, env.value);
    pointers.set(0x448f180, ui.value);
    pointers.set(ui.add(0x418).value, env.value);
    pointers.set(env.add(0x448).value, setup.value);
    pointers.set(env.add(0x644e8).value, stream.value);
    pointers.set(env.add(0x645c8).value, 0x9000000);
    words.set(setup.add(0xc8).value, 4);
    words.set(ui.add(0x15cf).value, 0);
    words.set(env.add(0x3b0).value, 0);
    words.set(env.add(0x3b1).value, 0);
    words.set(stream.add(0x5008).value, 100);
}
const send_packet = () => {
    words.set(ui.add(0x15cf).value, 1);
    words.set(stream.add(0x5008).value, 120);
};
function load() {
    const context = {
        assert, ptr, Uint8Array, rpc: {}, Date: {now: () => now}, String, Error, Set, Map, Object,
        Process: {getModuleByName: () => ({base: ptr(0)}), getCurrentThreadId: () => 7},
        setInterval: fn => { tick = fn; },
        NativeFunction: function (address, ret, args) {
            assert.equal(address.value, 0x1bfa108);
            assert.equal(ret, 'void');
            return pointer => { calls.push(pointer.value); side(); };
        },
        Interceptor: {attach(address, callbacks) {
            hooks.set(address.value, callbacks);
            return {detach() {}};
        }},
        send: row => messages.push(JSON.parse(JSON.stringify(row))),
    };
    vm.runInNewContext(source, context);
    return context.rpc.exports;
}
const step = () => hooks.get(0x2d78568).onEnter.call({}, [session]);
const results = () => messages.filter(r => r.event === 'operation_result');
eval(process.argv[3]);
''')
    assert result.returncode == 0, result.stdout + result.stderr


def test_a_request_runs_once_on_the_next_frame_and_reports_only_a_written_packet():
    agent_check(r'''
battle();
const api = load();
assert.equal(messages[0].event, 'adapter_ready');
side = send_packet;
assert.equal(api.submit('ready_deployment', 'r1'), 'queued');
assert.deepEqual(calls, [], 'a Frida RPC thread must not call the engine');
step();
assert.deepEqual(calls, [ui.value]);
assert.equal(results().at(-1).status, 'submitted');
assert.deepEqual(Array.from(results().at(-1).stream_offset), [100, 120]);
step();
assert.deepEqual(calls, [ui.value], 'exactly one engine call');
assert.equal(results().length, 1);
assert.equal(api.submit('ready_deployment', 'r1'), 'duplicate');
assert.throws(() => api.submit('anything_else', 'r2'), /unknown operation/);
step();
assert.deepEqual(calls, [ui.value]);
''')


def test_each_guard_refuses_before_the_engine_call():
    agent_check(r'''
const cases = [
    ['conflict phase', () => words.set(setup.add(0xc8).value, 5), /not deployment/],
    ['phase 1 is not deployment', () => words.set(setup.add(0xc8).value, 1), /not deployment/],
    ['phase 0 precedes the click', () => words.set(setup.add(0xc8).value, 0), /not deployment/],
    ['one-shot already set', () => words.set(ui.add(0x15cf).value, 1), /already sent/],
    ['engine flag a', () => words.set(env.add(0x3b0).value, 1), /engine flags/],
    ['engine flag b', () => words.set(env.add(0x3b1).value, 1), /engine flags/],
    ['single player', () => pointers.set(env.add(0x645c8).value, 0), /not a network battle/],
    ['no stream', () => pointers.set(env.add(0x644e8).value, 0), /no input stream/],
    ['no interface', () => pointers.set(0x448f180, 0), /no battle interface/],
    ['stale interface', () => pointers.set(ui.add(0x418).value, 0x7000000), /stale/],
    ['wrong session', () => pointers.set(session.value, 0x1234), /session layout/],
];
battle();
const api = load();
let n = 0;
for (const [name, plant, reason] of cases) {
    battle();
    plant();
    api.submit('ready_deployment', 'r' + n++);
    step();
    assert.equal(results().at(-1).status, 'refused', name);
    assert.match(results().at(-1).reason, reason, name);
}
assert.deepEqual(calls, []);
battle();
assert.equal(api.submit('ready_deployment', 'r0'), 'duplicate', 'a refused id stays spent');
''')


def test_a_request_expires_with_a_row_even_with_no_battle_frames_and_never_reaches_the_engine():
    agent_check(r'''
battle();
const api = load();
assert.equal(api.submit('ready_deployment', 'r1'), 'queued');
now += 29000;
tick();
assert.equal(results().length, 0, 'still inside the 30 s bound');
assert.equal(api.submit('ready_deployment', 'r2'), 'busy');
now += 1001;
tick();
assert.equal(results().at(-1).status, 'expired');
assert.equal(results().at(-1).request, 'r1');
step();
assert.deepEqual(calls, []);
assert.equal(api.submit('ready_deployment', 'r3'), 'queued', 'one outstanding at a time');
now += 30001;
step();
assert.equal(results().at(-1).status, 'expired', 'a late frame also expires it');
assert.deepEqual(calls, []);
''')


def test_no_written_packet_or_a_native_failure_is_unknown_and_never_repeated():
    agent_check(r'''
battle();
const api = load();
// The engine sets its flag and then declines: nothing written, so not submitted.
side = () => words.set(ui.add(0x15cf).value, 1);
api.submit('ready_deployment', 'r1');
step();
assert.equal(results().at(-1).status, 'unknown');
step();
assert.equal(calls.length, 1, 'an unknown effect is never retried');
battle();
side = () => { throw new Error('access violation'); };
api.submit('ready_deployment', 'r2');
step();
assert.equal(results().at(-1).status, 'unknown');
assert.match(results().at(-1).reason, /access violation/);
step();
assert.equal(calls.length, 2, 'one call per request');
''')


def test_the_adapter_refuses_an_unknown_build_before_any_hook():
    agent_check(r'''
for (const address of signatures.keys()) {
    bad = address;
    assert.throws(load, /Unsupported/);
    assert.equal(hooks.size, 0);
    assert.equal(messages.length, 0);
}
''')


def test_stdin_lines_become_operations_and_bad_lines_become_evidence():
    submitted, rows = [], []

    class Exports:
        def submit(self, operation, request):
            submitted.append((operation, request))
            return "queued"

    class Script:
        exports_sync = Exports()

    lines = io.StringIO('{"operation": "ready_deployment", "request": "a"}\n'
                        'not json\n{"operation": "write_memory", "request": "b"}\n'
                        '{"operation": "ready_deployment"}\n'
                        '{"operation": "ready_deployment", "request": ["a"]}\n')
    adapter.Adapter(lines).start(Script(), rows.append).join(timeout=5)
    assert submitted == [("ready_deployment", "a")]
    assert [row["event"] for row in rows] == ["request_answer", *["request_refused"] * 4]


def test_a_broken_request_stream_leaves_a_row_and_a_closed_log_does_not_raise():
    def broken():
        yield '{"operation": "ready_deployment", "request": "a"}'
        raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad")

    class Exports:
        def submit(self, operation, request):
            return "queued"

    class Script:
        exports_sync = Exports()

    rows = []
    adapter.Adapter(broken()).start(Script(), rows.append).join(timeout=5)
    assert [row["event"] for row in rows] == ["request_answer", "request_failed"]

    def closed(row):
        raise ValueError("I/O operation on closed file")
    thread = adapter.Adapter(broken()).start(Script(), closed)
    thread.join(timeout=5)
    assert not thread.is_alive()


def test_a_passive_capture_loads_no_operations_and_an_adapter_capture_loads_them(
        tmp_path, monkeypatch):
    exe = tmp_path / "Warhammer3.exe"
    exe.write_bytes(b"fake pinned executable")
    with exe.open("rb") as file:
        digest = probe.hashlib.file_digest(file, "sha256").hexdigest()
    monkeypatch.setattr(probe, "process_executable", lambda pid: exe)
    monkeypatch.setattr(probe.runtime, "PINS", {"Warhammer3.exe": digest})

    class Script:
        def on(self, name, callback):
            self.callback = callback

        def load(self):
            self.callback({"type": "send", "payload": {"event": "ready"}}, None)

    class Device:
        def __init__(self):
            self.sources = []

        def attach(self, pid):
            return self

        def on(self, *args):
            pass

        off = on

        def detach(self):
            pass

        def create_script(self, source):
            self.sources.append(source)
            return Script()

    passive, active = Device(), Device()
    assert probe.capture(passive, 1, tmp_path / "passive", seconds=0.01) == 0
    assert len(passive.sources) == 1
    manifest = json.loads((tmp_path / "passive/manifest.json").read_text())
    assert manifest["diagnostic_only"] is True and manifest["adapter_sha256"] is None

    assert probe.capture(active, 1, tmp_path / "active", seconds=0.01,
                         adapter=adapter.Adapter(io.StringIO(""))) == 0
    assert len(active.sources) == 2 and active.sources[1] == adapter.AGENT.read_text()
    manifest = json.loads((tmp_path / "active/manifest.json").read_text())
    assert manifest["diagnostic_only"] is False and manifest["adapter_sha256"]


class Process:
    def __init__(self, *args, **kwargs):
        self.argv, self.stdin = args[0], io.StringIO()
        self.waited = False

    def poll(self):
        return None

    def wait(self, timeout):
        self.waited = True


def test_the_helper_reads_whole_lines_tracks_requests_and_keeps_the_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "CAPTURES", tmp_path / "windows")
    monkeypatch.setattr(adapter, "source_path", lambda: "C:/source")
    monkeypatch.setattr(adapter.windows, "windows_path", lambda path: str(path))
    helper = adapter.Helper(321, "m.a.A", tmp_path / "evidence", seconds=9, run=Process)
    assert (tmp_path / "helper-console.txt").exists(), "a start failure must leave its output"
    assert helper.process.argv[-6:] == ["--pid", "321", "--output",
                                        str(tmp_path / "windows/m.a.A"), "--seconds", "9"]
    helper.poll()
    assert helper.rows_from(0) == [], "no file yet"
    helper.native.mkdir(parents=True)
    path = helper.native / "native.jsonl"
    path.write_bytes(b'{"event": "adapter_ready"}\n{"event": "completed_tick"}\n'
                     b'{"event": "opera')
    helper.poll()
    assert [row["event"] for row in helper.rows_from(0)] == ["adapter_ready"]
    helper.wait_ready(seconds=0)
    with path.open("ab") as file:
        file.write(b'tion_result", "request": "x", "status": "submitted"}\n')
    assert helper.result("x", ("submitted",), 0)["status"] == "submitted"
    assert helper.result("x", ("applied",), 0) is None, "a later status has not arrived"
    request = helper.request("ready_deployment")
    assert json.loads(helper.process.stdin.getvalue()) == {"operation": "ready_deployment",
                                                           "request": request}
    helper.close()
    assert helper.process.waited and (helper.native / "STOP").exists()
    assert (tmp_path / "evidence/native.jsonl").read_bytes() == path.read_bytes()


def test_two_threads_polling_read_every_row_exactly_once(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "CAPTURES", tmp_path / "windows")
    monkeypatch.setattr(adapter, "source_path", lambda: "C:/source")
    monkeypatch.setattr(adapter.windows, "windows_path", lambda path: str(path))
    helper = adapter.Helper(1, "m.a.A", tmp_path / "evidence", seconds=9, run=Process)
    helper.native.mkdir(parents=True)
    path = helper.native / "native.jsonl"
    path.write_bytes(b"")
    stop = threading.Event()

    def reader():
        while not stop.is_set():
            helper.poll()

    threads = [threading.Thread(target=reader) for _ in range(2)]
    for thread in threads:
        thread.start()
    with path.open("ab", buffering=0) as file:
        for n in range(2000):
            file.write(json.dumps({"event": "operation_result", "n": n}).encode() + b"\n")
    stop.set()
    for thread in threads:
        thread.join(timeout=10)
    helper.poll()
    assert [row["n"] for row in helper.rows_from(0)] == list(range(2000))
