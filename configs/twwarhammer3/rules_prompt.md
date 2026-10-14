You command one army in a Total War: WARHAMMER III battle against the game's AI. Achieve the objective stated in the Battle section. In a plain land battle, rout or destroy the enemy army; the state states which side wins if time expires. Choose your own strategy for the forces, terrain and objectives you observe.

The battle runs unpaused at 1x while you think. You receive another decision after the preceding batch is acknowledged, subject to any declared pacing. A snapshot may also have an explicitly added age. The prompt gives the measured delay between the snapshot and the previous orders being issued. Positions may have changed when new orders reach the game.

Information:
- Coordinates are metres: x increases east, z increases north. Facing is degrees: 0 north, 90 east. Battle time and the remaining time are shown.
- Friendly units show type/class, position, facing, men and health, ammunition/range, walk/run speed, fatigue, state flags, current targets, destinations, formation width, behaviour toggles and active abilities. Changes in men and health compare with the previous decision. A coarse terrain grid samples clear squares; it is not a complete pathfinding map, can miss narrow routes and can become stale when buildings change.
- The initial enemy roster is public. Later enemy arrivals become known on sight. Enemy unit state is shown only while visible; last-seen entries are memory, not current locations. A destruction flag records an observed death. Routing units may rally; shattered units will not.
- Visible units show walk/run speeds and flight capability; flying units also show whether they are airborne or on the ground. These are capabilities, not a measurement of their current velocity.
- The Battle section gives the game mode, role, timeout winner and objective text. Relevant modes expose capture points, tickets, gates, supplies, building slots, reinforcement pools and spawn zones. Capture points may be locked or contested. In free-for-all, other enemy alliances also fight each other.
- Winds of Magic pool/reserve and ability costs are army resources. Ability cast range, effect radius, duration, readiness, remaining uses, active/recharge state and last issue times are shown when available. Readiness may change before an order arrives. A unit's barrier is shown separately from its health as current/maximum barrier HP.
- Orders persist until replaced, completed or interrupted by the game. An attack can lapse when its target dies or leaves sight, or its unit routs. Omitted units keep their current orders. "Game's choice" identifies a target the game selected; "stopped short" identifies a move it dropped. Infer current execution from observed position, target and state.

Order contract:
- Give at most one immediate move/attack/halt per unit in a reply. Behaviour changes and an ability can accompany it. Orders are processed in list order. Empty orders are permitted.
- move: unit, type, x, z, facing (degrees or null), width (metres or null), run (boolean), queue (boolean). Null facing/width preserves the corresponding setting. An unreachable destination is rejected; nearby tested alternatives may be shown for you to choose. No alternative is applied automatically.
- attack: unit, type, target (visible enemy id), mode ("auto", "melee" or "ranged"), run, queue. Auto uses the unit's primary attack; melee closes to fight even if it has ammunition; ranged requires ammunition. An attack replaces movement and may move the unit into range.
- queue: true is allowed only for moves/attacks following a move for that unit in this reply. An attack must end its sequence. A rejected earlier move also rejects its queued successors. A new immediate order replaces the old sequence. Acceptance of queued orders does not establish their completion.
- halt: unit and type only; cancels the current sequence.
- behaviour: unit, type, behaviour (a key shown for that unit), enabled (boolean). "defend" is guard mode; other supported keys include fire_at_will, skirmish, change_formation_spacing and formed_attack.
- ability: unit, type, ability (an owned ready key), target, x, z, facing, width. For Self/Around self, all target/position fields are null. For Ally/Enemy, give the permitted unit id as target and leave x/z null. For Ground, give x/z and leave target null; facing/width can specify direction/spread. Use unit "army" for a shown army ability. Abilities cannot be queued. The engine enforces remaining conditions; issued does not guarantee it fired.
- build: unit "army", type, slot (shown slot id), option (shown option name). It consumes supplies and takes construction time; built towers act automatically.
- reinforce: unit "army", type, reinforcement (a unit type from the shown pool), zone (an available spawn-zone id). It consumes supplies. New arrivals get friendly ids; a returning purchased unit can retain its old id. A zone may refuse a purchase.
- run true is faster and causes fatigue; false walks. Formation movement and ordinary unit combat/fire behaviour remain handled by the game.

Acknowledgements identify order indexes and report validation or engine refusals. They establish that an order was issued or queued, not that its intended effect occurred. Use subsequent observations to assess effects and revise your plan. Hidden scoring state and setup/debug controls are unavailable.

Reply with JSON only, following the supplied schema:
- "orders": the order list, using only the fields for each command type.
- "reason": one short sentence explaining the decision.
- "notes": null to retain your notes, or the complete replacement notes text (at most 2000 characters). Notes persist within this battle only; record your plan, observations and revisions as useful.
