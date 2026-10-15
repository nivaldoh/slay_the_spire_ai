# WH3 benchmark report: redesign brief for Codex

## 1. The product we want

Make the report a compelling way to **watch an AI command an army, understand its consequential decisions, and compare its performance with other models or configurations**.

The primary reader is an AI researcher arriving from a social-media post. They may know nothing about Total War. They should understand the challenge and see an interesting maneuver almost immediately. They should also be able to check an interpretation without reading an engineering log.

The organizing sequence is:

**Watch the battle → understand the decisions → compare the results.**

This is not a request for a general-purpose analytics platform, a new simulator, or a prescribed agent architecture. Keep the existing battle visualizer central. Keep useful records underneath; stop making readers navigate the experiment bookkeeping to reach the interesting part.

### Basis and boundaries

This brief follows inspection of the supplied `visual-report.html`, including its rendered interface, embedded records, and replay data. It does **not** follow inspection of the repository that generated it. The current repository may already have changed. Verify available fields and behavior before committing to changes.

Treat the earlier latency-benchmark brief as background, not an obligation to keep every metric or preserve its page structure. Model behavior, tactical competence, context changes, and performance under increasing control demands are now central; latency is one important explanatory dimension.

Separate changes achievable from existing records from changes requiring new instrumentation or experiments. Do not invent missing results, reconstruct unrecorded events, or add placeholder charts for experiments that have not happened.

## 2. What is wrong with this particular report

The visual identity is not the main problem. The restrained paper-colored page and dark battle map can stay. The information hierarchy needs substantial change.

| Current element | Required direction |
|---|---|
| Large masthead, “Research series,” generic report title, decorative map | Make the header compact and lead with the tactical question. Keep the visual character, not the ceremonial space. |
| “Scope,” “Job wall time,” launched jobs, throughput | Remove from the public reading path. These concern operating the benchmark, not understanding model behavior. Retain in exported run data where useful. |
| Long featured-run identifier and sentence of counters | Show a readable model/configuration name, battle outcome, and duration. Other quantities belong where they answer a question. |
| Scenario selector exposing source revisions and unrun catalogue entries | Offer readable names for scenarios with results. Keep unrun development candidates out of the public report. |
| Full-size stills, capture failures, repeated briefings, and raw faction names before the replay | Remove the obstacle course. Put the interactive battle near the top; use imagery selectively. |
| JSON orders and acknowledgments filling the decision panel | Translate actual orders into concise tactical instructions with recognizable unit names. Keep raw records one action away. |
| Dense legend, resource tracks, unit-state lanes, and event feed all visible | Default to what explains the selected battle moment. Do not show every available dimension at once. |
| “Evidence & definitions,” provenance, hashes, setup records | Remove the entire section from the public page. Preserve relevant information in run settings, experiment documentation, and downloadable data. Do not replace it with another large accordion collection. |

The supplied snapshot has four recorded battle results: two model battles, both labeled `gpt-6-sol` with low reasoning in different source revisions, and two scripted baselines. It is **not yet a multi-model leaderboard**. The report should become more informative about the actual evidence, not imply broader coverage through layout or naming.

## 3. The page should have three main sections

### A. Watch a battle

Start with a plain-language tactical challenge. For the supplied scenario, a suitable direction is:

> **Can an AI get its cavalry past the defenders and reach the guns?**
>
> Six mounted units face eight enemy units, including four anti-cavalry infantry units protecting handgunners and a cannon. The attacker must defeat the defenders before the timer expires.

Use the scenario's real objective. Do not turn a designer's preferred tactic into the only acceptable solution.

Next, show the selected model/configuration, the observed result, and the replay. For example, the supplied featured battle can be described as a win in **6:22**, not “won · 382.0 s · active-strength margin 0.433 …”. Put “Single recorded battle” nearby rather than presenting 100% as an established success rate.

