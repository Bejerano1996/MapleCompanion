"""EXP to the next level, EXP per kill solo and in a party, and kills left to level up.

Formulas from meowdb.com's Leveling & Tables page (/msclassic/formulas/leveling), checked
against its EXP table (Lv 1 15, Lv 25 47,216, Lv 50 709,716, Lv 51 748,608, Lv 90 11,938,059).
"""
import math
import re

PARTY_MAX = 6
# who hits the monsters in a party: everyone (your damage = 1/N), you alone (all of it),
# or the others while you're only there (eligible, no damage)
HITS = ("all", "me", "leech")


def exp_to_next(level):
    """EXP needed to go from `level` to `level` + 1."""
    if level < 1:
        return 0
    if level <= 5:
        return (level * level // 2 + 15) * level
    if level <= 50:
        q = level * level // 3
        return (q + 19) * q
    need = exp_to_next(50)
    for lv in range(51, min(level, 89) + 1):
        need = need * 10548 // 10000  # trunc(previous × 1.0548), in whole numbers
    for _ in range(90, level + 1):
        need = need * 21 // 10        # Lv 90-99: trunc(previous × 2.1)
    return need


def _round(x):
    """Halves round up (7.5 → 8), like the game."""
    return math.floor(x + 0.5)


def party_exp(mob_exp, level, members=1, hits="all", party_levels=None):
    """EXP you get when your party kills one monster worth `mob_exp`.
    `members`: eligible members on the map (you included; 1 = solo). `hits`: see HITS.
    `party_levels`: the sum of every eligible member's level (default: all at your level).
    The pool is split 80% by level and 20% by damage, then the party bonus is added:
    +10% per extra member (max 30%) and +5% per extra member who hit the monster."""
    members = max(1, min(PARTY_MAX, members))
    if members == 1:
        return mob_exp
    levels = party_levels or level * members
    hitters, damage = {"all": (members, 1 / members), "me": (1, 1.0), "leech": (1, 0.0)}[hits]
    share = max(1, _round(mob_exp * (0.8 * level / levels + 0.2 * damage)))
    bonus = min(0.30, 0.10 * (members - 1)) + 0.05 * (hitters - 1)
    return share + (max(1, _round(share * bonus)) if bonus > 0 else 0)


def kills_to_level(gain, level, exp_now=0):
    """Kills worth `gain` EXP each still needed to level up from `exp_now`."""
    left = max(0, exp_to_next(level) - exp_now)
    return math.ceil(left / gain) if gain > 0 else None


def percent(exp, level):
    """`exp` as a share of this level's bar, in % (what the game shows in brackets)."""
    need = exp_to_next(level)
    return 100 * exp / need if need else 0.0


def fmt_percent(p):
    """0.11% · 0.004% (tiny gains keep a digit that shows) · 12.50%"""
    return f"{p:.3f}%" if 0 < p < 0.01 else f"{p:.2f}%"


# ---------- the game's EXP bar: "EXP. 28,474 [51.87%]" ----------

# letters OCR reads for the bar's pixel digits: "Sl" for 51, "s.340" for 5.340, "B7" for 87
_DIGIT_LOOKALIKES = str.maketrans("SsZzGBOoDlIi|", "5522680001111")
_PERCENT = re.compile(r"(?<![\d.,])(\d{1,3}) ?[.,] ?(\d{2})(?!\d)")
_FRACTION = re.compile(r"[.,] ?(\d{2}) ?[%*+]")             # ".87%": the percent's end alone
_NUMBER = re.compile(r"(?<![\d.,])\d{1,3}(?:[.,]\d{3})+(?![\d])|(?<![\d.,])\d{1,10}(?![\d.,])")


def _digits(text):
    """Look-alike letters made digits, only inside words that already have a digit in them."""
    return re.sub(r"\S*\d\S*|[SsZzGBOoDlIi|]{1,3}(?= ?[.,] ?\d)",
                  lambda m: m[0].translate(_DIGIT_LOOKALIKES), text)


def bar_numbers(texts):
    """What the OCR'd versions of the EXP text say: (EXP numbers, percents, percent endings).
    The game writes thousands with a dot or a comma ("5.340", "28,474")."""
    numbers, percents, fractions = [], [], []
    for text in texts:
        text = _digits(text)
        for m in _PERCENT.finditer(text):
            if "%" in text[m.end():m.end() + 3] or not any(c in text for c in "%*+"):
                pct = int(m[1]) + int(m[2]) / 100
                if pct <= 100:
                    percents.append(pct)
        fractions += [int(f) for f in _FRACTION.findall(text)]
        rest = _PERCENT.sub(" ", text)
        numbers += [int(re.sub(r"[.,]", "", n)) for n in _NUMBER.findall(rest)]
    return numbers, percents, fractions


def shown_percent(exp, level):
    """The percent the game shows for `exp` at `level` (rounded to 0.01)."""
    return round(10000 * exp / exp_to_next(level)) / 100


def read_bar(texts, level, previous=None):
    """(level, exp or None, percent) from OCR'd versions of the bar's EXP text, or None.
    The EXP number is trusted when the percent agrees with it at your level: the whole percent,
    or just its two decimals (at some sizes "51.87%" reads as "Sl .87%"). The level just above
    yours is tried too (you leveled up), and any level within 10 when a whole percent agrees
    (the level box was wrong). Without an agreeing number, the percent most versions read
    (a tie goes to the one nearest the `previous` percent: the bar only creeps up)."""
    numbers, percents, fractions = bar_numbers(texts)
    order = sorted(set(numbers), key=lambda n: (-numbers.count(n), -n))
    for lv in [level, level + 1] + sorted(range(max(1, level - 10), level + 11), key=lambda v: abs(v - level)):
        for n in order:
            if not 0 <= n < exp_to_next(lv):
                continue
            shown = shown_percent(n, lv)
            if any(abs(shown - p) < 0.006 for p in percents) or                     (lv in (level, level + 1) and round(shown * 100) % 100 in fractions):
                return lv, n, shown
    if percents:
        near = (lambda p: -abs(p - previous)) if previous is not None else (lambda p: 0)
        best = max(set(percents), key=lambda p: (percents.count(p), near(p)))
        return level, None, best
    return None


def exp_from_bar(exp, pct, level):
    """Your EXP into this level from a bar reading: the number when it matches the percent
    (to 0.01%), else worked out from the percent (off by at most 0.005% of the bar)."""
    need = exp_to_next(level)
    if exp is not None and exp < need and abs(100 * exp / need - pct) < 0.011:
        return exp
    return min(need - 1, round(pct * need / 100))
