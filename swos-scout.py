#!/usr/bin/env python3
"""swos-scout: read-only scouting report for an OpenSWOS career save.

Purpose:
    Rate every player in your squad and in the world database (every club,
    transfer-listed or not) by how well their skills suit their position,
    next to their market value, so you can see who is worth keeping and who
    is worth buying. The save is only read.

    swos-scout                 squad with verdicts, then best buys
    swos-scout squad|buy       one of the two
    swos-scout team NAME       any club's full squad
    swos-scout find [filters]  search every player by position/skill/price

    Rating (0-100): the player's seven skills (0-7) weighted by how much each
    one counts at his position (WEIGHTS below: speed and ball control first
    for everyone, a judgement call, not a game table). Goalkeepers have no
    skills in SWOS. Their quality is their price index, so their rating is
    that index scaled to 0-100.

    Value: what the game shows as the player's price. It is the price index
    plus a form adjustment, looked up in the game's value table
    (GetDisplayedPlayerValue / FormatPlayerValueOrStatusText in OpenSWOS,
    https://github.com/benbaker76/OpenSWOS).

Dependencies:
    Python 3 standard library only. Reads ~/.swos/save/*.CAR (OpenSWOS JSON
    careers) and ~/.swos/assets/data_json/teams/*.json (the team database).

Author:
    AI (Claude), for Dinth. https://github.com/Dinth/swos-scout
"""

import argparse
import glob
import json
import os
import sys

POS = ["GK", "RB", "LB", "D", "RW", "LW", "M", "A"]
POS_LONG = {
    "GK": "Goalkeepers", "RB": "Right backs", "LB": "Left backs",
    "D": "Centre backs", "RW": "Right wingers", "LW": "Left wingers",
    "M": "Midfielders", "A": "Attackers",
}
# Order the game shows skills in, and the save's field names.
SKILLS = ["passing", "velocity", "heading", "tackling",
          "control", "speed", "finishing"]
SKILL_LABELS = ["Pas", "Vel", "Hea", "Tck", "Ctl", "Spd", "Fin"]
SKILL_ALIASES = {
    "p": "passing", "pas": "passing", "v": "velocity", "vel": "velocity",
    "h": "heading", "hea": "heading", "t": "tackling", "tck": "tackling",
    "c": "control", "ctl": "control", "s": "speed", "spd": "speed",
    "f": "finishing", "fin": "finishing",
}

# How much each skill counts at each outfield position. Speed and ball
# control matter most for every player, whatever the position; the rest
# only separates players who are otherwise level.
WEIGHTS = {
    1: dict(speed=4, control=4, tackling=3, passing=2, heading=1, velocity=0, finishing=0),  # RB
    2: dict(speed=4, control=4, tackling=3, passing=2, heading=1, velocity=0, finishing=0),  # LB
    3: dict(speed=4, control=4, tackling=3, heading=2, passing=1, velocity=0, finishing=0),  # D
    4: dict(speed=4, control=4, passing=2, velocity=1, finishing=1, tackling=1, heading=0),  # RW
    5: dict(speed=4, control=4, passing=2, velocity=1, finishing=1, tackling=1, heading=0),  # LW
    6: dict(speed=4, control=4, passing=3, tackling=2, velocity=1, heading=1, finishing=1),  # M
    7: dict(speed=4, control=4, finishing=3, velocity=2, heading=1, passing=1, tackling=0),  # A
}

# _avgTeamValues (price index + form -> value step) and _avgTeamValueBases
# (value step -> value in thousands of pounds).
AVG_TEAM_VALUES = [
    5, 5, 6, 8, 10, 13, 15, 17, 20, 21, 23, 25, 26, 28, 30, 32, 34, 35, 37,
    38, 39, 40, 41, 42, 43, 44, 45, 47, 48, 49, 51, 53, 54, 56, 57, 58, 59,
    61, 62, 63, 65, 66, 67, 68, 69, 70, 71, 73, 76, 76,
]
VALUE_BASES = [
    0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85,
    90, 95, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 225, 250,
    275, 300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800, 850, 900,
    950, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000,
    2250, 2500, 2750, 3000, 3500, 4000, 4500, 5000, 6000, 7000, 8000, 9000,
    10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000, 18000, 19000,
    20000, 21000, 22000, 23000, 24000, 25000, 26000, 27000, 28000, 29000,
    30000,
]
# kPlayerAgeToFormDivisorTable (indexed by price index).
FORM_DIVISOR = [
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 6, 6, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8, 9, 9, 9, 10, 10, 12, 12, 12, 15, 15, 15,
    15, 15, 15, 15,
]
FORM_TRIALIST = -101   # 0x9B as a signed byte
FORM_RESERVE = -102    # 0x9A
PF_INFORM, PF_LOAN = 0x01, 0x02