Keep the input conditions in one compact sentence or short line: text-based observations, battle continues during model calls, and the relevant enemy-visibility rule. Verify those statements for the selected run. The animation is a viewer's rendering of recorded state, not automatically the image the model received.

Provide a clear way to watch the featured maneuver, watch the full battle, and choose another recorded run. Do not force a large settings selection before anything useful appears.

### B. What happened

Connect a few consequential moments to the replay: an opening plan, a successful maneuver, a mistake or recovery when supported, and the outcome. These can sit beside the map or immediately beneath it; they do not require another major interface.

The main explanatory unit is a **battle moment**, not a request number or log entry.

### C. Compare results

Below the replay, show a compact comparison of genuinely comparable runs. Add an experiment-specific chart only when there are sufficient relevant observations.

Use small footer links such as **Run settings**, **Data**, and **Code / methodology**. Exact prompts should also remain accessible from the decision they belong to. Readers should never need to open these to understand the main result.

## 4. Preserve the replay; make it easier to read

The current map is the strongest component. Improve its clarity rather than replacing it with a new rendering system.

Keep team colors, a stable orientation, time scrubbing, playback speed, and selecting a unit or decision. Make the battle and its controls usable on a phone without first scrolling through technical tables. Essential explanations cannot depend on hover alone.

The default display should show current unit positions, recognizable unit roles, and a small number of relevant movement trails. Orders, historical positions, and current observations must not compete as equally prominent marks.

When a unit or annotated maneuver is selected, emphasize that unit's route and relevant targets; fade unrelated detail. Distinguish **issued waypoints and targets** from **observed movement**. A line to an attack target is not evidence that the unit took that straight route. In particular, chained move orders should not look like several simultaneous instructions to cross the obstacle.

Keep spatial framing stable enough to follow a long flank. Repeated automatic rescaling can make movement difficult to judge. Optional focus on a moment is useful; constant cinematic camera motion is not required.

A selected decision currently has a before/after comparison available. Make that an explicit inspection action, not the default explanation readers must decipher on first arrival. Ordinary playback should look like ordinary playback. A pinned historical decision should be visibly pinned; otherwise, the displayed explanation and orders should follow the current replay time. Never show a future response as though it was already available while the request was pending.

Do not introduce inferred battle dynamics merely to smooth animation. Preserve meaningful recording gaps. Any later visual interpolation must be presentation-only, clearly distinguishable from recorded samples, and never bridge unknown intervals or drive metrics.

## 5. Make different units mean something

The current renderer assigns the same horse symbol to cavalry and missile cavalry. This hides an important distinction in this very example: **Mounted Yeomen Archers are not another interchangeable melee cavalry unit**.

Use a compact unit presentation that answers: **What is this unit, and why would I use it differently?**

Candidate labels for the supplied roster are below. These are proposed reader-facing descriptions, not an authoritative balance guide; verify them against the recorded unit identity and relevant game version before publishing.

| Unit | Candidate short explanation |
|---|---|
| Mounted lord | Army leader with combat abilities; one character, not a regiment of knights. |
| Knights of the Realm | Lance cavalry used for charges. Distinguish the two regiments as 1 and 2. |
| Questing Knights | Sword cavalry; emphasize the verified armor-piercing / sustained-melee distinction rather than labeling them just “cavalry.” |
| Grail Knights | Elite cavalry; explain the verified properties that matter in this matchup, not simply “better knights.” |
| Mounted Yeomen Archers | Fast mounted archers that can attack from a distance. |
| Halberdiers | Anti-cavalry infantry protecting the ranged units. Use the correct unit name, not a generic “pikemen” label. |
| Handgunners | Ranged infantry whose positioning and protection matter. |
| Great Cannons | Long-range artillery; a different target from the infantry screen. |

The source of truth for identities must be the recorded roster, not the order of entries in a scenario declaration. Remove internal suffixes such as “0” or “4” when they are asset identifiers, but retain meaningful variants and mounts.

