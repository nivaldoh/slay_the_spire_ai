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
};
const VTABLE = {deployment: 0x37c45f0, session: 0x3ab9b38};
const ENV = {tick: 0x64720, checksums: 0x64598, worker_job: 0x64810};
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
            battle = {env: this.env, session: null, pending: null, emitted: 0, failed: false};
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
                record('completed_tick', p);
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
} catch (e) {
    for (const listener of listeners) listener.detach();
    throw e;
}
record('ready', {base: main.base.toString(), path: main.path, diagnostic_only: true,
                 capabilities: [], missing: ['native lifecycle operations', 'raw witnesses',
                     'submission tracing', 'phase and ending readback', 'peer calibration']});
