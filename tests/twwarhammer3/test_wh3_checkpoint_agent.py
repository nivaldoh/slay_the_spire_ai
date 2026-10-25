"""Exercise the real agent with a simulated completed replay tick; no game."""
import shutil
import subprocess

import pytest

from twwarhammer3.battle import checkpoint


def agent_checks(checks):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is needed to run the Frida agent component check")
    result = subprocess.run([node, "-", str(checkpoint.AGENT), checks], input=r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[2], 'utf8');
const signatures = new Map([...source.matchAll(/\['(0x[0-9a-f]+)', '([0-9a-f]+)'\]/g)]
    .map(m => [Number(m[1]), m[2]]));
class Pointer {
    constructor(value) { this.value = Number(value); }
    add(offset) { return new Pointer(this.value + Number(offset)); }
    readByteArray() {
        return Uint8Array.from(Buffer.from(signatures.get(this.value), 'hex')).buffer;
    }
    toString() { return String(this.value); }
    isNull() { return this.value === 0; }
}
const hooks = new Map(), messages = [];
vm.runInNewContext(source + `
const env = {
    equals: other => other === env,
    add(offset) {
        if (offset === ENV.tick) return {readU32: () => 100};
        if (offset === ENV.replay_flag) return {readU8: () => 0};
        if (offset === ENV.worker_job || offset === ENV.recording)
            return {readPointer: () => ptr(0)};
        throw new Error('unexpected environment field ' + offset);
    }
};
const session = {add: offset => {
    assert.equal(offset, 0x20);
    return {readPointer: () => env};
}};
const step = hooks.get(Number(BUILD.session_step[0]));
` + process.argv[3], {
    assert, hooks, messages, Uint8Array, rpc: {}, ptr: value => new Pointer(value),
    Process: {getModuleByName: () => ({base: new Pointer(0)})},
    NativeFunction: function () { return () => null; },
    Interceptor: {attach: (address, callbacks) => hooks.set(address.value, callbacks)},
    send: row => messages.push(row)
});
''', text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_save_refuses_rebuilding_or_failed_battles_without_breaking_the_restore():
    agent_checks('''
battle = {env, tick: 100, seed: 7, speed: REBUILD_SPEED, restore: {tick: 1200},
          handedOff: false, failed: false};
let refusal;
try { rpc.exports.save('during_rebuild'); } catch (error) { refusal = error; }
step.onLeave.call({session}, {readU8: () => 1});
assert.equal(battle.failed, false, 'a refused save must leave the rebuild running');
assert.match(refusal && refusal.message || '', /restor/);
assert.equal(pendingSave, null);
assert.equal(messages.filter(row => row.event === 'error').length, 0);

battle.failed = true;
assert.throws(() => rpc.exports.save('after_failure'), /failed/);
assert.equal(pendingSave, null);

battle.failed = false;
battle.handedOff = true;
assert.equal(rpc.exports.save('after_handover'), 100);
assert.equal(pendingSave, 'after_handover');
pendingSave = null;
battle.restore = null;
assert.equal(rpc.exports.save('source'), 100);
assert.equal(pendingSave, 'source');
''')


def test_seed_must_match_before_handover_or_a_restored_event():
    agent_checks('''
let handovers = 0;
handOver = () => { handovers++; };
luaSeedSlot = () => ({readU32: () => 7});
for (const saved of [8, undefined]) {
    messages.length = 0;
    battle = {env, tick: 100, seed: 7, speed: 1, restore: {tick: 100, seed_at_tick: saved},
              handedOff: false, failed: false};
    step.onLeave.call({session}, {readU8: () => 1});
    assert.equal(handovers, 0, 'a wrong seed must refuse the native input swap');
    assert.equal(battle.failed, true);
    assert.equal(battle.handedOff, false);
    assert.equal(messages.some(row => row.event === 'restored'), false);
    assert.match(messages.find(row => row.event === 'error').message, /Lua random seed/);
}
messages.length = 0;
battle = {env, tick: 100, seed: 7, speed: 1, restore: {tick: 100, seed_at_tick: 7},
          handedOff: false, failed: false};
step.onLeave.call({session}, {readU8: () => 1});
assert.equal(handovers, 1);
assert.equal(battle.failed, false);
assert.equal(battle.handedOff, true);
assert.equal(messages.find(row => row.event === 'restored').lua_seed_matches, true);
''')
