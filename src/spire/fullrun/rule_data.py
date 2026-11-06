"""Hand-written Ironclad knowledge for the rule policy in ``spire.fullrun.rules``.

Numbers are the public card text at Ascension 0. CommunicationMod reports a card's cost
and type but not its damage or block, so the policy has to carry them. Values are a play
aid, not a model of the game: the policy never predicts draws, and an error here costs
quality of play, never legality, because a choice always comes from the live candidates.

JUDGEMENT: Rule policy values — Claude, 2026-11-06, unattended: the card ratings and relic
order below are my own estimates of Ironclad at Ascension 0, written without an owner
direction. Other ratings would make a different teacher; any use as a teacher or baseline
rests on them.
"""

from __future__ import annotations

# id: (damage per hit, hits, block). Upgraded values are (damage, block) added per upgrade.
ATTACKS = {
    "Strike_R": (6, 1), "Bash": (8, 1), "Anger": (6, 1), "Body Slam": (0, 1), "Clash": (14, 1),
    "Cleave": (8, 1), "Clothesline": (12, 1), "Headbutt": (9, 1), "Heavy Blade": (14, 1),
    "Iron Wave": (5, 1), "Perfected Strike": (6, 1), "Pommel Strike": (9, 1),
    "Sword Boomerang": (3, 3), "Thunderclap": (4, 1), "Twin Strike": (5, 2), "Wild Strike": (12, 1),
    "Blood for Blood": (18, 1), "Carnage": (20, 1), "Dropkick": (5, 1), "Hemokinesis": (15, 1),
    "Pummel": (2, 4), "Rampage": (8, 1), "Reckless Charge": (7, 1), "Searing Blow": (12, 1),
    "Sever Soul": (16, 1), "Uppercut": (13, 1), "Whirlwind": (5, 1), "Bludgeon": (32, 1),
    "Feed": (10, 1), "Fiend Fire": (7, 1), "Immolate": (21, 1), "Reaper": (4, 1),
    "Dramatic Entrance": (8, 1), "Flash of Steel": (3, 1), "Mind Blast": (0, 1),
    "Swift Strike": (7, 1), "Trip": (0, 1), "Bite": (7, 1), "HandOfGreed": (20, 1),
}
BLOCKS = {
    "Defend_R": 5, "Armaments": 5, "Iron Wave": 5, "Shrug It Off": 8, "True Grit": 7,
    "Flame Barrier": 12, "Ghostly Armor": 10, "Power Through": 15, "Sentinel": 5, "Impervious": 30,
    "Good Instincts": 6, "Dark Shackles": 0, "Ghostly": 0,
}
# Values once upgraded, where the upgrade changes them. Checked against recorded engine results.
UPGRADED_ATTACKS = {
    "Strike_R": (9, 1), "Bash": (10, 1), "Anger": (8, 1), "Clash": (18, 1), "Cleave": (11, 1),
    "Clothesline": (14, 1), "Headbutt": (12, 1), "Iron Wave": (7, 1), "Pommel Strike": (10, 1),
    "Sword Boomerang": (3, 4), "Thunderclap": (7, 1), "Twin Strike": (7, 2), "Wild Strike": (17, 1),
    "Blood for Blood": (22, 1), "Carnage": (28, 1), "Dropkick": (8, 1), "Hemokinesis": (20, 1),
    "Pummel": (2, 5), "Reckless Charge": (10, 1), "Sever Soul": (22, 1), "Whirlwind": (8, 1),
    "Bludgeon": (42, 1), "Feed": (12, 1), "Fiend Fire": (10, 1), "Immolate": (28, 1), "Reaper": (5,
    1),
    "Dramatic Entrance": (12, 1), "Flash of Steel": (6, 1), "Swift Strike": (10, 1), "Bite": (8, 1),
    "HandOfGreed": (25, 1),
}
UPGRADED_BLOCKS = {
    "Defend_R": 8, "Iron Wave": 7, "Shrug It Off": 11, "True Grit": 9, "Flame Barrier": 16,
    "Ghostly Armor": 13, "Power Through": 20, "Sentinel": 8, "Impervious": 40, "Good Instincts": 9,
}
AREA = frozenset({"Cleave", "Thunderclap", "Whirlwind", "Immolate", "Reaper", "Dramatic Entrance"})
# Cards that apply Vulnerable, played before other attacks so those hit 50% harder.
VULNERABLE = frozenset({"Bash", "Thunderclap", "Uppercut", "Shockwave", "Trip"})
WEAK = frozenset({"Clothesline", "Uppercut", "Shockwave", "Intimidate", "Blind"})
# Played early in a fight when the turn is not dangerous, because they pay back every turn.
POWERS_FIRST = frozenset({
    "Inflame", "Metallicize", "Feel No Pain", "Dark Embrace", "Demon Form", "Barricade",
    "Corruption", "Evolve", "Fire Breathing", "Juggernaut", "Rupture", "Combust", "Berserk",
    "Brutality", "Panache", "Sadistic Nature", "Mayhem", "Magnetism",
})
# Cards the policy leaves in hand: their cost outweighs a plain turn.
SITUATIONAL = frozenset({"Dual Wield", "Exhume", "Forethought", "Havoc", "Second Wind"})
FREE_ENERGY = frozenset({"Bloodletting", "Seeing Red", "Offering", "Adrenaline", "Flex"})
DRAW = frozenset({"Battle Trance", "Pommel Strike", "Shrug It Off", "Warcry", "Burning Pact",
                  "Master of Strategy", "Deep Breath", "Finesse", "Flash of Steel"})
