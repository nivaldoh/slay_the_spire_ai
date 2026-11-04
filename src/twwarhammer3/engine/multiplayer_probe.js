// Passive reference probe for foundation stage 1, build 26403568 only.
// Followed Frida's Interceptor per-invocation storage (javascript-api/#interceptor).
// The MP deployment constructor installs vtable 0x37c45f0. Its +0x188 dispatcher
// resolves event names in table 0x448ff18 before tail-calling the result. Record that
// result for bounded follow-up; a callback invocation is NOT native submission/readiness.
// No RPC, game NativeFunction, Lua evaluation, state writes or checkpoint restoration.
'use strict';

const BUILD = {
    deployment_dispatch: ['0x1bef0c0', '40534883ec20488bd94d8bd8488d0d45'],
    event_lookup: ['0x22db234', '4c8bd2eb234d8bca4c2bc80fb610460f'],
    env_ctor: ['0x2d9f56c', '4c894c24204889542410555356574154'],
    session_ctor: ['0x2d20c68', '48895c24084889742410574883ec3048'],
    post_tick: ['0x2dda3ac', '488bc44889580848897010488978184c'],
    session_step: ['0x2d78568', '48895c241048896c2418565741544156'],
    simulate_click: ['0x22d1f58', '48895c2410574883ec20488379180048'],
    click_extension: ['0x22bacfd', '4d8bc733d241ffd1488b9f000200008b'],
    click_callback: ['0x22bad3a', '498bd7ff50684883c378493bde75d240'],
    click_component: ['0x22bad5e', 'ff90f800000080bf5c03000000741548'],
    click_event: ['0x22bae58', 'e89fd208ff90488d4de0e8d99523fe90'],
    end_deployment_receiver: ['0x1c3bc48', '40534883ec50488d05bb16e00148c744'],
    end_deployment: ['0x1bfa108', '4c8bdc49895b0849896b104989731849'],
    end_deployment_command: ['0x1bc9350', '48895c2418574883ec408b0544f04a02'],
    command_packet: ['0x1bd09b0', '48895c24084c8bda488bd94c89590833'],
    end_deployment_execute: ['0x2ed483c', '48895c2410574883ec2041b904000000'],
};
const VTABLE = {deployment: 0x37c45f0, session: 0x3ab9b38};
const ENV = {tick: 0x64720, checksums: 0x64598, worker_job: 0x64810, setup: 0x448, model: 0x440,
             network: 0x645c8, provider: 0x644e8, local_entries: 0x3a8, local_index: 0x3b4,
             flag_a: 0x3b0, flag_b: 0x3b1};
const UI = {env: 0x418, deployment_flag: 0x15cf};
// The tick hands each command handler [env+0x440] (0x2ddab54 -> 0x2f0b580 -> call rax).
const MODEL = {state: 0x150};
const STATE = {alliance_count: 0x134, alliances: 0x138, ready_count: 0x9b8,
               ready_countdown: 0x9b4};
const PROVIDER = {buffer: 8, write_offset: 0x5008};
// Unit fields as the battle_unit Lua getters read them (table 0x3d4ac70): ui id 0x2f22df8,
// men 0x2f03cdc, ammo 0x2ec5688, bearing 0x2ec9c88, position 0x30409f0. The morale word is
// the state 0x303bd08 reads for is_routing. Hit points: 0x310da24 reads unit+0x80 and +0x88
// among others; these two are raw words. The walk is the one Lua's alliances/armies/units
// make, through the model state: 0x2ec53d0, 0x2dd8f28, 0x2ed0708.
const WORLD = {phase: 0xc8};
const ALLIANCE = {army_count: 0x34, armies: 0x38};
const ARMY = {unit_count: 0x164, units: 0x168};
const UNIT = {hp_a: 0x80, hp_b: 0x88, men: 0xa4, body: 0x32f8, morale: 0x3b70, ammo: 0x3d90,
              ui_id: 0x3ea0};
