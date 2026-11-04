"""Passive deployment-readiness trace; offsets independently read from retained assembly.

Reference: pinned disassembly of 0x1bfa108 and 0x2ed483c in
runs/wh3-mp-overnight-20261104/notes.md. The stubbed memory establishes field reads and
bookkeeping, not that a real click takes this path; a live reference decides that.
"""

from test_wh3_multiplayer_probe import agent_check


def test_probe_records_each_step_of_the_readiness_path_without_acting():
    agent_check(r'''
load(`
const env = ptr(0x6000000), session = ptr(0x6100000), ui = ptr(0x6200000), setup = ptr(0x6300000);
const entries = ptr(0x6400000), provider = ptr(0x6500000), command = ptr(0x6600000);
const model = ptr(0x6700000), id = ptr(0x6800000);
battle = {env, session, emitted: 5, failed: false};
// Offsets as read from 0x1bfa108: ui+0x418 env, env+0x448 setup, +0xc8 kind,
// env+0x3a8/0x3b4 local list and index, env+0x645c8 network, env+0x644e8 provider.
pointers.set(ui.add(0x418).value, env.value);
pointers.set(env.add(0x3a8).value, entries.value);
pointers.set(env.add(0x448).value, setup.value);
pointers.set(env.add(0x645c8).value, 0x9000000);
pointers.set(env.add(0x644e8).value, provider.value);
words.set(env.add(0x3b4).value, 1);
words.set(env.add(0x3b0).value, 0);
words.set(env.add(0x3b1).value, 0);
words.set(setup.add(0xc8).value, 4);
words.set(entries.add(8).value, 3);
words.set(entries.add(12).value, 2);
words.set(ui.add(0x15cf).value, 0);
const enter = {};
hooks.get(Number(BUILD.end_deployment[0])).onEnter.call(enter, [ui]);
words.set(ui.add(0x15cf).value, 1);
hooks.get(Number(BUILD.end_deployment[0])).onLeave.call(enter);
const entered = messages.find(r => r.event === 'end_deployment_enter');
assert.deepEqual([entered.sent_before, entered.same_env, entered.setup_kind, entered.local_index,
                  Array.from(entered.local_entry), entered.network, entered.last_completed_tick],
                 [0, true, 4, 1, [3, 2], '0x9000000', 5]);
assert.equal(messages.find(r => r.event === 'end_deployment_return').sent_after, 1);
// Command object from 0x1bfa1a0: vtable, then two u32 fields at +8 and +0xc.
pointers.set(command.value, 0x37c3ef0);
words.set(command.add(8).value, 2);
words.set(command.add(12).value, 3);
hooks.get(Number(BUILD.end_deployment_command[0])).onEnter.call({}, [provider, command]);
const sent = messages.find(r => r.event === 'end_deployment_command');
assert.equal(sent.provider_is_env, true);
assert.deepEqual([sent.command_vtable, Array.from(sent.fields)], ['0x37c3ef0', [2, 3]]);
// Packet start 0x1bd09b0: rdx is provider+8, r8 the id's address, r9b the flags;
// the 0x5000-byte buffer's write offset sits at buffer+0x5000.
words.set(id.value, 0xabcd);
words.set(provider.add(0x5008).value, 40);
hooks.get(Number(BUILD.command_packet[0])).onEnter.call(
    {}, [ptr(1), provider.add(8), id, ptr(0x101)]);
const packet = messages.find(r => r.event === 'command_packet');
assert.deepEqual([packet.id, packet.flags, packet.on_provider, packet.offset],
                 [0xabcd, 1, true, 40]);
// Execute handler 0x2ed483c: rdx+0x150 model, count +0x9b8, countdown +0x9b4.
pointers.set(env.add(0x150).value, model.value);
words.set(model.add(0x9b8).value, 0);
words.set(model.add(0x9b4).value, 0xffffffff);
const execute = {};
hooks.get(Number(BUILD.end_deployment_execute[0])).onEnter.call(execute, [ptr(1), env]);
words.set(model.add(0x9b8).value, 1);
words.set(model.add(0x9b4).value, 600);
hooks.get(Number(BUILD.end_deployment_execute[0])).onLeave.call(execute);
const done = messages.find(r => r.event === 'end_deployment_execute');
assert.equal(done.same_env, true);
assert.deepEqual([Array.from(done.before), Array.from(done.after)],
                 [[0, 0xffffffff], [1, 600]]);
assert.ok(!messages.some(r => r.event === 'probe_error'));
assert.equal(messages[0].capabilities.length, 0, 'tracing grants no operation');
`);
''')


def test_probe_ignores_packets_outside_a_battle_and_fails_visibly_on_a_bad_read():
    agent_check(r'''
load(`
const packet = hooks.get(Number(BUILD.command_packet[0]));
const before = messages.length;
packet.onEnter.call({}, [ptr(1), ptr(2), ptr(3), ptr(0)]);
assert.equal(messages.length, before, 'no battle means no submission record');
battle = {env: ptr(0x6000000), session: ptr(0x6100000), emitted: 0, failed: false};
packet.onEnter.call({}, [ptr(1), ptr(2), ptr(3), ptr(0)]);
assert.equal(messages.at(-1).event, 'probe_error');
assert.equal(battle.failed, true);
const count = messages.length;
packet.onEnter.call({}, [ptr(1), ptr(2), ptr(3), ptr(0)]);
assert.equal(messages.length, count, 'a failed capture does not resume');
`);
''')
