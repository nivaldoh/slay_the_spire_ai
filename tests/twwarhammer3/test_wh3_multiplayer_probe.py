"""Foundation stage-1 discovery guards, not ABI/replication or acceptance tests.

Reference: the plan's passive-discovery rule and the checkpoint completed-tick contract
(consumed frame, joined worker, matching counters). Frida API specifies per-invocation
hook storage. Native fields/addresses still require a live reference at this build.
"""

import json
import shutil
import subprocess
import threading

import pytest

from twwarhammer3.engine import multiplayer_probe as probe


def agent_check(checks):
    node = shutil.which("node")
    assert node is not None, "Node.js is required to check the multiplayer native probe"
    result = subprocess.run([node, "-", str(probe.AGENT), checks], text=True, capture_output=True,
                            input=r'''
const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const source = fs.readFileSync(process.argv[2], 'utf8');
const signatures = new Map([...source.matchAll(/\['(0x[0-9a-f]+)', '([0-9a-f]+)'\]/g)]
    .map(m => [Number(m[1]), m[2]]));
const hooks = new Map(), messages = [], pointers = new Map(), words = new Map();
let bad = null, badLayout = false, attachFails = null, detached = 0, thread = 7;
class Pointer {
    constructor(value) { this.value = Number(value); }
    add(n) { return new Pointer(this.value + Number(n)); }
    sub(p) { return new Pointer(this.value - p.value); }
    equals(p) { return p instanceof Pointer && this.value === p.value; }
    compare(p) { return Math.sign(this.value - p.value); }
    isNull() { return this.value === 0; }
    toInt32() { return this.value | 0; }
    toString() { return '0x' + this.value.toString(16); }
    readByteArray(n) {
        let bytes = signatures.get(this.value) || '01'.repeat(n);
        if (bad === this.value) bytes = '00'.repeat(n);
        return Uint8Array.from(Buffer.from(bytes.slice(0, n*2), 'hex')).buffer;
    }
    readPointer() {
        if (this.value === 0x37c45f0 + 0x188)
            return new Pointer(badLayout ? 0 : 0x1bef0c0);
        assert.ok(pointers.has(this.value), 'unmapped pointer ' + this.toString());
        return new Pointer(pointers.get(this.value));
    }
    readU32() { assert.ok(words.has(this.value)); return words.get(this.value); }
    readU8() { return this.readU32() & 0xff; }
}
const ptr = x => new Pointer(x);
function load(checks) {
    return vm.runInNewContext(source + '\n' + checks, {
        assert, hooks, messages, pointers, words, ptr, Uint8Array,
        Process: {getModuleByName: () => ({base: ptr(0), size: 0x5000000, path: 'Warhammer3.exe'}),
                  getCurrentThreadId: () => thread},
        NativeFunction: function () { throw new Error('probe must never invoke game code'); },
        Interceptor: {attach(address, callbacks) {
            if (address.value === attachFails) throw new Error('attach failed');
            hooks.set(address.value, callbacks);
            return {detach() { hooks.delete(address.value); detached++; }};
        }},
        send: row => messages.push(JSON.parse(JSON.stringify(row))),
    });
}
eval(process.argv[3]);
''')
    assert result.returncode == 0, result.stdout + result.stderr


def test_probe_checks_all_signatures_and_layout_before_any_hook_and_rolls_back():
    agent_check(r'''
for (const address of signatures.keys()) {
    bad = address;
    assert.throws(() => load(''), /Unsupported/);
    assert.equal(hooks.size, 0);
    assert.equal(messages.length, 0);
}
bad = null; badLayout = true;
assert.throws(() => load(''), /layout/);
assert.equal(hooks.size, 0);
badLayout = false;
attachFails = 0x2d9f56c;
assert.throws(() => load(''), /attach failed/);
assert.equal(hooks.size, 0);
assert.equal(detached, 2);
assert.equal(messages.length, 0);
''')