const BODY = {bearing: 0xb70, position: 0xc10, attached: 0xc28, entity: 0xc90};
const ENTITY = {position: 0x88};
// Rests on JUDGEMENT docs/twwarhammer3/multiplayer-control-foundation.md Raw witness: every
// ten completed ticks, plus the last completed tick before a local command packet and the
// first after it. Floats stay as raw 32-bit words, so no rounding hides a difference.
// Evaluator-only: this reaches native.jsonl, never a policy.
const WITNESS_EVERY = 10;
const main = Process.getModuleByName('Warhammer3.exe');
const hex = bytes => Array.from(new Uint8Array(bytes))
    .map(b => b.toString(16).padStart(2, '0')).join('');
const addresses = {};
// Validate EVERY signature and layout before attaching ANY hook.
for (const [name, [rva, bytes]] of Object.entries(BUILD)) {
    const address = main.base.add(rva);
    if (hex(address.readByteArray(bytes.length / 2)) !== bytes)
        throw new Error('Unsupported multiplayer probe signature: ' + name);
    addresses[name] = address;
}
if (!main.base.add(VTABLE.deployment + 0x188).readPointer().equals(addresses.deployment_dispatch))
    throw new Error('Unsupported multiplayer deployment layout');

let sequence = 0, callId = 0, generation = 0, battle = null;
const active = new Map(), clicks = new Map(), listeners = [];
function record(event, data = {}) {
    // Date.now is sampled IN the Windows process, before transport/file handling.
    // It is a wall clock, not tick alignment or proof of simulation rate.
    send({event, seq: ++sequence, source_wall_ms: Date.now(),
          thread: Process.getCurrentThreadId(), generation, ...data});
}
function failure(where, error) {
    record('probe_error', {where, message: String(error)});
    if (battle) battle.failed = true;
}
function hook(name, callbacks) {
    listeners.push(Interceptor.attach(addresses[name], callbacks));
}
function unitRow(alliance, army, index, unit) {
    const body = unit.add(UNIT.body).readPointer();
    const row = [alliance, army, index, unit.add(UNIT.ui_id).readU32(), unit.add(UNIT.men).readU32(),
                 unit.add(UNIT.hp_a).readU32(), unit.add(UNIT.hp_b).readU32(),
                 unit.add(UNIT.ammo).readU32(), unit.add(UNIT.morale).readU32()];
    if (body.isNull()) return row;   // a unit with no body on the field has no position
    const entity = body.add(BODY.entity).readPointer();
    const attached = !body.add(BODY.attached).readPointer().isNull();
    // Position kind: 0 entity, 1 the unit's own, 2 attached to something (0x31296c4 asks it).
    const kind = entity.isNull() ? (attached ? 2 : 1) : 0;
    const at = entity.isNull() ? body.add(BODY.position) : entity.add(ENTITY.position);
    row.push(kind, at.readU32(), at.add(4).readU32(), at.add(8).readU32(),
             body.add(BODY.bearing).readU32() & 0xffff);
    return row;
}
function witnessRows(env) {
    const state = env.add(ENV.model).readPointer().add(MODEL.state).readPointer();
    const rows = [], alliances = state.add(STATE.alliances).readPointer();
    for (let a = 0, n = state.add(STATE.alliance_count).readU32(); a < n; a++) {
        const alliance = alliances.add(a * 8).readPointer();
        const armies = alliance.add(ALLIANCE.armies).readPointer();
        for (let b = 0, m = alliance.add(ALLIANCE.army_count).readU32(); b < m; b++) {
            const army = armies.add(b * 8).readPointer();
            const units = army.add(ARMY.units).readPointer();
            for (let c = 0, k = army.add(ARMY.unit_count).readU32(); c < k; c++)
                rows.push(unitRow(a, b, c, units.add(c * 8).readPointer()));
        }
    }
    return rows;
}
function currentClick() {
    const stack = clicks.get(Process.getCurrentThreadId());
    const call = stack && stack[stack.length - 1];
    return call && call.generation === generation && call.battle === battle &&
        battle && !battle.failed && battle.session && battle.session.equals(call.session) ? call : null;
}

