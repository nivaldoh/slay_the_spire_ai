export const meta = {
  name: 'wh3-version-review',
  description: 'Review each episode of a WH3 LLM battle job, propose one harness change from three angles, judge them',
  whenToUse: 'After a twwarhammer3 play job of the autoresearch loop. args: {job: "runs/twwarhammer3/battle/<job>", episodes: ["episode-0000", ...], history: "versions so far, the baseline, measured facts"}',
  phases: [{ title: 'Review' }, { title: 'Propose' }, { title: 'Judge' }],
}

// The autoresearch loop's review step (docs/twwarhammer3/README.md#the-loop): one reviewer
// per episode, three proposers (tactics prompt, state and memory, interface), three judges.
// The orchestrator reads the totals and implements the winning change.

const ROOT = '/home/niv/repos/slay_the_spire_ai'
const job = args.job
const episodes = args.episodes
const CONTEXT = `Repository ${ROOT}: an API language model (gpt-6-luna, low reasoning effort) commands one army in a real-time Total War: WARHAMMER III custom battle against the game AI, through a Lua mod. The scenario is fixed (docs/twwarhammer3/log.md describes it). Every ~10 s of battle time the model gets a text state (its units, visible enemies, last-seen enemies, timing, its notes and recent decisions) and replies with JSON orders: move (x, z, optional facing), attack (target id), halt; run true/false. The battle keeps running while it thinks (delay ~4 s, measured and shown).
Editable surface for improvements: configs/twwarhammer3/system_prompt.md (system prompt), src/twwarhammer3/battle/llm.py (rendering of the state, memory: notes, history, last seen), and if needed the observation the Lua mod publishes (src/twwarhammer3/mod/script/battle/mod/twwarhammer3_battle.lua) and the order types. The game's scripting docs are extracted in ${ROOT}/runs/twwarhammer3/vanilla/documentation/script/battle/*.html (unitcontroller methods, unit queries).
Evidence: ${ROOT}/${job}/episode-NNNN/trace.jsonl has one JSON per line with kind in battle|roster|observation|decision|ack|result; a decision record has behavior.prompt (the exact text the model saw), behavior.reason, behavior.notes, behavior.attempts[*].text (raw reply), orders, time_ms; an ack has latency.delay_ms and ack.results (engine verdicts). result.json has the outcome. Run "cd ${ROOT} && uv run python -m twwarhammer3 digest ${job}/episode-NNNN" for a one-line-per-decision summary (time, strengths us/seen, orders, delay, reason) and the final state.
History so far (read docs/twwarhammer3/log.md for details):\n${args.history || ''}\nREAD-ONLY: do not edit files, do not run "python -m twwarhammer3 play/launch/menu", do not touch /mnt/c (a game job is running).`

const REVIEW = {
  type: 'object',
  properties: {
    outcome: { type: 'string' },
    summary: { type: 'string', description: 'at most 150 words: how the battle went and why it was won or lost' },
    mistakes: { type: 'array', items: { type: 'object', properties: {
      time_s: { type: 'number' }, what: { type: 'string' }, evidence: { type: 'string' },
      cause: { type: 'string', description: 'why the model did it: missing information, misleading rendering, prompt guidance, delay, lack of an order type, or plain tactical error' },
      cost: { type: 'string' } }, required: ['time_s', 'what', 'evidence', 'cause', 'cost'] } },
    good: { type: 'array', items: { type: 'string' } },
    harness_issues: { type: 'array', items: { type: 'string' }, description: 'places where the state text, prompt or interface misled or limited the model' },
  },
  required: ['outcome', 'summary', 'mistakes', 'good', 'harness_issues'],
}

const PROPOSAL = {
  type: 'object',
  properties: {
    title: { type: 'string' },
    change: { type: 'string', description: 'exactly what to change, file by file, small enough for one version' },
    evidence: { type: 'string', description: 'which mistakes in which episodes it addresses, with times' },
    expected_effect: { type: 'string' },
    risks: { type: 'string' },
  },
  required: ['title', 'change', 'evidence', 'expected_effect', 'risks'],
}