def test_probe_preserves_duplicate_callback_invocations_without_claiming_submission():
    agent_check(r'''
load(`
assert.equal(messages[0].event, 'ready');
assert.equal(messages[0].diagnostic_only, true);
assert.equal(messages[0].capabilities.length, 0);
const dispatch = hooks.get(Number(BUILD.deployment_dispatch[0]));
const lookup = hooks.get(Number(BUILD.event_lookup[0]));
const object = ptr(0x6000000);
pointers.set(object.value, VTABLE.deployment);
const eventName = {readUtf8String: () => 'reference-event'};
// Same event twice: distinct calls even if no unit would move differently.
for (let n = 0; n < 2; n++) {
    const invocation = {}, resolution = {};
    dispatch.onEnter.call(invocation, [object, eventName, ptr(123)]);
    lookup.onEnter.call(resolution, [ptr(0x448ff18), eventName]);
    lookup.onLeave.call(resolution, ptr(0x123456));
    dispatch.onLeave.call(invocation);
}
const entered = messages.filter(x => x.event === 'deployment_callback_enter');
assert.equal(entered.length, 2);
assert.notEqual(entered[0].call, entered[1].call);
assert.equal(messages.filter(x => x.event === 'deployment_callback_return').length, 2);
assert.equal(messages.filter(x => x.event === 'deployment_handler_resolved').length, 2);
assert.ok(messages.every(x => Number.isFinite(x.source_wall_ms) && x.thread === 7));
assert.ok(messages.every((x, i) => x.seq === i + 1));
const completions = ['submitted', 'ready_deployment', 'operation_completed'];
assert.ok(!messages.some(x => completions.includes(x.event)));
const unrelated = {};
lookup.onEnter.call(unrelated, [ptr(0x448ff18), eventName]);
const count = messages.length;
lookup.onLeave.call(unrelated, ptr(0x123456));
assert.equal(messages.length, count, 'a lookup outside deployment must be ignored');
`);
''')


def test_probe_only_emits_joined_completed_ticks_and_forgets_old_sessions():
    agent_check(r'''
load(`
const env = ptr(0x6000000), session = ptr(0x6100000);
const checks = ptr(0x6200000), entry = ptr(0x6300000), world = ptr(0x6600000);
const model = ptr(0x6700000), state = ptr(0x6800000);
pointers.set(session.value, VTABLE.session);
pointers.set(env.add(ENV.setup).value, world.value);
pointers.set(env.add(ENV.model).value, model.value);
pointers.set(model.add(MODEL.state).value, state.value);
pointers.set(state.add(STATE.alliances).value, 0);
words.set(state.add(STATE.alliance_count).value, 0);
words.set(world.add(WORLD.phase).value, 4);
pointers.set(SCRIPT.global, 0);
pointers.set(session.add(0x20).value, env.value);
pointers.set(env.add(ENV.checksums).value, checks.value);
pointers.set(checks.add(0x48).value, entry.value);
pointers.set(env.add(ENV.worker_job).value, 0);
words.set(env.add(ENV.tick).value, 1);
words.set(entry.add(0x18).value, 1);
words.set(entry.add(0x14).value, 123);
function invoke(name, argument, result) {
    const callbacks = hooks.get(Number(BUILD[name][0])), invocation = {};
    if (callbacks.onEnter) callbacks.onEnter.call(invocation, [argument]);
    // Native reference: step returns the out-buffer address, with consumed at byte 0;
    // the address's low byte is independent of that flag (RVA 0x2d786c1..0x2d78701).
    const returned = name === 'session_step' ? ptr(0x6500000 + (result ? 0 : 1)) : ptr(result);
    if (name === 'session_step') words.set(returned.value, result);
    if (callbacks.onLeave) callbacks.onLeave.call(invocation, returned);
}
const samples = () => messages.filter(x => x.event === 'completed_tick');
invoke('env_ctor', env, 0);
invoke('session_ctor', session, 0);
invoke('post_tick', env, 0);
invoke('session_step', session, 0);
assert.equal(samples().length, 0, 'unconsumed frame');
pointers.set(env.add(ENV.worker_job).value, 456);
invoke('session_step', session, 1);
assert.equal(samples().length, 0, 'worker not joined');
pointers.set(env.add(ENV.worker_job).value, 0);
words.set(env.add(ENV.tick).value, 2);
invoke('session_step', session, 1);
assert.equal(samples().length, 0, 'counter mismatch');
words.set(env.add(ENV.tick).value, 1);
invoke('session_step', session, 1);
invoke('session_step', session, 1);
assert.equal(samples().length, 1, 'one sample per completed tick');
assert.equal(samples()[0].checksum, 123);
const generation1 = samples()[0].generation;
invoke('env_ctor', ptr(0x6400000), 0);
invoke('post_tick', env, 0);
invoke('session_step', session, 1);
assert.equal(samples().length, 1, 'old handles must not survive a new environment');
assert.ok(messages.at(-1).generation > generation1);
invoke('env_ctor', env, 0);
invoke('session_ctor', session, 0);
words.set(entry.add(0x18).value, 9);
invoke('post_tick', env, 0);
assert.equal(messages.at(-1).event, 'probe_error');
words.set(entry.add(0x18).value, 1);
invoke('post_tick', env, 0);
invoke('session_step', session, 1);
assert.equal(samples().length, 1, 'failed collection cannot resume silently');
`);
''')