try {
    hook('deployment_dispatch', {
        onEnter(args) {
            this.call = null;
            try {
                if (!args[0].readPointer().equals(main.base.add(VTABLE.deployment)))
                    throw new Error('unexpected deployment callback object');
                this.call = {call: ++callId, object: args[0].toString(),
                             name: args[1].readUtf8String(), argument: args[2].toString()};
                const thread = Process.getCurrentThreadId(), stack = active.get(thread) || [];
                stack.push(this.call);
                active.set(thread, stack);
                record('deployment_callback_enter', this.call);
            } catch (e) { failure('deployment_dispatch', e); }
        },
        onLeave() {
            if (!this.call) return;
            const thread = Process.getCurrentThreadId(), stack = active.get(thread);
            if (!stack || stack.pop() !== this.call) {
                failure('deployment_dispatch', 'unmatched return');
                return;
            }
            if (!stack.length) active.delete(thread);
            record('deployment_callback_return', {call: this.call.call});
        },
    });
    hook('event_lookup', {
        onEnter(args) {
            this.call = null;
            const stack = active.get(Process.getCurrentThreadId());
            if (stack && stack.length && args[0].equals(main.base.add(0x448ff18)))
                this.call = stack[stack.length - 1].call;
        },
        onLeave(result) {
            if (this.call === null) return;
            try {
                const inMain = result.compare(main.base) >= 0 &&
                    result.compare(main.base.add(main.size)) < 0;
                record('deployment_handler_resolved', {
                    call: this.call, address: result.toString(),
                    rva: inMain ? result.sub(main.base).toString() : null,
                    bytes: inMain ? hex(result.readByteArray(16)) : null,
                });
            } catch (e) { failure('event_lookup', e); }
        },
    });
    hook('env_ctor', {
        onEnter(args) { this.env = args[0]; },
        onLeave() {
            generation++;
            battle = {env: this.env, session: null, pending: null, emitted: 0, failed: false,
                      last: null, commanded: false, provider: null};
            record('environment_created');
        },
    });
    hook('session_ctor', {
        onEnter(args) { this.session = args[0]; },
        onLeave() {
            if (!battle || battle.failed) return;
            try {
                if (!this.session.readPointer().equals(main.base.add(VTABLE.session)) ||
                    !this.session.add(0x20).readPointer().equals(battle.env))
                    throw new Error('unexpected battle session layout');
                battle.session = this.session;
                record('session_created');
            } catch (e) { failure('session_ctor', e); }
        },
    });
    hook('post_tick', {
        onEnter(args) {
            if (!battle || battle.failed || !args[0].equals(battle.env)) return;
            try {
                const env = battle.env, tick = env.add(ENV.tick).readU32();
                const entry = env.add(ENV.checksums).readPointer().add(0x48).readPointer();
                if (entry.isNull() || entry.add(0x18).readU32() !== tick)
                    throw new Error('no checksum for tick ' + tick);
                battle.pending = {tick, checksum: entry.add(0x14).readU32()};
            } catch (e) { failure('post_tick', e); }
        },
    });
    hook('session_step', {
        onEnter(args) { this.session = args[0]; this.generation = generation; },
        onLeave(result) {
            const b = battle;
            if (!b || b.failed || this.generation !== generation || !b.session ||
                !b.session.equals(this.session) || !b.pending) return;
            try {
                // session_step returns its output buffer, not a Boolean register value:
                // native 0x2d786c1/0x2d786f0 writes byte 0, 0x2d78701 returns that pointer.
                if (result.readU8() !== 1) return;
                const env = this.session.add(0x20).readPointer(), p = b.pending;
                // Same boundary as checkpoints: consumed frame, joined worker, counters agree.
                if (!env.equals(b.env) || !env.add(ENV.worker_job).readPointer().isNull() ||
                    env.add(ENV.tick).readU32() !== p.tick || p.tick <= b.emitted) return;
                b.emitted = p.tick;
                const world = env.add(ENV.setup).readPointer();
                record('completed_tick', {...p, phase: world.add(WORLD.phase).readU32()});
                const sample = {tick: p.tick, units: witnessRows(env), sent: false};
                if (b.commanded && b.last && !b.last.sent)
                    record('witness', {tick: b.last.tick, units: b.last.units,
                                       reason: 'before_command'});
                if (b.commanded || p.tick % WITNESS_EVERY === 0) {
                    record('witness', {tick: sample.tick, units: sample.units,
                                       reason: b.commanded ? 'after_command' : 'schedule',
                                       before_available: !b.commanded || !!b.last});
                    sample.sent = true;
                }
                b.commanded = false;
                b.last = sample;
            } catch (e) { failure('session_step', e); }
        },
    });
    // Reference-only input tracing. The generic named-event dispatcher above was absent
    // from foundation-ref1. The name/function pair at 0x3d46900/08 binds the script method
    // to 0x22d1f58; the Cco proxy's 0x22d1ed0 scope was absent in foundation-ref3.
    // These are UI component calls, not a UI-independent readiness operation.
    hook('simulate_click', {
        onEnter(args) {
            this.click = null;
            if (!battle || battle.failed || !battle.session) return;
            const stack = clicks.get(Process.getCurrentThreadId()) || [];
            this.click = {call: ++callId, battle, session: battle.session, generation};
            stack.push(this.click);
            clicks.set(Process.getCurrentThreadId(), stack);
            record('ui_click_enter', {call: this.click.call, receiver: args[0].toString(),
                                     receiver_kind: 'UIComponent_script_wrapper',
                                     last_completed_tick: battle.emitted});
        },
        onLeave() {
            if (!this.click) return;
            const thread = Process.getCurrentThreadId(), stack = clicks.get(thread);
            if (!stack || stack.pop() !== this.click) {
                failure('simulate_click', 'unmatched return');
                return;
            }
            if (!stack.length) clicks.delete(thread);
            record('ui_click_return', {call: this.click.call, generation: this.click.generation,
                stale: this.click.generation !== generation || this.click.battle !== battle});
        },
    });
    for (const site of ['click_extension', 'click_callback', 'click_component', 'click_event']) {
        // These are points before call instructions, not ABI function entries. The first
        // two precede final argument setup (short call sites could not be intercepted in
        // foundation-ref2); R9/RAX already hold the targets. Snapshots are raw registers,
        // not function arguments. Frida supplies this.context; ignore args mid-function.
        hook(site, function () {
            const call = currentClick();
            if (!call) return;
            try {
                const c = this.context;
                let target;
                if (site === 'click_extension') target = c.r9;
                else if (site === 'click_callback') target = c.rax.add(0x68).readPointer();
                else if (site === 'click_component') target = c.rax.add(0xf8).readPointer();
                else target = main.base.add(0x13480fc);
                const inMain = target.compare(main.base) >= 0 &&
                    target.compare(main.base.add(main.size)) < 0;
                // A DLL target is valid discovery evidence too, but an unreadable address
                // must fail capture just like one in the executable. Retain its module base
                // so a later process's load address cannot be mistaken for the same offset.
                const bytes = hex(target.readByteArray(16));
                const module = inMain ? main : Process.findModuleByAddress(target);
                record('ui_call_target', {call: call.call, site, target: target.toString(),
                    rva: inMain ? target.sub(main.base).toString() : null,
                    bytes, module: module ? {name: module.name, path: module.path,
                        base: module.base.toString(), rva: target.sub(module.base).toString()} : null,
                    registers: {rcx: c.rcx.toString(), rdx: c.rdx.toString(),
                                r8: c.r8.toString(), r9: c.r9.toString()},
                    last_completed_tick: battle.emitted,
                    evidence: 'target_before_call_instruction'});
            } catch (e) { failure(site, e); }
        });
    }
    // Readiness path read from the pinned disassembly: button signal -> receiver 0x1c3bc48
    // -> 0x1bfa108 (one-shot, local army) -> typed command BCQ_ARMY_ORDER_END_DEPLOYMENT_PHASE
    // 0x1bc9350 -> packet 0x1bd09b0 on the input provider; its execute handler is 0x2ed483c.
    // Function entries, so args are ABI arguments. Whether this is the path a real click
    // takes is what this trace checks; it says nothing of other peers or of the session.
    const tick = () => battle ? battle.emitted : null;
    hook('end_deployment_receiver', {
        onEnter(args) {
            record('end_deployment_receiver', {receiver: args[0].toString(),
                                                last_completed_tick: tick()});
        },
    });
    hook('end_deployment', {
        onEnter(args) {
            try {
                this.ui = args[0];
                const env = this.ui.add(UI.env).readPointer();
                const entries = env.add(ENV.local_entries).readPointer();
                const index = env.add(ENV.local_index).readU32();
                // 0x1bfa108 sets this flag before its checks: 1 afterwards does not prove a
                // command went out; end_deployment_command and command_packet do.
                record('end_deployment_enter', {
                    flag_before: this.ui.add(UI.deployment_flag).readU8(),
                    same_env: !!battle && env.equals(battle.env),
                    setup_kind: env.add(ENV.setup).readPointer().add(0xc8).readU32(),
                    flags: [env.add(ENV.flag_a).readU8(), env.add(ENV.flag_b).readU8()],
                    network: env.add(ENV.network).readPointer().toString(),
                    local_index: index,
                    local_entry: entries.isNull() ? null : [entries.add(index * 8).readU32(),
                                                            entries.add(index * 8 + 4).readU32()],
                    last_completed_tick: tick(),
                });
            } catch (e) { this.ui = null; failure('end_deployment', e); }
        },
        onLeave() {
            if (!this.ui) return;
            try {
                record('end_deployment_return', {
                    flag_after: this.ui.add(UI.deployment_flag).readU8()});
            } catch (e) { failure('end_deployment', e); }
        },
    });
    hook('end_deployment_command', {
        onEnter(args) {
            try {
                const vtable = args[1].readPointer();
                record('end_deployment_command', {
                    provider_is_env: !!battle && args[0].equals(
                        battle.env.add(ENV.provider).readPointer()),
                    command_vtable: vtable.sub(main.base).toString(),
                    // Stored reversed from local_entry: 0x1bfa198..0x1bfa1ac.
                    fields: [args[1].add(8).readU32(), args[1].add(12).readU32()],
                    last_completed_tick: tick(),
                });
            } catch (e) { failure('end_deployment_command', e); }
        },
    });
    hook('command_packet', {
        onEnter(args) {
            if (!battle || battle.failed) return;
            try {
                // Kept once read: a packet after the battle ended must not touch its freed
                // environment (0x1bd09b0 also serves the campaign queue).
                if (!battle.provider || battle.provider.isNull())
                    battle.provider = battle.env.add(ENV.provider).readPointer();
                if (!args[1].equals(battle.provider.add(PROVIDER.buffer))) return;
                battle.commanded = true;
                record('command_packet', {
                    id: args[2].readU32(), flags: args[3].toInt32() & 0xff,
                    offset: args[1].add(PROVIDER.write_offset - PROVIDER.buffer).readU32(),
                    last_completed_tick: tick(),
                });
            } catch (e) { failure('command_packet', e); }
        },
    });
    hook('end_deployment_execute', {
        onEnter(args) {
            try {
                this.state = args[1].add(MODEL.state).readPointer();
                this.same_model = !!battle && args[1].equals(
                    battle.env.add(ENV.model).readPointer());
                this.before = [this.state.add(STATE.ready_count).readU32(),
                               this.state.add(STATE.ready_countdown).readU32()];
            } catch (e) { this.state = null; failure('end_deployment_execute', e); }
        },
        onLeave() {
            if (!this.state) return;
            try {
                record('end_deployment_execute', {
                    same_model: this.same_model, before: this.before,
                    after: [this.state.add(STATE.ready_count).readU32(),
                            this.state.add(STATE.ready_countdown).readU32()],
                    last_completed_tick: tick(),
                });
            } catch (e) { failure('end_deployment_execute', e); }
        },
    });
} catch (e) {
    for (const listener of listeners) listener.detach();
    throw e;
}
record('ready', {base: main.base.toString(), path: main.path, diagnostic_only: true,
                 capabilities: [], missing: ['native lifecycle operations', 'ending readback',
                                             'peer calibration']});
