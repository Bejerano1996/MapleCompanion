"""Party quests in MapleStory Classic World: requirements, what to do in each stage (with the quiz
answers and every puzzle combination), EXP and rewards.

Sources (read 2026-10-25):
- meowdb.com/msclassic/guides/kerning-city-party-quest-kpq-guide (stages, quiz, combinations,
  the PQ's own monster stats, Proof of Companionship, Squishy Shoes)
- mapleclassic.wiki/wiki/Kerning_City_Party_Quest (more quiz questions, Companion's Magic Box
  contents, channels 3-12 since the 21 Oct 2026 update)
Numbers the sources don't give (EXP per stage, box chances) are left out rather than guessed.
"""

PARTY_QUESTS = [
    {
        "key": "kpq",
        "name": "Kerning City PQ",
        "quest": "First Time Together",
        "level": "21+ (21-30 in the original game)",
        "party": "exactly 4 players",
        "time": "30 min",
        "channels": "3-12",
        "npc": "Lakelis",
        "map": "010003000",  # Kerning City, by the sewer entrance
        "stages": [
            {"name": "Stage 1 · Ligators and Cloto",
             "do": "Kill the 22 Ligators for coupons. Cloto asks everyone but the leader a question; "
                   "hand her exactly that many coupons for a pass, drop the extras. The leader gives "
                   "the passes to Cloto.",
             "answers": [
                 ("Level for 1st job (Warrior / Magician / Bowman / Thief)", 10),
                 ("EXP needed from level 1 to level 2", 15),
                 ("INT a Magician needs", 20),
                 ("Level needed to enter this party quest", 21),
                 ("DEX a Bowman or Thief needs", 25),
                 ("Total AP gained from level 1 to level 6", 25),
                 ("Level needed for the 2nd job advancement", 30),
                 ("STR a Warrior needs", 35),
             ],
             "tip": "The leader is never asked: if someone gets the 35-coupon question, make them leader."},
            {"name": "Stage 2 · Ropes",
             "do": "4 ropes (A, B high; C, D low). 3 players hang on 3 ropes, the leader asks Cloto.",
             "combos": ["A B C", "A B D", "A C D", "B C D"]},
            {"name": "Stage 3 · Kittens",
             "do": "5 platforms with 1-5 kittens. 3 players stand on 3 platforms, the leader asks Cloto.",
             "combos": ["1 2 3", "1 2 4", "1 2 5", "1 3 4", "1 3 5", "1 4 5", "2 3 4", "2 3 5", "2 4 5", "3 4 5"],
             "tip": "Lists going around often miss 3 4 5."},
            {"name": "Stage 4 · Barrels",
             "do": "6 numbered barrels. 3 players stand on 3 barrels, the leader asks Cloto.",
             "combos": ["1 2 3", "1 2 4", "1 2 5", "1 2 6", "1 3 4", "1 3 5", "1 3 6", "1 4 5", "1 4 6", "1 5 6",
                        "2 3 4", "2 3 5", "2 3 6", "2 4 5", "2 4 6", "2 5 6", "3 4 5", "3 4 6", "3 5 6", "4 5 6"]},
            {"name": "Last stage · King Slime",
             "do": "Kill 3 Curse Eyes, 6 Jr. Neckis and King Slime; each drops a pass, the leader gives "
                   "them all to Cloto. King Slime splits into 11 Slimes when it dies.",
             "tip": "Jr. Neckis dodge a lot: bring someone with good accuracy."},
            {"name": "Bonus",
             "do": "36 mushrooms (24 Horny, 12 Green) in one small room until the time runs out. "
                   "There's no portal out: talk to Nella."},
        ],
        # the PQ's own monsters (their stats differ from the same names outside the PQ)
        "exp": [("Ligator", 21, 68, 22), ("Jr. Necki", 25, 80, 6), ("Curse Eye", 29, 94, 3), ("King Slime", 32, 2400, 1)],
        "exp_note": "Monster EXP for the whole run (the bonus room's mushrooms come on top). The sources "
                    "give no fixed EXP per stage.",
        "once": "Proof of Companionship (Lakelis, Lv 21, once): defeat King Slime → 1,870 EXP, 687 mesos, "
                "1 fame and an Intermediate earring scroll (STR, DEX, INT or LUK).",
        "rewards": [
            ("Companion's Magic Box (everyone, one per clear) · chances not published",
             ["Blue / Brown / Green Bamboo Hat", "Yellow Square", "Red Cross, Gold, Star or Emerald Earrings",
              "Earring LUK Scroll: Intermediate", "Earring Crit. Damage Scroll: Intermediate",
              "Overall Armor STR Scroll: Greater", "Orange Potion ×10", "Blue Potion ×10", "Unagi ×10",
              "Screw ×10", "Bronze or Gold Ore ×5", "Iron, Orihalcon, Amethyst or Opal Ore ×8",
              "Fragment of Magic ×1"]),
            ("King Slime can drop", ["Squishy Shoes (Lv 28, +1 all stats, 18 DEF, 5 slots, tradeable)"]),
        ],
        "notes": ["Dying doesn't end the run. 3 players can finish; at 2 the puzzles can't be done.",
                  "New accounts may not be able to drop coupons: make the new player the leader."],
        "sources": ["meowdb.com KPQ guide", "mapleclassic.wiki Kerning City Party Quest"],
    },
]