On the map, prioritize a readable role glyph, team identity, facing, and stable short label. On selection, show the full name and a short explanation. Use the same name everywhere: map, orders, captions, and comparison examples. Group duplicates in a compact roster summary, while keeping individual regiments identifiable during play.

Expose only relevant status: health, fleeing or fighting, and context-specific ammunition or exhaustion. Do not place complete stat cards around every marker. A fleeing unit is not necessarily dead; soldiers remaining and health remaining are different quantities.

### Unit artwork

Real unit portraits or icons are worthwhile **as supplementary identity cues**, especially in the roster or selected-unit card. They do not replace role explanations: three different armored horse portraits still mean little to a newcomer.

Start with assets for the demonstrated roster rather than an exhaustive unit encyclopedia. Keep a sensible fallback. Confirm appropriate use and redistribution conditions before shipping game artwork. Do not make understanding the report depend on acquiring assets first.

## 6. Explain decisions without pretending to read minds

For a selected moment, use three distinct pieces:

**Model's explanation.** Show its actual recorded short reason, attributed as such. Preserve wording when quoting. Do not manufacture a more impressive rationale or describe an explanatory field as direct access to internal reasoning.

**Orders given.** Summarize the actual command sequence in ordinary language. For example: “Send the lance cavalry around the west side, then attack the handgunners.” Preserve consequential differences between units, queued steps, and changed targets. Do not paraphrase the reason and mistake it for a summary of the orders.

**What happened next.** Describe what subsequent observations support: units moved, the cannon began fleeing, an order was rejected, or the intended action was not observed. Let the reader jump to the relevant interval. Temporal sequence alone does not prove a particular order caused the outcome.

This supports valuable comparisons between what a model says, what it orders, and what the game does. Contradictions are often more informative than eloquent explanations. Anchor judgments to the observation actually supplied to that decision: the replay recorder may contain intermediate frames the model never received.

Do not demand longer rationales from agents just to improve presentation. That would change latency, token cost, and possibly behavior. First use existing reasons, notes, and actions.

### Treat waiting intelligently

The featured replay contains 92 decision records, including 46 with no new orders. Many accompanying reasons say to let the existing route or queued attacks continue. That is a useful inspection target, not automatically inactivity or failure.

Show “Keeping current orders” when that is what the record supports. Do not reward command volume or count every interval without a new command as neglect. Persistent orders and the game's normal unit behavior can continue during model calls.

Conversely, a model saying “the archers are withdrawing” does not establish that the withdrawal order was accepted or carried out. Failed and superseded orders should remain visible when relevant to that claim.

## 7. Curate a few tactical highlights, not every event

Add a small number of timestamped, human-reviewed annotations per featured battle. Start with manual curation; do not build an automated tactical analyst or add an LLM judge to the reporting pipeline.

Each highlight should have a short title, one sentence explaining why it matters, the relevant units, and a jump into the replay with enough lead-in to see the situation develop. Not every battle needs both a triumph and a failure; do not manufacture balance.

The supplied replay already provides candidate material:

- **The long approach:** the opening reason explicitly describes going west around the obstruction to attack the ranged units. Show how the subsequent route develops, not just the opening arrows.
- **The ranged defense starts fleeing:** the records mark the cannon routing at about 3:27 and both handgunner units routing at about 3:46. Inspect the surrounding action before writing a causal caption.
- **Execution trouble:** mounted-archer movement orders are rejected as unreachable around 4:12 and 4:27. Inspect what information and feedback were available and how the model responds. Do not automatically attribute every rejection to poor reasoning.

These are inspection candidates from this snapshot, not finished claims about model capability.

Manual annotations must be distinguishable from the model's words. A compact “Analyst note” label is enough. Keep their backing timestamps and record references internally, not printed as filenames beneath every sentence.

Feature selection can favor an instructive battle or maneuver. Label it “Selected example” and retain access to all runs. Aggregate results must not be computed from the showcase selection. A highlight does not need to pretend to be statistically representative.

## 8. Make latency concrete

Replace abstract timing jargon with a direct question:

