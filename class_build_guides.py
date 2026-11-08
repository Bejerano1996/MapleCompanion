"""Compact AP and SP reference for MapleStory Classic World.

Allocation facts summarized from NiaMeowDB's November 2026 guides.
Skill totals are cumulative milestones, not points to add at that level.
"""

GUIDE_ROOT = "https://meowdb.com/msclassic/guides/"
CLASS_ROOT = "https://meowdb.com/msclassic/classes/"

BUILDS = {
    "Warrior": {
        "family": "warrior",
        "ap": (
            "Start at 12 STR / 5 DEX / 4 INT / 4 LUK. Levels 2–10: +5 STR each.",
            "After Lv 10, put the 5 AP into STR except when you need DEX for your next weapon. Count DEX from gear you already wear.",
            "Total DEX examples: Viking Sword 15, Mithril Axe 20, Blue Axe 30. The Lv 30 Blue Axe example uses 27 base DEX plus 3 from gear.",
        ),
        "sp": (
            (10, "Power Strike 1"),
            (14, "Power Strike 4, Slash Blast 4, Precise Strikes 5"),
            (20, "Power Strike 20, Slash Blast 6"),
            (25, "Slash Blast 19, Precise Strikes 6, Improved HP Recovery 1"),
            (28, "Precise Strikes 15"),
            (30, "Improved HP Recovery 3, Max HP Increase 3, Iron Body 1"),
        ),
        "next": "Fighter / Page / Spearman",
    },
    "Magician": {
        "family": "magician",
        "ap": (
            "Start at 4 STR / 4 DEX / 12 INT / 5 LUK. Levels 2–19: +5 INT each.",
            "Sample wand route: +5 LUK at Lv 20, 25 and 30. Every other level gets +5 INT. Lv 30 target: 142 base INT / 20 base LUK.",
            "If equipped gear supplies LUK, add only the shortfall for your wand and put the remaining AP into INT.",
        ),
        "sp": (
            (10, "Energy Bolt 1"),
            (11, "Energy Bolt 3, Improved MP Recovery 1"),
            (17, "Energy Bolt 20, Magic Guard 1"),
            (19, "Magic Guard 3, Improved MP Recovery 3, Max MP Increase 2"),
            (26, "Magic Armor 20, Max MP Increase 3"),
            (30, "Max MP Increase 15"),
        ),
        "next": "Fire/Poison Wizard / Ice/Lightning Wizard / Cleric",
    },
    "Bowman": {
        "family": "bowman",
        "ap": (
            "Start at 5 STR / 12 DEX / 4 INT / 4 LUK. Levels 2–10: +5 DEX each.",
            "After Lv 10, add STR only to meet your next weapon’s total requirement, then put the rest of each level’s 5 AP into DEX.",
            "At Lv 30, Ryden needs 30 total STR and Eagle Crow needs 20 total STR. Both need 65 total DEX. Use the matching bow or crossbow AP table in the source.",
        ),
        "sp": (
            (10, "Arrow Blow 1"),
            (15, "Arrow Blow 13, Eye of Amazon 3"),
            (18, "Arrow Blow 20, Critical Shot 2"),
            (23, "Critical Shot 15, Eye of Amazon 5"),
            (27, "Eye of Amazon 15, Focus 2"),
            (30, "Focus 10, Power Knockback 1"),
        ),
        "next": "Hunter / Crossbowman",
    },
    "Thief · Lucky Seven": {
        "family": "thief",
        "ap": (
            "Start at 4 STR / 5 DEX / 4 INT / 12 LUK. Levels 2–13: +5 LUK each.",
            "Claw example: +5 DEX at Lv 14, 15, 20, 25 and 30. All other levels get +5 LUK. Lv 30 target: 30 base DEX / 132 base LUK.",
            "DEX on existing gear can cover some weapon requirements. Spend the remaining AP on LUK.",
        ),
        "sp": (
            (10, "Lucky Seven 1"),
            (12, "Lucky Seven 3, Nimble Body 3, Keen Eyes 1"),
            (18, "Lucky Seven 20, Keen Eyes 2"),
            (23, "Keen Eyes 15, Nimble Body 5"),
            (28, "Nimble Body 15, Disorder 3, Dark Sight 2"),
            (30, "Dark Sight 8"),
        ),
        "next": "Assassin / Sindit (claw leveling before Bandit)",
    },
    "Thief · Double Stab": {
        "family": "thief",
        "ap": (
            "For DEX daggers, use the Lucky Seven route’s AP targets, adjusting for the dagger you plan to equip.",
            "For STR daggers, keep starting DEX at 5 and raise STR only for the next dagger. Use the source’s STR Bandit table for the exact levels and put the remaining AP into LUK.",
        ),
        "sp": (
            (10, "Double Stab 1"),
            (17, "Double Stab 20, Nimble Body 2"),
            (22, "Nimble Body 15, Disorder 2"),
            (23, "Disorder 3, Dark Sight 2"),
            (29, "Dark Sight 20"),
            (30, "Disorder 6"),
        ),
        "next": "Bandit (dagger route without an SP reset)",
    },
}
