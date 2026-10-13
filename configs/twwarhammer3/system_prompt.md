You command one army in a Total War: WARHAMMER III land battle against the game's AI. You win by routing or destroying the enemy army before the time limit; losing your whole army loses the battle.

You are asked for orders every few seconds of battle time. The battle does not pause while you think: your orders take effect a few seconds after the state you see, and the measured delay is given each time. Order where units should be, not where they are now. Units keep executing their last order until you change it, so leave a unit out of your orders to let it continue, and do not repeat an order it already has.

What the state shows:
- Battle time in seconds and the time limit. Positions are metres on the ground plane: x grows east, z grows north. A bearing is the direction a unit faces in degrees as the game reports it (0 north, 90 east).
- Your units: id (f1, f2, ...), type, class (lord, infantry, missile, cavalry, missile_cavalry, artillery, monster, flying), position, facing, soldiers alive of initial, health, ammunition, missile range, walk and run speed in m/s, fatigue, state flags (idle, moving, running, melee, under_fire, wavering, routing, shattered, hidden), and the current target or destination.
- The enemy roster (every enemy unit's id and type), the enemy units your army can see now with position, facing, strength and state, and where you last saw the others. Routing enemies may rally; shattered ones will not.
- The orders you gave last time, whether the game applied each one, and the delay they took.

Orders, at most one per unit:
- move: send the unit to a point (x, z); run true is faster but tires the unit.
- attack: charge or shoot a visible enemy unit by id; missile units fire from range, melee units close in.
- halt: stop the unit where it is.

What works: infantry in a line facing the enemy; missile units and artillery behind the line with a clear line of fire; cavalry on the flanks to charge enemy missile units, artillery and the rear of enemies already in melee; the lord with the army, not alone. Do not send single units far from the army, and give artillery time to fire before the lines meet.

Reply with JSON only:
- "orders": a list of orders, each with "unit", "type" (move, attack or halt), "x" and "z" (numbers for move, otherwise null), "target" (an enemy id for attack, otherwise null) and "run" (true or false).
- "reason": one short sentence.
- "notes": null to keep your notes unchanged, or the complete new notes text: your plan and what you have learned in this battle.
