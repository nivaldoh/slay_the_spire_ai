// Direct lifecycle operations for one owned WH3 client, build 26403568 only.
// A fixed operation list: no generic native call, Lua evaluation or memory write.
// ready_deployment calls the engine's own sender 0x1bfa108, the routine Start Battle's
// receiver 0x1c3bc48 calls (static reading; a live trace must confirm it). It finds no UI
// component, but needs the battle-interface object at global 0x448f180, so this is not yet
// proven headless. Requests wait for session_step on the game thread, because a Frida RPC
// runs on another thread (frida.re/docs/javascript-api). The stream is handed off elsewhere
// in the frame (0x2d82540), so a command written here goes out on the next hand-off.
// Requested and submitted are separate rows. Readiness itself is not reported here: the
// passive agent's end_deployment_execute row shows the engine's count, which is anonymous.
'use strict';

const BUILD = {
    session_step: ['0x2d78568', '48895c241048896c2418565741544156'],
    end_deployment: ['0x1bfa108', '4c8bdc49895b0849896b104989731849'],
};
const VTABLE = {session: 0x3ab9b38};
const GLOBAL = {battle_interface: 0x448f180};
const SESSION = {env: 0x20};
const ENV = {setup: 0x448, provider: 0x644e8, network: 0x645c8, flag_a: 0x3b0, flag_b: 0x3b1};
const UI = {env: 0x418, deployment_flag: 0x15cf};
const SETUP = {phase: 0xc8};
const PROVIDER = {write_offset: 0x5008};
const REQUEST_MS = 30000;   // rests on JUDGEMENT? multiplayer_adapter.py Request bound

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

let sequence = 0, pending = null;
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
    return {ui, env, stream: env.add(ENV.provider).readPointer()};
}
// The checks 0x1bfa108 makes silently, read first so a refusal is reported. Phase 0 and 4
// are what the engine's own IsDeploymentPhase (0x1e8933c) accepts; it also sends in phase 1.
function refusal(state) {
    if (state.refused) return state.refused;
    const {ui, env, stream} = state;
    const phase = env.add(ENV.setup).readPointer().add(SETUP.phase).readU32();
    if (phase !== 0 && phase !== 4) return 'not deployment: phase ' + phase;
    if (ui.add(UI.deployment_flag).readU8() !== 0) return 'already sent';
    if (env.add(ENV.flag_a).readU8() !== 0 || env.add(ENV.flag_b).readU8() !== 0)
        return 'engine flags set';
    if (env.add(ENV.network).readPointer().isNull()) return 'not a network battle';
    if (stream.isNull()) return 'no input stream';
    return null;
}
function run(request, session) {
    const state = current(session), reason = refusal(state);
    if (reason) {
        record('operation_result', {request: request.request, status: 'refused', reason});
        return;
    }
    // The sender sets its flag before its own checks, so only a written packet shows it sent.
    const offset = () => state.stream.add(PROVIDER.write_offset).readU32();
    const before = offset();
    endDeployment(state.ui);
    const after = offset();
    record('operation_result', {request: request.request,
                                status: after > before ? 'submitted' : 'unknown',
                                stream_offset: [before, after]});
}
function expire() {
    if (!pending || Date.now() <= pending.deadline) return;
    record('operation_result', {request: pending.request, status: 'expired'});
    pending = null;
}
const listener = Interceptor.attach(addresses.session_step, {
    onEnter(args) {
        expire();
        if (!pending) return;
        const request = pending;
        pending = null;
        try {
            run(request, args[0]);
        } catch (e) {
            record('operation_result', {request: request.request, status: 'unknown',
                                        reason: String(e)});
        }
    },
});
setInterval(expire, 1000);   // no battle frames run in the frontend
rpc.exports = {
    submit(operation, request) {
        if (operation !== 'ready_deployment') throw new Error('unknown operation ' + operation);
        // A repeated request id is reported, never resubmitted, even after a refusal.
        if (seen.has(request)) return 'duplicate';
        if (pending) return 'busy';
        seen.add(request);
        pending = {request, deadline: Date.now() + REQUEST_MS};
        record('operation_requested', {request, operation});
        return 'queued';
    },
};
record('adapter_ready', {capabilities: ['ready_deployment'], unverified: true});
