// WH3 battle checkpoints: Frida agent. Total War: WARHAMMER III, Steam build 25961564 only;
// every native address is checked against its expected bytes before use.
//
// Save: write the game's replay file (battle setup and every input so far) at a completed
// tick, plus the Lua random seed from tick 1. Restore: when that replay is opened from the
// Replays menu, run it as a live battle, rebuild it quickly while checking every tick's
// checksum against the file, and hand over live control at the saved tick.
//
// Published without the test hooks as github.com/nivaldoh/wh3-battle-checkpoints (v0.1.0).
// The hooks (CONFIG, set by checkpoint_frida.py) save at exact ticks and run Lua on the battle
// script state at exact ticks, for twwarhammer3.battle.checkpoint and its live check.
'use strict';
const CONFIG = null;  // replaced by checkpoint_frida.py


const BUILD = {
    post_tick: ['0x2dd3304', '488bc44889580848897010488978184c'],
    session_step: ['0x2d714a8', '48895c241048896c2418565741544156'],
    session_ctor: ['0x2d19a18', '48895c24084889742410574883ec3048'],
    env_ctor: ['0x2d98420', '4c894c24204889542410555356574154'],
    tick_threading_check: ['0x2db0e08', '40534883ec2080b9e045060000488bd9'],
    save_replay: ['0x2dd7698', '48895c240855488d6c24904881ec7001'],
    string_from_utf16: ['0x4eb5d0', '40534883ec20488bd94c8bc233c94889'],
    string_free: ['0x4d34b4', '40534883ec30488b5908488d058fd8a9'],
    string_from_utf8: ['0x4d7960', '40534883ec20488bd948c74108000000'],
    string_free_utf8: ['0x4d49d0', '40534883ec20488b5908488d056fc3a9'],
    allocate: ['0x4d3da0', '48895c2408574883ec3065488b042558'],
    make_live_provider: ['0x1b9c678', '48895c2408574883ec20488361080048'],
    crt_existing_context: ['0x116bb58', '40534883ec208bd94c8d0df9605502b9'],
    crt_current_context: ['0x1168d74', '48895c24084889742410574883ec20ff'],
    luaL_loadbuffer: ['0x18415b0', '4883ec384889542420488d1504f8ffff'],
    lua_gettop: ['0x183ee38', '488b4110482b411848c1f804c3cccccc'],
    lua_settop: ['0x183f940', '85d278294863d24803d2eb0d488b4110'],
    lua_checkstack: ['0x183e9a0', '48895c2408574883ec204c8b4110488b'],
    lua_pcall: ['0x183f1a8', '48895c2408574883ec4033c0418bf844'],
    lua_tolstring: ['0x183fa80', '48895c24084889742410574883ec2049'],
};
const VTABLE = {session: 0x3aaf118, replay_provider: 0x3ab4830, live_provider: 0x3a2e0c0, recording: 0x38bfbc0};
const GLOBAL = {tick_interval: 0x3d0e294, input_name: 0x3ab2ec0, debug_replay: 0x3f69b94, crt_context_index: 0x3d0d9c8};
// Battle environment fields (build-specific).
const ENV = {tick: 0x64720, checksums: 0x64598, provider_cache: 0x64770, replay: 0x645d0,
             replay_flag: 0x645e0, recording: 0x645f0, worker_job: 0x64810};
const REBUILD_SPEED = 1000.0;   // replay input speed while rebuilding (constructor value 1.0)
const SLOW_DOWN_TICKS = 50;     // rebuild the last 5 s at 1x

