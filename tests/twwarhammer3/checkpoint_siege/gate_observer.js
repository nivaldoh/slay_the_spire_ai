// Private diagnostic: build 25961564 gate-HP accessor resolves the same building piece
// used by the recorded CHANGE_GATE_STATUS command (0x142ecd9d4 -> 0x14316b348).
// Gate state 0 selects _gate_closed; other values select _gate_open. Keep the raw enum
// until its changes have been witnessed in game. HP is independently read through Lua.
BUILD.gate_hp = ['0x1be9e48', '488b41080f57c0488b88900000004885'];
const gatePieces = new Map();
let gateOpenSaved = false;
Interceptor.attach(at('gate_hp'), {
    onEnter(args) {
        try {
            const building = args[0].add(8).readPointer();
            if (building.isNull()) return;
            const piece = building.add(0x90).readPointer();
            if (piece.isNull() || piece.add(0xa8).readPointer().isNull()) return;
            gatePieces.set(piece.toString(), piece);
        } catch (e) { fail('gate observation: ' + e); }
    }
});
function gateStates() {
    const result = [];
    for (const piece of gatePieces.values()) {
        const visual = piece.add(0xa8).readPointer();
        const maximum = piece.add(0x88).readU32(), damage = piece.add(0x1b8).readFloat();
        result.push({
            x: (piece.add(0xb8).readFloat() + piece.add(0xc4).readFloat()) / 2,
            y: (piece.add(0xbc).readFloat() + piece.add(0xc8).readFloat()) / 2,
            z: (piece.add(0xc0).readFloat() + piece.add(0xcc).readFloat()) / 2,
            hp: maximum - damage, max_hp: maximum,
            enabled: visual.readU8(), state: visual.add(0x18).readU32(),
            change_started_s: visual.add(0x34).readFloat(),
        });
    }
    if (!battle.restore && !gateOpenSaved && result.some(g => g.hp > 0 && g.state !== 0)) {
        pendingSave = GATE_OPEN_NAME;
        gateOpenSaved = true;
    }
    return result.sort((a,b) => a.x-b.x || a.z-b.z || a.y-b.y);
}