BAD_CARDS = frozenset({"AscendersBane", "Clumsy", "CurseOfTheBell", "Decay", "Doubt", "Injury",
                       "Necronomicurse", "Normality", "Pain", "Parasite", "Pride", "Regret",
                       "Shame", "Writhe", "Burn", "Dazed", "Slimed", "Void", "Wound"})

# Worth of a card added to a typical Ironclad deck: 0 is skipped. Above about 6 is taken
# over most alternatives; between 1 and 3 only until the deck has enough of that role.
CARD_VALUE = {
    # Scaling and engines.
    "Demon Form": 9, "Limit Break": 7, "Inflame": 8, "Spot Weakness": 7, "Barricade": 6,
    "Corruption": 8, "Feel No Pain": 8, "Dark Embrace": 7, "Metallicize": 7, "Offering": 8,
    "Juggernaut": 5, "Evolve": 4, "Rupture": 3, "Fire Breathing": 3, "Combust": 4, "Brutality": 5,
    "Berserk": 4,
    # Strong attacks.
    "Feed": 8, "Reaper": 7, "Immolate": 8, "Bludgeon": 7, "Fiend Fire": 5, "Uppercut": 7,
    "Carnage": 7, "Hemokinesis": 6, "Blood for Blood": 6, "Dropkick": 6, "Pummel": 5, "Rampage": 5,
    "Whirlwind": 7, "Sever Soul": 5, "Searing Blow": 4, "Reckless Charge": 3,
    "Pommel Strike": 7, "Twin Strike": 4, "Cleave": 5, "Thunderclap": 6, "Headbutt": 5,
    "Clothesline": 5, "Iron Wave": 3, "Anger": 5, "Heavy Blade": 4, "Perfected Strike": 5,
    "Sword Boomerang": 3, "Wild Strike": 3, "Body Slam": 3, "Clash": 2,
    # Block and utility.
    "Shrug It Off": 7, "Flame Barrier": 7, "Impervious": 8, "Power Through": 6, "Ghostly Armor": 5,
    "True Grit": 5, "Armaments": 4, "Entrench": 3, "Rage": 3, "Sentinel": 3, "Second Wind": 3,
    "Disarm": 7, "Shockwave": 8, "Intimidate": 4, "Battle Trance": 7, "Seeing Red": 5,
    "Bloodletting": 5, "Burning Pact": 4, "Warcry": 2, "Flex": 2, "Infernal Blade": 3, "Exhume": 3,
    "Double Tap": 4, "Dual Wield": 2, "Havoc": 2,
    # Colorless.
    "Apotheosis": 9, "Ghostly": 9, "Master of Strategy": 7, "Panacea": 4, "Trip": 5, "Blind": 5,
    "Dark Shackles": 4, "Flash of Steel": 5, "Swift Strike": 3, "Dramatic Entrance": 4,
    "Good Instincts": 3, "Finesse": 3, "Deep Breath": 2, "Purity": 3, "Madness": 3, "Mind Blast": 3,
    "Bandage Up": 3, "Secret Weapon": 3, "Secret Technique": 3, "HandOfGreed": 6,
    "Thinking Ahead": 3,
    "Violence": 2, "Forethought": 2, "Enlightenment": 2, "Impatience": 2, "Jack Of All Trades": 1,
    "Panic Button": 3, "The Bomb": 4, "Transmutation": 2, "Metamorphosis": 2, "Chrysalis": 3,
}
# Most copies worth holding, by the kind of card; unlisted cards allow two.
MAX_COPIES = {
    "Demon Form": 1, "Barricade": 1, "Corruption": 1, "Feel No Pain": 2, "Dark Embrace": 2,
    "Limit Break": 1, "Juggernaut": 1, "Evolve": 1, "Rupture": 1, "Fire Breathing": 1, "Combust": 1,
    "Brutality": 1, "Berserk": 1, "Inflame": 2, "Metallicize": 2, "Offering": 1, "Impervious": 2,
    "Shrug It Off": 3, "Pommel Strike": 3, "Rage": 1, "Entrench": 1, "Double Tap": 1,
    "Dual Wield": 1,
    "Exhume": 1, "Clash": 1, "Warcry": 1, "Flex": 1, "Havoc": 1, "Body Slam": 1, "Sentinel": 1,
}
UPGRADE_VALUE = {
    "Bash": 7, "Offering": 9, "Limit Break": 9, "Whirlwind": 8, "Feed": 7, "Immolate": 7,
    "Shockwave": 8,
    "Demon Form": 8, "Uppercut": 8, "Armaments": 6, "Burning Pact": 5, "True Grit": 6,
    "Flame Barrier": 6,
    "Shrug It Off": 6, "Pommel Strike": 6, "Inflame": 6, "Metallicize": 6, "Feel No Pain": 7,
    "Dark Embrace": 6, "Body Slam": 5, "Disarm": 6, "Battle Trance": 6, "Thunderclap": 5,
    "Twin Strike": 4,
    "Anger": 4, "Perfected Strike": 5, "Searing Blow": 8, "Impervious": 6, "Spot Weakness": 6,
    "Strike_R": 1, "Defend_R": 1,
}
# Best first; unlisted boss relics rank below every listed one.
BOSS_RELICS = [
    "Philosopher's Stone", "Sozu", "Runic Pyramid", "Snecko Eye", "Empty Cage", "Black Star",
    "Astrolabe", "Calling Bell", "Pandora's Box", "Black Blood", "Slaver's Collar", "Runic Dome",
    "Sacred Bark", "Velvet Choker", "Mark of Pain", "Coffee Dripper", "Fusion Hammer", "Ectoplasm",
    "Busted Crown", "Tiny House",
]
BAD_POTION_NOW = frozenset({"Potion Slot", "FairyPotion", "SmokeBomb", "ElixirPotion",
"EntropicBrew"})
# Potions that spend a whole slot well only in a fight that can kill the run.
ATTACK_POTIONS = frozenset({"Fire Potion", "Explosive Potion", "AttackPotion", "SteroidPotion",
                            "Strength Potion", "CultistPotion", "Fear Potion", "FearPotion",
                            "Weak Potion", "Energy Potion", "Swift Potion", "SpeedPotion",
                            "DuplicationPotion", "DistilledChaos", "ColorlessPotion", "SkillPotion",
                            "PowerPotion", "HeartOfIron", "GamblersBrew", "LiquidMemories",
                            "LiquidBronze", "EssenceOfSteel", "Ancient Potion", "Dexterity Potion",
                            "BlessingOfTheForge", "Regen Potion", "SneckoOil", "Ambrosia"})
DEFENCE_POTIONS = frozenset({"Block Potion", "BloodPotion", "Fruit Juice", "Regen Potion",
                             "LiquidBronze", "EssenceOfSteel", "HeartOfIron", "Dexterity Potion",
                             "Ghost In A Jar", "GhostInAJar"})