const main = Process.getModuleByName('Warhammer3.exe');
const hex = bytes => Array.from(new Uint8Array(bytes)).map(b => b.toString(16).padStart(2, '0')).join('');
function at(name) {
    const [rva, bytes] = BUILD[name], address = main.base.add(rva);
    if (hex(address.readByteArray(bytes.length / 2)) !== bytes)
        throw new Error('This game build is not supported (byte check failed at ' + name + ')');
    return address;
}
const fn = (name, ret, args) => new NativeFunction(at(name), ret, args);
const engine = {
    save_replay: fn('save_replay', 'void', ['pointer', 'pointer']),
    string_from_utf16: fn('string_from_utf16', 'pointer', ['pointer', 'pointer']),
    string_free: fn('string_free', 'void', ['pointer']),
    string_from_utf8: fn('string_from_utf8', 'pointer', ['pointer', 'pointer']),
    string_free_utf8: fn('string_free_utf8', 'void', ['pointer']),
    allocate: fn('allocate', 'pointer', ['uint64']),
    make_live_provider: fn('make_live_provider', 'pointer', ['pointer', 'uint', 'pointer']),
    crt_existing_context: fn('crt_existing_context', 'pointer', ['uint']),
    crt_current_context: fn('crt_current_context', 'pointer', []),
};
const vtable = name => main.base.add(VTABLE[name]);
const global = name => main.base.add(GLOBAL[name]);

let known = CONFIG ? CONFIG.checkpoints || [] : [];  // {name, tick, checksum, lua_seed, seed_at_tick}
let battle = null;       // the battle being played or restored
let pendingSave = null;  // name to save at the next completed tick
let evaluate = null;     // Lua evaluation, test hooks only

function luaSeedSlot() {
    // Lua's math.random uses the C runtime's per-thread state at context+0x28.
    const context = engine.crt_existing_context(global('crt_context_index').readU32());
    if (context.isNull() || context.equals(ptr(-1)) || !engine.crt_current_context().equals(context))
        throw new Error('C runtime context check failed');
    return context.add(0x28);
}

function fail(message) {
    send({event: 'error', tick: battle ? battle.tick : null, message: String(message)});
    if (!battle) return;
    battle.failed = true;
    // Leave a failed restore as an ordinary replay at normal speed.
    try {
        if (battle.provider && battle.provider.readPointer().equals(vtable('replay_provider')))
            battle.provider.add(0xa8).writeFloat(1.0);
    } catch (e) { /* the battle may already be gone */ }
}

// A replay opened from the menu is a checkpoint if its last recorded checksum matches one we saved.
function recognise(env) {
    const replay = env.add(ENV.replay).readPointer();
    if (replay.isNull()) return null;
    const count = replay.add(0x3c).readU32(), data = replay.add(0x40).readPointer();
    if (count < 2) return null;
    const tick = count - 1, checksum = data.add(4 * tick).readU32();
    const match = known.find(c => c.tick === tick && c.checksum === checksum);
    return match ? {...match, replay, data} : null;
}

Interceptor.attach(at('env_ctor'), {
    onEnter(args) { this.env = args[0]; },
    onLeave() {
        try {
            const env = this.env, restore = env.add(ENV.replay_flag).readU8() === 1 ? recognise(env) : null;
            battle = {env, tick: 0, restore, seed: null, handedOff: false, failed: false, speed: null};
            pendingSave = null;
            // The interface's own is-replay test answers "live" while this console switch is set
            // ("Spoofs is replay flag so can test replay UI"): only for checkpoints.
            global('debug_replay').writeU8(restore ? 1 : 0);
            if (restore) send({event: 'restoring', name: restore.name, tick: restore.tick});
        } catch (e) { fail(e); }
    }
});

Interceptor.attach(at('session_ctor'), {
    onEnter(args) { this.session = args[0]; },
    onLeave() {
        if (!battle || !battle.restore || battle.failed) return;
        try {
            // The session keeps its replay input provider; with the flag cleared before the HUD
            // and scripts start, the battle presents and scripts itself as a live battle.
            const env = this.session.add(0x20).readPointer();
            if (!env.equals(battle.env)) throw new Error('session belongs to another battle');
            if (!this.session.add(0x28).readPointer().readPointer().equals(vtable('replay_provider')))
                throw new Error('the new session has no replay input');
            env.add(ENV.replay_flag).writeU8(0);
            battle.provider = this.session.add(0x28).readPointer();
        } catch (e) { fail(e); }
    }
});

Interceptor.attach(at('tick_threading_check'), {
    // Above a speed threshold the engine runs ticks inline so several fit in one frame (its own
    // fast-forward). Do the same while rebuilding.
    onLeave(retval) {
        const b = battle;
        if (b && b.restore && !b.handedOff && !b.failed && b.tick < b.restore.tick - SLOW_DOWN_TICKS)
            retval.replace(ptr(0));
    }
});