> **How old was the battlefield information when the new orders were issued?**

For a selected decision, show the actual sequence, using meaningful endpoints:

**Observed battlefield → requested a decision → received a reply → issued / acknowledged orders.**

Use the endpoint the instrumentation really measures. “Acknowledged” is not proof of a completed charge, a successful spell, or even immediate movement. Queued attacks may intentionally happen much later.

A reader-facing explanation can be: “These orders used a view of the battlefield from 4.2 seconds earlier.” This is a format example; populate it from the selected record and correct population.

The best accompanying visual is not another large chart. Offer a focused before/after view for the selected decision: where a relevant target was in the observation and where it was next recorded around command issuance. Use a label such as “While the response was being generated…” rather than claiming that the interval measures pure reasoning. Do not animate a made-up exact path between sparse observations.

### Keep the timing quantities separate

API response duration is a wall-clock measurement. Observation age at order issuance may be measured in battle time and include preexisting staleness. Artificially aging a snapshot is not the same intervention as delaying the model's response. Report playback speed is neither game speed nor model latency.

Choose one consistent end-to-end age definition for the primary comparison. Use a median as the default summary; a slow-response percentile can be available in detail when useful. Do not mix populations or calculate pooled summaries by silently combining incompatible runs.

The current featured data illustrates why this needs attention: its replay summary has a median age of 3.9 seconds across 91 decision records, while the result metrics have a median order age of 4.2 seconds across 45 nonempty batches. The API-call median is about 3.42 seconds. These are different quantities and populations, not interchangeable versions of one number. Verify the underlying boundaries and choose clear labels rather than averaging away the discrepancy.

Move “provider,” “call minus provider,” and “roundtrip minus think” to technical detail. Never relabel a residual as precisely measured network time. Measure response-to-visible-effect separately only when justified; do not add a speculative “reaction time” metric.

Latency should help explain a battle. A long response is not automatically harmful; a short response is not automatically tactically sound. To claim delay caused a failure, conduct a controlled comparison rather than relying only on a dramatic replay moment.

## 9. Compare models and configurations, not just run labels

Provide a compact results table answering: **Under the same conditions, who wins, how delayed are their orders, and what does it cost?**

A suitable default is:

| Model / setup | Battles won | Typical order delay | Inference cost / battle | Replay |
|---|---|---|---|---|
| Readable name and meaningful variant | Counts with denominator | Clearly defined median age | Recorded value, sensible precision | Watch |

Use wins out of trials for small samples. Do not make “100%” the headline of a single victory. Show uncertainty when the experiment supports it, with statistical details available away from the main page. Do not treat repeated decisions, correlated rematches, or screenshots as additional independent battles.

Retain actual engine outcomes and termination reasons. A timeout can be a win or loss under the scenario rules. Do not silently redefine it as a non-win merely to simplify the table. If a separate objective requires victory before timeout, name that objective explicitly. An interruption is not a tactical loss; failed runs must not disappear from the denominator without a visible explanation.

One model under changed prompting, memory, reasoning settings, tools, or controller code is a **configuration comparison**. Use descriptive names such as “Compact observations” and “Full observations”; show what differs in one sentence. Do not rename two revisions of the same model as different models or attribute every change in results to model intelligence.

Comparable model rows should share the intended scenario distribution and declared control conditions. Different maps, attacker roles, enemy strength, action helpers, observation access, or material controller changes require explicit treatment. Source hashes can remain hidden while compatibility checks remain active. Do not merge the two supplied model runs merely because the scenario name matches, or keep all future comparisons fragmented solely for incidental recording changes without investigating compatibility.

### Compare behavior as well as outcomes

Let readers move from a result row to that run's replay and annotated moments. A selected model-versus-model or configuration-versus-configuration view should explain the contrast in plain language, backed by what happened.

For now, switching the same replay viewer between two runs is enough. Side-by-side synchronized replay is optional later. If added, use the same map scale and distinguish alignment by elapsed battle time from alignment by an event such as first contact. Separate rollouts diverge; they are not the same evolving state with different decisions substituted.

