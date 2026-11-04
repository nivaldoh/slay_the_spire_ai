// Direct lifecycle operations for one owned WH3 client, build 26403568 only.
// A fixed operation list: no generic native call, Lua evaluation or memory write.
// ready_deployment calls the engine's own sender 0x1bfa108, the routine the Start Battle
// button reaches (trace: foundation-ref5). It finds no UI component. It does use the
// battle-interface object at global 0x448f180, so this is not yet proven headless.
// Requests wait for session_step on the game thread, where the input it reads next is
// assembled, because a Frida RPC call runs on another thread (frida.re/docs/javascript-api).
// Requested, submitted and applied are separate: a native return is not readiness.
'use strict';

const BUILD = {
    session_step: ['0x2d78568', '48895c241048896c2418565741544156'],
    end_deployment: ['0x1bfa108', '4c8bdc49895b0849896b104989731849'],
};
const VTABLE = {session: 0x3ab9b38};
const GLOBAL = {battle_interface: 0x448f180};
const SESSION = {env: 0x20};
const ENV = {setup: 0x448, model: 0x440, network: 0x645c8, flag_a: 0x3b0, flag_b: 0x3b1};
const UI = {env: 0x418, deployment_flag: 0x15cf};
const SETUP = {phase: 0xc8};
// The tick hands the command handler [env+0x440]; it counts at [that+0x150]+0x9b8.
const MODEL = {state: 0x150};
const STATE = {ready_count: 0x9b8};
const REQUEST_MS = 30000;   // JUDGEMENT?: see multiplayer_adapter.py Request bound.

const main = Process.getModuleByName('Warhammer3.exe');
const hex = bytes => Array.from(new Uint8Array(bytes))
    .map(b => b.toString(16).padStart(2, '0')).join('');
const addresses = {};
for (const [name, [rva, bytes]] of Object.entries(BUILD)) {
    const address = main.base.add(rva);
    if (hex(address.readByteArray(bytes.length / 2)) !== bytes)
        throw new Error('Unsupported multiplayer adapter signature: ' + name);
    addresses[name] = address;
}
const endDeployment = new NativeFunction(addresses.end_deployment, 'void', ['pointer']);

let sequence = 0, pending = null, waiting = null;
const seen = new Set();
function record(event, data) {
    send({event, seq: ++sequence, source_wall_ms: Date.now(),
          thread: Process.getCurrentThreadId(), adapter: true, ...data});
}
// Every handle is re-read here, never kept across frames: the battle interface and
// environment do not outlive a battle.
function current(session) {
    if (!session.readPointer().equals(main.base.add(VTABLE.session)))
        return {refused: 'unexpected session layout'};
    const ui = main.base.add(GLOBAL.battle_interface).readPointer();
    if (ui.isNull()) return {refused: 'no battle interface'};
    const env = session.add(SESSION.env).readPointer();
    if (!ui.add(UI.env).readPointer().equals(env)) return {refused: 'stale battle interface'};
    return {ui, env, state: env.add(ENV.model).readPointer().add(MODEL.state).readPointer()};
}
// The checks 0x1bfa108 makes silently, read first so a refusal is reported. Phase 0 and 4
// are what the engine's own IsDeploymentPhase (0x1e8933c) accepts.
function refusal(state) {
    if (state.refused) return state.refused;
    const {ui, env} = state, phase = env.add(ENV.setup).readPointer().add(SETUP.phase).readU32();
    if (phase !== 0 && phase !== 4) return 'not deployment: phase ' + phase;
    if (ui.add(UI.deployment_flag).readU8() !== 0) return 'already sent';
    if (env.add(ENV.flag_a).readU8() !== 0 || env.add(ENV.flag_b).readU8() !== 0)
        return 'engine flags set';
    if (env.add(ENV.network).readPointer().isNull()) return 'not a network battle';
    return null;
}
function run(request, session) {
    if (Date.now() > request.deadline) {
        record('operation_result', {request: request.request, status: 'expired'});
        return;
    }
    const state = current(session), reason = refusal(state);
    if (reason) {
        record('operation_result', {request: request.request, status: 'refused', reason});
        return;
    }
    const before = state.state.add(STATE.ready_count).readU32();
    endDeployment(state.ui);
    // The guards above passed, so the flag means the sender ran its body. Only the count
    // ("applied") shows the engine took the command.
    const sent = state.ui.add(UI.deployment_flag).readU8() === 1;
    record('operation_result', {request: request.request, status: sent ? 'submitted' : 'unknown',
                                ready_count: before});
    if (sent) waiting = {request: request.request, env: state.env, before};
}
function check(session) {
    const state = current(session);
    if (state.refused || !state.env.equals(waiting.env)) {
        record('operation_result', {request: waiting.request, status: 'unknown',
                                    reason: state.refused || 'battle changed'});
        waiting = null;
        return;
    }
    const count = state.state.add(STATE.ready_count).readU32();
    if (count > waiting.before) {
        record('operation_result', {request: waiting.request, status: 'applied',
                                    ready_count: count});
        waiting = null;
    }
}
const listener = Interceptor.attach(addresses.session_step, {
    onEnter(args) {
        if (!pending && !waiting) return;
        const request = pending;
        pending = null;
        try {
            if (request) run(request, args[0]);
            else check(args[0]);
        } catch (e) {
            const id = request ? request.request : waiting.request;
            waiting = null;
            record('operation_result', {request: id, status: 'unknown', reason: String(e)});
        }
    },
});
rpc.exports = {
    submit(operation, request) {
        if (operation !== 'ready_deployment') throw new Error('unknown operation ' + operation);
        // A repeated request id is reported, never resubmitted.
        if (seen.has(request)) return 'duplicate';
        if (pending || waiting) return 'busy';
        seen.add(request);
        pending = {request, deadline: Date.now() + REQUEST_MS};
        record('operation_requested', {request, operation});
        return 'queued';
    },
};
record('adapter_ready', {capabilities: ['ready_deployment'], unverified: true});