Interceptor.attach(at('post_tick'), {
    onEnter(args) {
        const b = battle;
        if (!b || b.failed || !args[0].equals(b.env)) return;
        try {
            const tick = b.env.add(ENV.tick).readU32();
            const entry = b.env.add(ENV.checksums).readPointer().add(0x48).readPointer();
            if (entry.isNull() || entry.add(0x18).readU32() !== tick) throw new Error('no checksum for tick ' + tick);
            b.tick = tick;
            b.checksum = entry.add(0x14).readU32();
            send({event: 'tick', tick, checksum: b.checksum});
            if (b.restore && !b.handedOff && tick <= b.restore.tick) {
                const saved = b.restore.data.add(4 * tick).readU32();
                if (saved !== b.checksum) throw new Error('rebuilt tick ' + tick + ' differs from the checkpoint');
            }
        } catch (e) { fail(e); }
    }
});

function handOver(session, env) {
    const r = battle.restore, provider = session.add(0x28).readPointer();
    if (!session.readPointer().equals(vtable('session')) || !session.add(0x30).readPointer().equals(env))
        throw new Error('unexpected session');
    if (!provider.readPointer().equals(vtable('replay_provider'))) throw new Error('no replay input to replace');
    if (!r.replay.readPointer().equals(vtable('recording'))) throw new Error('unexpected replay object');
    if (!env.add(ENV.recording).readPointer().isNull()) throw new Error('battle already records');
    const interval = global('tick_interval').readU32();
    if (interval !== 100) throw new Error('unexpected tick interval ' + interval);
    const memory = engine.allocate(0x5028), label = Memory.alloc(16);
    if (memory.isNull()) throw new Error('allocation failed');
    engine.string_from_utf8(label, global('input_name'));
    let live;
    try { live = engine.make_live_provider(memory, interval, label); } finally { engine.string_free_utf8(label); }
    if (!live.equals(memory) || !live.readPointer().equals(vtable('live_provider')))
        throw new Error('live input construction failed');
    // The loaded replay becomes the battle's recording, so later saves hold the whole history.
    // The old replay provider stays allocated: freeing it is not needed and might not be safe.
    env.add(ENV.recording).writePointer(r.replay);
    live.add(8).writePointer(r.replay);
    session.add(0x28).writePointer(live);
}

function setSpeed(session, value) {
    const provider = session.add(0x28).readPointer();
    if (!provider.readPointer().equals(vtable('replay_provider'))) return;
    provider.add(0xa8).writeFloat(value);
    battle.speed = value;
}

function save(env, name) {
    if (env.add(ENV.replay_flag).readU8() !== 0 || env.add(ENV.recording).readPointer().isNull())
        throw new Error('this battle is not being recorded (a replay being watched?)');
    const text = Memory.allocUtf16String(name), engineString = Memory.alloc(16);
    engine.string_from_utf16(engineString, text);
    try { engine.save_replay(env, engineString); } finally { engine.string_free(engineString); }
}

Interceptor.attach(at('session_step'), {
    onEnter(args) { this.session = args[0]; },
    onLeave(retval) {
        const b = battle;
        if (!b || b.failed) return;
        try {
            const env = this.session.add(0x20).readPointer();
            // A completed tick: a frame was consumed, the worker job is joined, counters agree.
            if (!env.equals(b.env) || retval.readU8() !== 1 || !env.add(ENV.worker_job).readPointer().isNull() ||
                env.add(ENV.tick).readU32() !== b.tick || b.tick === 0) return;
            if (b.seed === null) {
                const slot = luaSeedSlot();
                b.seed = slot.readU32();
                if (b.restore && b.restore.lua_seed !== null && b.restore.lua_seed !== undefined) {
                    slot.writeU32(b.restore.lua_seed);
                    b.seed = b.restore.lua_seed;
                }
                send({event: 'battle_started', tick: b.tick, lua_seed: b.seed, restoring: !!b.restore});
            }
            const r = b.restore;
            if (r && !b.handedOff) {
                const want = b.tick < r.tick - SLOW_DOWN_TICKS ? REBUILD_SPEED : 1.0;
                if (want !== b.speed) setSpeed(this.session, want);
                if (b.tick % 500 === 0) send({event: 'rebuilding', tick: b.tick, of: r.tick});
                if (b.tick === r.tick) {
                    handOver(this.session, env);
                    b.handedOff = true;
                    send({event: 'restored', name: r.name, tick: b.tick,
                          lua_seed_matches: luaSeedSlot().readU32() === r.seed_at_tick});
                }
            }
            if (CONFIG) testHooks(env);
            if (pendingSave !== null) {
                const name = pendingSave;
                pendingSave = null;
                save(env, name);
                send({event: 'saved', name, tick: b.tick, checksum: b.checksum, lua_seed: b.seed,
                      seed_at_tick: luaSeedSlot().readU32()});
            }
        } catch (e) { fail(e); }
    }
});