Do not add radar charts, invented “tactical intelligence” scores, or a universal leaderboard assembled from unlike scenarios. Prefer a small number of reproducible measurements and inspectable examples.

## 10. Experiments the report should eventually explain

Do not build these pages before collecting the relevant data. Allow the report to present one focused experiment at a time rather than exposing a combinatorial filter panel.

### How does performance change with army size?

This is a high-priority extension. Show controllable unit count on the horizontal axis and an explicit task-success measure on the vertical axis, with model/configuration series and the available trial counts and uncertainty.

Count the units the agent actually controls, including characters consistently. A cavalry regiment containing many soldiers is still one commandable unit; do not describe every rendered soldier as a separately controlled agent.

Adding friendly units alone changes combat advantage. Increasing both armies changes command demands but also battlefield density and encounter difficulty. Preserve relative forces and composition as sensibly as possible, assess the difficulty of each size with the same reference controller, and explain remaining confounds. An unchanged map is not automatically an equally difficult battle when formations become larger.

Show measured response latency alongside scaling results when available. More units may increase observation size, response size, and execution delay. If these change together, describe the result as end-to-end degradation under larger armies, not proof of a pure reasoning-capacity limit. A stronger causal claim needs additional controlled experiments.

Useful diagnostic examples include units left without an effective task, broken coordination, repeated target switching, and missed responses to an observed threat. Do not convert these into headline scores until their detection is dependable and they correlate with something meaningful. “Time since last order” alone is not a neglect detector.

### What changes when the same model gets different context?

Compare a baseline with one deliberate change: compact versus verbose state, unit-role descriptions versus raw names, memory versus no memory, or different reasoning budgets. Start with one question and a few conditions.

Show the changed information or setting, task performance, and latency/cost consequences. Keep other conditions controlled as far as feasible. Viewer-side role explanations and analyst captions must not leak into the agent's input unless they are the explicit treatment.

### How much does delay matter?

Use controlled experiments that identify where delay is introduced. A plot of older observations should not be titled “API slowdown.” Natural latency differences across models are useful operational observations, not a clean causal experiment by themselves.

Use observed conditions only. Do not draw a smooth degradation curve from a single latency setting or mix unrelated battles into a supposed dose-response relationship.

## 11. Use Total War's tactical richness selectively

Emphasize situations where viewers can recognize a clever decision or costly mistake. Not every ingredient is exclusive to Total War; the goal is to use this game's combination well, not make unsupported uniqueness claims.

**Position and facing:** going around a defender, choosing an approach, getting behind a protected target, and coordinating arrival. The current cavalry scenario is already a good foundation.

**Different unit jobs:** mounted archers, charge-focused cavalry, melee specialists, artillery, and commanders should create visibly different decisions. The report should reveal whether the model uses those differences rather than treating the army as identical attack tokens.

**Morale and disengagement:** show when units flee, rally, or remain engaged despite a withdrawal order. These can explain why an apparently intact army stops fighting or why a model retargets after a rout. Do not infer the precise cause of a rout from proximity alone.

**Resources and special abilities:** where the evaluated roster actually makes them consequential, explain a limited-use ability, ammunition decision, fatigue tradeoff, flight change, or spell. No magic chart is needed simply because a global magic resource is present in the recorded state. No supplies panel is needed for a battle without a meaningful supplies decision.

**Persistence and coordination:** the interesting control problem is not clicking individual soldiers. It is managing persistent unit-level instructions while other units continue acting. Good restraint and timely intervention can both be competent behavior.

Only display mechanics actually supported by the run's units and records. Keep future caster, flying-unit, or larger-army scenarios out of the current results until evaluated.

## 12. Add spectacle only where it improves understanding

### A short real-game highlight: worthwhile, optional