const SCORE = {
  type: 'object',
  properties: {
    scores: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' }, impact: { type: 'number' }, evidence: { type: 'number' },
      simplicity: { type: 'number' }, generality: { type: 'number' }, comment: { type: 'string' } },
      required: ['title', 'impact', 'evidence', 'simplicity', 'generality', 'comment'] } },
    pick: { type: 'string' },
  },
  required: ['scores', 'pick'],
}

phase('Review')
const reviews = await parallel(episodes.map(ep => () => agent(`${CONTEXT}
Review ${job}/${ep} (outcome in result.json). Read the digest first, then the prompts and raw replies around the turning points (first contact, the first unit lost or routed, the decisive minute). Identify the model's concrete mistakes with battle times and evidence, what it did well, and where the harness (state text, prompt, order types, timing) misled or limited it. Be specific and evidence-based; no generic advice.`,
  { label: `review:${ep}`, phase: 'Review', schema: REVIEW }).then(r => r && ({ episode: ep, ...r }))))
const done = reviews.filter(Boolean)
log(`${done.length} reviews: ${done.map(r => r.episode + ' ' + r.outcome).join(', ')}`)

const ANGLES = [
  ['tactics', 'the system prompt\'s tactical guidance and how the model is told to think about this battle (formation, timing of commitment, using each unit type, protecting the lord, reacting to routs)'],
  ['information', 'the state rendering and memory: information the model lacked, misread or had to compute itself (distances, who fights whom, map bounds, unit roles/strengths, ammunition, threat) and how llm.py could show it compactly'],
  ['interface', 'the decision interface: order types and parameters (unitcontroller offers more: e.g. attack_location, change_formation/width, fire_at_will, withdraw, perform_special_ability), decision cadence and delay handling, reply format'],
]
phase('Propose')
const proposals = await parallel(ANGLES.map(([key, focus]) => () => agent(`${CONTEXT}
Episode reviews of ${job}:
${JSON.stringify(done, null, 1)}

Propose ONE change for the next harness version, focused on ${focus}. Weigh the version history: what changed between versions and how results moved, and the scripted baseline. It must address the mistakes that cost the most in these reviews, be small and lean (this codebase avoids bloat), and generalise beyond this one scenario. Read the current files before proposing so the change fits them. If you think the best change is outside your angle, still give the best one within it.`,
  { label: `propose:${key}`, phase: 'Propose', schema: PROPOSAL })))
const props = proposals.filter(Boolean)

phase('Judge')
const judges = await parallel([0, 1, 2].map(i => () => agent(`${CONTEXT}
Episode reviews:
${JSON.stringify(done.map(r => ({ episode: r.episode, outcome: r.outcome, summary: r.summary, mistakes: r.mistakes })), null, 1)}

Candidate changes for the next version (only one will be made):
${JSON.stringify(props, null, 1)}

Score each candidate 1-10 on impact (expected improvement in battle outcomes), evidence (how directly the reviews support it), simplicity (small, lean, low risk), generality (helps beyond this scenario). Judge ${i + 1} of 3: be independent and skeptical; check claims against the traces where cheap. Then pick the single best candidate by title.`,
  { label: `judge:${i + 1}`, phase: 'Judge', schema: SCORE })))
const valid = judges.filter(Boolean)
const totals = props.map(p => {
  const s = valid.flatMap(j => j.scores.filter(x => x.title === p.title))
  const mean = s.length ? s.reduce((a, x) => a + x.impact + x.evidence + x.simplicity + x.generality, 0) / s.length : 0
  return { title: p.title, mean, picks: valid.filter(j => j.pick === p.title).length }
})
return { reviews: done, proposals: props, totals, comments: valid.map(j => j.scores.map(x => `${x.title}: ${x.comment}`)) }