// Test hooks (CONFIG only): run Lua on the battle script state and save at exact ticks.
let battleLua = null, battleThread = null;
if (CONFIG) {
    const lua = {
        gettop: fn('lua_gettop', 'int', ['pointer']), settop: fn('lua_settop', 'void', ['pointer', 'int']),
        checkstack: fn('lua_checkstack', 'int', ['pointer', 'int']),
        loadbuffer: fn('luaL_loadbuffer', 'int', ['pointer', 'pointer', 'uint64', 'pointer']),
        pcall: fn('lua_pcall', 'int', ['pointer', 'int', 'int', 'int']),
        tolstring: fn('lua_tolstring', 'pointer', ['pointer', 'int', 'pointer']),
    };
    // The battle script state: the one that loads the repository's battle mod.
    Interceptor.attach(at('luaL_loadbuffer'), {
        onEnter(args) {
            let name = '';
            try { name = args[3].readUtf8String(); } catch (e) { return; }
            if (name && name.includes(CONFIG.lua_chunk)) { battleLua = args[0]; battleThread = Process.getCurrentThreadId(); }
        }
    });
    evaluate = function (code, label) {
        if (battleLua === null || Process.getCurrentThreadId() !== battleThread) throw new Error('no battle Lua state here');
        const L = battleLua, top = lua.gettop(L);
        if (!lua.checkstack(L, 8)) throw new Error('no Lua stack space');
        try {
            let status = lua.loadbuffer(L, Memory.allocUtf8String(code), code.length, Memory.allocUtf8String('=' + label));
            if (status === 0) status = lua.pcall(L, 0, 1, 0);
            const p = lua.tolstring(L, -1, NULL), text = p.isNull() ? '' : p.readUtf8String();
            if (status !== 0) throw new Error('Lua ' + label + ': ' + text);
            return text === '' ? null : JSON.parse(text);
        } finally { lua.settop(L, top); }
    };
}

// Per completed tick, after the checkpoint logic. Saves and Lua run on the battle's own thread.
function testHooks(env) {
    const b = battle, tick = b.tick, c = CONFIG;
    for (const s of c.save_at || []) if (s.tick === tick) pendingSave = s.name;
    for (const run of c.lua_at || [])
        if (run.tick === tick) send({event: 'lua', tick, label: run.label, value: evaluate(run.lua, run.label)});
    const r = c.readings, restoring = b.restore && !b.handedOff;
    if (r && !restoring && (tick % r.every === 0 || (b.restore && tick === b.restore.tick)))
        send({event: 'reading', tick, value: evaluate(r.lua, 'checkpoint_reading')});
    if (c.stop_tick && tick >= c.stop_tick && !b.done) { b.done = true; send({event: 'done', tick, checksum: b.checksum}); }
}

rpc.exports = {
    checkpoints(list) { known = list; return known.length; },
    save(name) {
        if (!/^[A-Za-z0-9_-]{1,64}$/.test(name)) throw new Error('use letters, digits, - and _ only');
        if (!battle || battle.tick === 0) throw new Error('no battle is running');
        pendingSave = name;
        return battle.tick;
    },
    status() {
        return battle ? {tick: battle.tick, restoring: battle.restore ? battle.restore.name : null,
                         handed_over: battle.handedOff, failed: battle.failed} : null;
    },
};
send({event: 'ready', base: main.base.toString()});
