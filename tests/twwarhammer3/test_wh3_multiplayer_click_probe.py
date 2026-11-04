"""Passive click-path discovery, with registers independently read from retained assembly.

This exercises the new hooks through the existing Frida harness; the harness's native
mutator trap remains active. It establishes neither ABI correctness nor submission.
"""

from test_wh3_multiplayer_probe import agent_check


def test_click_probe_reads_the_callsite_registers_and_slots_only_in_a_battle_click():
    agent_check(r'''
load(`
const click = hooks.get(Number(BUILD.simulate_click[0]));
const extension = hooks.get(Number(BUILD.click_extension[0]));
const callback = hooks.get(Number(BUILD.click_callback[0]));
const component = hooks.get(Number(BUILD.click_component[0]));
const event = hooks.get(Number(BUILD.click_event[0]));
const componentPointer = ptr(0x6000000), session = ptr(0x6100000);
const context = {rax: ptr(0x100000), rcx: componentPointer, rdx: ptr(0x777),
                 r8: ptr(0), r9: ptr(0x123456)};
pointers.set(context.rax.add(0x68).value, 0x234567);
pointers.set(context.rax.add(0xf8).value, 0x345678);
const targets = () => messages.filter(r => r.event === 'ui_call_target');
// Frontend clicks and unrelated calls must not become deployment evidence.
const frontend = {};
click.onEnter.call(frontend, [componentPointer]);
extension.call({context});
click.onLeave.call(frontend);
assert.equal(targets().length, 0);
battle = {session, emitted: 7, failed: false};
const invocation = {};
click.onEnter.call(invocation, [componentPointer]);
extension.call({context}); callback.call({context});
component.call({context}); event.call({context});
click.onLeave.call(invocation);
assert.deepEqual(Array.from(targets(), r => r.rva),
                 ['0x123456', '0x234567', '0x345678', '0x13480fc']);
assert.ok(targets().every(r => r.registers.rcx === componentPointer.toString()));
assert.ok(targets().every(r => r.evidence === 'target_before_call_instruction'));
assert.ok(targets().every(r => r.last_completed_tick === 7));
assert.ok(targets().every(r => r.call === invocation.click.call));
assert.equal(messages.at(-1).event, 'ui_click_return');
assert.equal(messages.at(-1).stale, false);
assert.equal(battle.failed, false);
extension.call({context});
assert.equal(targets().length, 4, 'nothing after the scoped click');
`);
''')


def test_click_probe_distinguishes_duplicates_nesting_threads_and_old_generations():
    agent_check(r'''
load(`
const click = hooks.get(Number(BUILD.simulate_click[0]));
const target = hooks.get(Number(BUILD.click_extension[0]));
const component = ptr(0x6000000), session = ptr(0x6100000);
const context = {rcx: component, rdx: ptr(0), r8: ptr(0), r9: ptr(0x123456)};
battle = {session, emitted: 1, failed: false};
const first = {}, nested = {};
click.onEnter.call(first, [component]);
click.onEnter.call(nested, [component]);
target.call({context});
assert.equal(messages.at(-1).call, nested.click.call);
click.onLeave.call(nested);
Process.getCurrentThreadId = () => 8;
const length = messages.length;
target.call({context});
assert.equal(messages.length, length, 'another thread is outside the scope');
Process.getCurrentThreadId = () => 7;
target.call({context});
assert.equal(messages.at(-1).call, first.click.call);
click.onLeave.call(first);
const duplicate = {};
click.onEnter.call(duplicate, [component]);
assert.notEqual(duplicate.click.call, first.click.call);
// Even address reuse cannot turn an old scope into a new-session event.
generation++;
battle = {session, emitted: 1, failed: false};
const count = messages.length;
target.call({context});
assert.equal(messages.length, count);
click.onLeave.call(duplicate);
assert.equal(messages.at(-1).event, 'ui_click_return');
assert.equal(messages.at(-1).stale, true);
assert.equal(messages.filter(r => r.event === 'ui_click_enter').length, 3);
assert.equal(messages.filter(r => r.event === 'ui_click_return').length, 3);
`);
''')


def test_click_probe_preserves_a_failed_read_and_stops_further_target_collection():
    agent_check(r'''
load(`
battle = {session: ptr(0x6100000), emitted: 1, failed: false};
const click = hooks.get(Number(BUILD.simulate_click[0]));
const callback = hooks.get(Number(BUILD.click_callback[0]));
const extension = hooks.get(Number(BUILD.click_extension[0]));
const invocation = {};
click.onEnter.call(invocation, [ptr(0x6000000)]);
const context = {rax: ptr(0x100000), rcx: ptr(0x6000000), rdx: ptr(0),
                 r8: ptr(0), r9: ptr(0x123456)};
callback.call({context});  // the referenced vtable slot is intentionally unreadable
assert.equal(messages.at(-1).event, 'probe_error');
assert.equal(messages.at(-1).where, 'click_callback');
assert.equal(battle.failed, true);
const count = messages.length;
extension.call({context});
assert.equal(messages.length, count);
click.onLeave.call(invocation);
assert.equal(messages.filter(r => r.event === 'ui_call_target').length, 0);
`);
''')


def test_click_probe_does_not_accept_an_unreadable_target_outside_the_executable():
    agent_check(r'''
load(`
battle = {session: ptr(0x6100000), emitted: 1, failed: false};
const click = hooks.get(Number(BUILD.simulate_click[0]));
const extension = hooks.get(Number(BUILD.click_extension[0]));
const invocation = {}, bad = ptr(0x6001000);
bad.readByteArray = () => { throw new Error('unreadable external target'); };
const context = {rcx: ptr(0x6000000), rdx: ptr(0), r8: ptr(0), r9: bad};
click.onEnter.call(invocation, [context.rcx]);
extension.call({context});
assert.equal(messages.at(-1).event, 'probe_error');
assert.match(messages.at(-1).message, /unreadable external target/);
assert.equal(battle.failed, true);
assert.equal(messages.filter(r => r.event === 'ui_call_target').length, 0);
click.onLeave.call(invocation);
`);
''')


def test_click_probe_records_a_dll_target_relative_to_its_own_loaded_module():
    agent_check(r'''
load(`
battle = {session: ptr(0x6100000), emitted: 1, failed: false};
const click = hooks.get(Number(BUILD.simulate_click[0]));
const extension = hooks.get(Number(BUILD.click_extension[0]));
const invocation = {}, target = ptr(0x6001234);
Process.findModuleByAddress = address => {
    assert.ok(address.equals(target));
    return {name: 'clockwork.Release.x64.dll', path: 'C:/game/clockwork.Release.x64.dll',
            base: ptr(0x6000000)};
};
const context = {rcx: ptr(0x6000000), rdx: ptr(0), r8: ptr(0), r9: target};
click.onEnter.call(invocation, [context.rcx]);
extension.call({context});
const entry = messages.at(-1);
assert.equal(entry.event, 'ui_call_target');
assert.equal(entry.rva, null, 'a DLL address is not an executable RVA');
assert.equal(entry.module.name, 'clockwork.Release.x64.dll');
assert.equal(entry.module.base, '0x6000000');
assert.equal(entry.module.rva, '0x1234');
assert.equal(entry.bytes.length, 32);
assert.equal(battle.failed, false);
click.onLeave.call(invocation);
`);
''')
