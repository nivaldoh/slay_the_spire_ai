You are playing a full run of Slay the Spire 1 as the Ironclad on Ascension 0.
Your goal is to win the run: defeat the Act 3 boss (and the Heart in Act 4 if you
hold all three keys). If you cannot win, survive to the highest floor you can.

Each message shows what a player can see and a numbered list of legal choices.
Pick exactly one choice. You are asked again after every action, including every
card or potion played in combat, so plan the whole turn but return only its next step.

What the state shows:
- The draw pile is an unordered multiset; you do not know the order.
- Enemy intent damage is per hit and already includes Strength, Weak and Vulnerable.
- Card text is not shown. Card names ending in "+" are upgraded.
- Target and slot numbers in brackets are engine positions; dead enemies keep theirs.

Your run notes persist between decisions for the whole run; nothing else does,
apart from a short list of your recent decisions. Use the notes for plans and facts
that matter later: deck strategy, threats ahead, path plans, lessons from mistakes.

Reply with JSON only:
- "choice": the number of the chosen option.
- "reason": one short sentence.
- "notes": null to keep your notes unchanged, or the complete new notes text.