def test_probe_hashes_the_process_image_and_refuses_before_attachment(tmp_path, monkeypatch):
    exe = tmp_path / "Warhammer3.exe"
    exe.write_bytes(b"unsupported executable")
    monkeypatch.setattr(probe, "process_executable", lambda pid: exe)

    class Device:
        def attach(self, pid):
            pytest.fail("unsupported process must not be attached")

    with pytest.raises(RuntimeError, match="unsupported.*sha256"):
        probe.capture(Device(), 123, tmp_path / "capture", seconds=1)
    assert not (tmp_path / "capture").exists()


@pytest.mark.parametrize("failure", ["probe_error", "crash", "load_error", "detach_error"])
def test_probe_preserves_errors_and_detaches_before_closing_evidence(
        tmp_path, monkeypatch, failure):
    exe = tmp_path / "Warhammer3.exe"
    exe.write_bytes(b"fake pinned executable")
    with exe.open("rb") as file:
        digest = probe.hashlib.file_digest(file, "sha256").hexdigest()
    monkeypatch.setattr(probe, "process_executable", lambda pid: exe)
    monkeypatch.setattr(probe.runtime, "PINS", {"Warhammer3.exe": digest})
    detached = []

    class Crash:
        summary = "Access violation"
        report = "reference crash report"

    class Script:
        def __init__(self, device):
            self.device = device

        def on(self, name, callback):
            self.callback = callback

        def load(self):
            self.callback({"type": "send", "payload": {"event": "ready"}}, None)
            if failure == "probe_error":
                self.callback({"type": "send", "payload": {"event": "probe_error",
                                                           "message": "wrong layout"}}, None)
            elif failure == "crash":
                # Frida delivers exceptions here on its event thread, outside capture's try.
                thread = threading.Thread(target=self.device.detached_callback,
                                          args=("process-terminated", Crash()))
                thread.start()
                thread.join(timeout=5)
                assert not thread.is_alive()
            elif failure == "load_error":
                raise RuntimeError("script load failed")

    class Device:
        def attach(self, pid):
            return self

        def on(self, name, callback):
            self.detached_callback = callback

        def off(self, *args):
            pass

        def create_script(self, source):
            return Script(self)

        def detach(self):
            detached.append(True)
            if failure == "detach_error":
                raise RuntimeError("session already gone")

    output = tmp_path / "capture"
    assert probe.capture(Device(), 123, output, seconds=0.01) == 1
    assert detached == [True]
    rows = [json.loads(line) for line in (output / "native.jsonl").read_text().splitlines()]
    error_event = {"crash": "detached", "probe_error": "probe_error",
                   "load_error": "capture_error", "detach_error": "detach_error"}[failure]
    assert [row["event"] for row in rows] == ["ready", error_event, "capture_stopped"]
    if failure == "crash":
        assert rows[1]["crash"] == {"summary": Crash.summary, "report": Crash.report}
    assert rows[-1]["failed"] is True
    assert all(isinstance(row["received_perf_ns"], int) for row in rows)
    with pytest.raises(FileExistsError):
        probe.capture(Device(), 123, output, seconds=1)