def skill(p, name):
    """The 0-7 skill the match engine uses (the high bit of the nibble is ignored)."""
    return p[name] & 7


def rating(p):
    """0-100 position-weighted rating (GK: price index scaled)."""
    if p["position"] == 0:
        return round(min(p["price"], 49) / 49 * 100)
    w = WEIGHTS[p["position"]]
    return round(sum(w[s] * skill(p, s) for s in SKILLS) / (7 * sum(w.values())) * 100)


def value_k(p):
    """Displayed market value in thousands of pounds."""
    price = max(0, min(p["price"], 49))
    form = p["form"]
    if form in (FORM_TRIALIST, FORM_RESERVE):
        form = 0
    elif p["flags"] & PF_INFORM:
        form *= 2
    step = AVG_TEAM_VALUES[price] + int(form / FORM_DIVISOR[price])
    return VALUE_BASES[max(1, min(step, 80))]


def money(k):
    """Format thousands of pounds the way the game does (750K, 1.5M)."""
    if k < 1000:
        return f"{k}K"
    m = k / 1000
    return f"{m:.2f}".rstrip("0").rstrip(".") + "M"


def status(p):
    """Short status column: injury, cards, loan, trialist/reserve, form."""
    out = []
    if p["form"] == FORM_TRIALIST:
        out.append("TRIAL")
    elif p["form"] == FORM_RESERVE:
        out.append("RES")
    elif p["form"]:
        out.append(f"form{p['form']:+d}")
    if p["flags"] & PF_LOAN:
        out.append("LOAN")
    if p["injury"]:
        out.append(f"INJ{p['injury']}")
    if p["cards"]:
        out.append(f"cards{p['cards']}")
    return " ".join(out)


def latest_save(save_dir):
    """Most recently written career save."""
    saves = glob.glob(os.path.join(save_dir, "*.CAR"))
    if not saves:
        sys.exit(f"swos-scout: no career saves (*.CAR) in {save_dir}")
    return max(saves, key=os.path.getmtime)


def world_players(save, db_dir, own_gtn):
    """Every player you could bid for: teams in the save (current skills and
    form) first, then the rest of the database (as the season started)."""
    seen_teams, players = set(), []

    def add(team, plist, source):
        # A club can be in the save twice (league and European pool) under
        # two numbers, so its name counts as seen too.
        gtn, name = team["global_team_number"], team["team_name"]
        if gtn == own_gtn or gtn in seen_teams or name in seen_teams:
            return
        seen_teams.update((gtn, name))
        for p in plist:
            if p.get("player_name"):
                players.append((team["team_name"], source, p))

    for t in (save.get("selected_teams") or []) + (save.get("tmd_teams") or []):
        add(t["team"], t["players"], "save")
    for path in sorted(glob.glob(os.path.join(db_dir, "*.json"))):
        try:
            with open(path, encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, ValueError):
            continue
        if doc.get("type") != "team":
            continue
        for t in doc.get("teams", []):
            add(t["team"], t["players"], "db")
    return players


def skill_name(text):
    """Full skill name from a name or abbreviation (s, spd, speed...)."""
    t = text.lower()
    if t in SKILLS:
        return t
    if t in SKILL_ALIASES:
        return SKILL_ALIASES[t]
    sys.exit(f"swos-scout: unknown skill {text} (P V H T C S F or full names)")


def row(p, club=None):
    """One table row: position, rating, each skill, value, status."""
    skills = " ".join(
        f"{'-' if p['position'] == 0 else skill(p, s):>3}" for s in SKILLS)
    name = p["player_name"].title()
    c = f"{club.title()[:18]:<18} " if club is not None else ""
    return (f"{POS[p['position']]:<3}{rating(p):>4}  {name[:22]:<22} {c}"
            f"{skills}  {money(value_k(p)):>6}  {status(p)}")


def header(with_club):
    """Column header matching row()."""
    c = f"{'Club':<18} " if with_club else ""
    return (f"Pos Rtg  {'Name':<22} {c}{' '.join(SKILL_LABELS)}  "
            f"{'Value':>6}  Status")