A short, well-framed clip of the actual cavalry approach or impact could be more useful to a newcomer than several more tables. The tactical map explains geometry; real footage establishes what the abstract markers represent.

The supplied report already embeds game stills, but also exposes failed/skipped captures and gives imagery substantial space before the replay. Remove failed-capture placeholders from the public page. They belong in capture diagnostics.

Choose a clip that shows an observable event, not merely trees, distant banners, or a victory screen. Roughly 15–30 seconds is a reasonable starting target, not a hard requirement. Manual selection and capture are acceptable; do not build an automatic cinematic director.

Identify the actual run and moment. Keep the clip optional and lightweight enough that the report works without loading it. It should not play audio unexpectedly or require synchronized dual playback to be useful.

Distinguish spectator footage from model input. Do not present a separately reenacted battle as footage of the measured run. Capturing additional media must not silently alter the timing conditions of a comparison. Check capture overhead before relying on it during evaluation; do not assume deterministic replay capture is available.

### Things not to build for this redesign

No custom 3D renderer, complete game-asset browser, automatic highlight classifier, live multi-agent control room, narrated commentary system, or general experiment-management backend. No cosmetic gamification scores. No frontend migration justified only by aesthetics.

A few role icons, selected-unit trails, manually annotated moments, clear latency presentation, and useful comparison tables should deliver most of the value.

## 13. Keep rigor without putting it on every surface

Remove provenance hashes and operational accounting from the visible report, not from the underlying records. Keep enough data to inspect exact prompts, settings, timings, outcomes, and failures later, including for a paper.

Warnings that change the interpretation must remain local and plain: “One recorded battle,” “Different enemy strength,” “Run interrupted,” or “No observation recorded during this interval.” Do not bury these in a data export; do not repeat generic methodological warnings beside every component.

The current active-strength margin is based on unweighted soldier fractions and counts routing/shattered soldiers as lost. Remove it as a headline metric. Renaming it “army strength” or “tactical quality” would not fix the interpretation. Prefer the actual objective outcome, and use clearly labeled unit-level survival or health when it helps explain a moment.

Use readable precision: `6:22`, `4.2 s`, and `$0.63`, not excessive decimals. Unknown is not zero. Absent capabilities should usually produce no panel, not a screen full of unavailable values. A missing value that prevents a comparison does need a brief explanation.

## 14. Delivery order and acceptance

**First: subtract and reorganize.** Bring the replay to the front. Remove the unwanted sections and public bookkeeping. Use readable names, translate orders, show the real task and outcome, fix cavalry-role ambiguity, and make timing labels consistent. Preserve access to the original records.

**Second: explain.** Add a few reviewed highlights, selected-unit emphasis, and an explicit before/after latency inspection. Make results link back to inspectable runs. Add unit artwork or one real-game clip only where it improves this version.

**Later: run and present experiments.** Add army-size, context, and delay comparisons when actual data exists. Do not spend the first redesign building their infrastructure.

Validate the redesign against concrete reader tasks:

1. Without reading documentation, a newcomer can identify the two sides, the objective, and why the mounted archers differ from the knights.
2. Within the first screen or a small scroll, the reader can watch an interesting maneuver and jump to the full battle.
3. At a selected moment, the reader can distinguish the model's explanation, its actual orders, and the observed subsequent behavior without reading JSON.
4. The reader can understand how long information took to become an order, without mistaking acknowledgment for successful execution or playback speed for game speed.
5. A researcher can compare supported conditions, see small samples or mismatches, and inspect an apparent failure without traversing a provenance section.
6. The small dataset remains honestly small: no fabricated models, scores, confidence, annotations, or unrun experiment charts appear to fill space.

Before implementation, map this brief to the current repository. Identify what can be achieved with existing records, what needs a small addition, and what would require new game instrumentation or experimental runs. Implement the smallest coherent redesign rather than treating every optional idea as mandatory.

**The finished page should make someone say “I see what it tried, I see what worked or failed, and I know what I would compare next”—not “there is a lot of telemetry here.”**