def parse_pos(text):
    """Position code (GK RB LB D RW LW M A) to its number."""
    if text is None:
        return None
    t = text.upper()
    if t not in POS:
        sys.exit(f"swos-scout: unknown position {text} (one of {' '.join(POS)})")
    return POS.index(t)


def main():
    """Parse the command line and print the chosen report."""
    ap = argparse.ArgumentParser(
        description="Read-only OpenSWOS career scouting report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
commands and their options:
  (none)                       squad, then best buys
  squad                        your squad with keep/upgrade verdicts
      --pos POS                only this position
      --budget M               money for upgrades, in £M (default: bank balance)
  buy                          best buys per position, rated above your best
      --pos POS                only this position
      --budget M               max price in £M (default: bank balance)
      --top N                  players per position (default 5)
  team NAME                    any club's full squad (part of the name is enough)
  find                         search every player in the world
      --pos POS                only this position
      --min SKILL=N ...        minimum skills, e.g. --min s=6 c=5
      --max-price M            max value in £M
      --name TEXT              player name contains
      --sort KEY               rating (default), value, or a skill
      --top N                  rows shown (default 25)

--save goes before the command: swos-scout --save ~/.swos/save/D.CAR squad
Without it, the newest ~/.swos/save/*.CAR is read (named on the first line).

positions: GK RB LB D RW LW M A
skills (0-7): p/pas passing, v/vel velocity (shot power), h/hea heading,
  t/tck tackling, c/ctl ball control, s/spd speed, f/fin finishing
Rtg (0-100): skills weighted for the position, speed and ball control most;
  goalkeepers have no skills, so theirs is their price index.
Clubs marked * are not in your save: skills and value as the season started.

examples:
  swos-scout find --pos A --min s=6 c=6 --max-price 1
  swos-scout find --pos RB --sort s --top 10
  swos-scout team legia""")
    ap.add_argument("--save", help="career save (default: newest ~/.swos/save/*.CAR)")
    sub = ap.add_subparsers(dest="cmd")
    p_squad = sub.add_parser("squad", help="your squad with keep/upgrade verdicts")
    p_buy = sub.add_parser("buy", help="best buys per position within budget")
    for p in (p_squad, p_buy):
        p.add_argument("--pos", help="only this position (GK RB LB D RW LW M A)")
        p.add_argument("--budget", type=float, help="max price in £M (default: your bank balance)")
    p_buy.add_argument("--top", type=int, default=5, help="players per position (default 5)")
    p_team = sub.add_parser("team", help="any club's full squad (name or part of it)")
    p_team.add_argument("name", nargs="+")
    p_find = sub.add_parser("find", help="search every player in the world")
    p_find.add_argument("--pos", help="position (GK RB LB D RW LW M A)")
    p_find.add_argument("--min", nargs="+", default=[], metavar="SKILL=N",
                        help="minimum skills, e.g. --min s=6 c=5")
    p_find.add_argument("--sort", default="rating",
                        help="sort by rating (default), value, or a skill (s, c, f...)")
    p_find.add_argument("--max-price", type=float, help="max value in £M")
    p_find.add_argument("--name", help="player name contains")
    p_find.add_argument("--top", type=int, default=25, help="rows shown (default 25)")
    args = ap.parse_args()
    cmd = args.cmd or "all"

    home = os.path.expanduser("~/.swos")
    path = args.save or latest_save(os.path.join(home, "save"))
    with open(path, encoding="utf-8") as f:
        save = json.load(f)

    team = save["career_team"]["team"]
    squad = save["career_team"]["players"] + (save.get("career_team_reserves") or [])
    squad = [p for p in squad if p.get("player_name")]
    balance = save["career_scalars"].get("new_balance", 0)
    budget = getattr(args, "budget", None)
    budget_k = budget * 1000 if budget is not None else max(balance, 0) / 1000
    only = parse_pos(getattr(args, "pos", None))

    print(f"{team['team_name'].title()} - {os.path.basename(path)} - "
          f"balance £{balance:,} - squad value "
          f"{money(sum(value_k(p) for p in squad))}")
    print("Rtg: 0-100, speed and ball control weigh most (GK: price index). "
          "Skills 0-7.\n")

    db_dir = os.path.join(home, "assets", "data_json", "teams")
    world = world_players(save, db_dir, team["global_team_number"])
    note = "\n* not in your save: skills and value as the season started."

    def upgrades(pos, floor, cap_k):
        """World players at `pos` rated above `floor` and valued <= cap_k."""
        return sorted(
            (m for m in world
             if m[2]["position"] == pos and rating(m[2]) > floor
             and value_k(m[2]) <= cap_k),
            key=lambda m: (-rating(m[2]), value_k(m[2])))

    if cmd in ("all", "squad"):
        print("YOUR SQUAD (by position, best first)")
        print(header(False) + "  Verdict")
        for pos in range(8):
            if only is not None and pos != only:
                continue
            group = sorted((p for p in squad if p["position"] == pos),
                           key=rating, reverse=True)
            for i, p in enumerate(group):
                verdict = "keep"
                # Could you replace him with someone clearly better using
                # your balance plus his own sale price?
                better = upgrades(pos, rating(p) + 10, budget_k + value_k(p))
                if better:
                    club, _, b = better[0]
                    verdict = (f"upgrade: {b['player_name'].title()} of "
                               f"{club.title()} ({rating(b)}, {money(value_k(b))})")
                elif i >= 2 and pos != 0:
                    verdict = "depth"
                print(f"{row(p)}  {verdict}")
        print()

    if cmd in ("all", "buy"):
        print(f"BEST BUYS within {money(int(budget_k))} "
              f"(rated above your best at the position)")
        top = getattr(args, "top", 5)
        for pos in range(8):
            if only is not None and pos != only:
                continue
            mine = max((rating(p) for p in squad if p["position"] == pos), default=0)
            best = upgrades(pos, mine, budget_k)[:top]
            print(f"\n{POS_LONG[POS[pos]]} (your best: {mine})")
            if not best:
                print("  nobody better within budget")
                continue
            print("  " + header(True))
            for club, src, p in best:
                print("  " + row(p, club) + ("" if src == "save" else "  *"))
        print(note)

    if cmd == "team":
        want = " ".join(args.name).upper()
        clubs = {}
        for club, src, p in world:
            clubs.setdefault(club, (src, []))[1].append(p)
        hits = [c for c in clubs if want in c.upper()]
        exact = [c for c in hits if c.upper() == want]
        hits = exact or hits
        if not hits:
            sys.exit(f"swos-scout: no club matching {want}")
        if len(hits) > 1:
            print(f"{len(hits)} clubs match: " + ", ".join(sorted(c.title() for c in hits)))
            print("Give more of the name.")
            return
        club = hits[0]
        src, players = clubs[club]
        players = sorted(players, key=lambda p: (p["position"], -rating(p)))
        print(f"{club.title()}{'' if src == 'save' else '  *'}")
        print(header(False))
        for p in players:
            print(row(p))
        outfield = [p for p in players if p["position"]]
        if outfield:
            avg = " ".join(f"{sum(skill(p, s) for p in outfield) / len(outfield):>3.1f}"[-3:]
                           for s in SKILLS)
            print(f"{'':<7}{'outfield average':<23}{avg}")
        if src != "save":
            print(note)

    if cmd == "find":
        mins = []
        for m in args.min:
            k, _, v = m.partition("=")
            if not v.isdigit():
                sys.exit(f"swos-scout: --min wants SKILL=N, got {m}")
            mins.append((skill_name(k), int(v)))
        cap_k = args.max_price * 1000 if args.max_price is not None else None
        name = args.name.upper() if args.name else None
        hits = [
            (club, src, p) for club, src, p in world
            if (only is None or p["position"] == only)
            and (cap_k is None or value_k(p) <= cap_k)
            and (name is None or name in p["player_name"].upper())
            and all(p["position"] and skill(p, s) >= n for s, n in mins)
        ]
        sort = args.sort.lower()
        if sort == "rating":
            key = lambda m: (-rating(m[2]), value_k(m[2]))  # noqa: E731
        elif sort == "value":
            key = lambda m: (value_k(m[2]), -rating(m[2]))  # noqa: E731
        else:
            s = skill_name(sort)
            key = lambda m: (-skill(m[2], s), -rating(m[2]), value_k(m[2]))  # noqa: E731
        hits.sort(key=key)
        print(f"{len(hits)} players match; showing {min(len(hits), args.top)}")
        print(header(True))
        for club, src, p in hits[: args.top]:
            print(row(p, club) + ("" if src == "save" else "  *"))
        print(note)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
