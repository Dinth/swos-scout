# swos-scout

A read-only scouting report for [OpenSWOS](https://github.com/benbaker76/OpenSWOS)
career saves (Sensible World of Soccer 96/97). It shows which players in your squad
are worth keeping and who is worth buying. That includes players at every club in
the game, whether they are on the transfer list or not.

It never writes to your save. It is for looking, not cheating.

## What it shows

- **Your line-up**: each starter's rating in the slot your tactic gives him, with
  out-of-position, injured, loaned and sold players flagged. Then a plan, move by
  move: bring in a bench or reserve player who suits a slot better, or swap two
  starters. Each player is used once, and the team's total rating is shown before and
  after.
- **Your squad** by position: a 0–100 rating, each skill (0–7), the market value
  the game shows, status (form, injury, cards, trialist/reserve), and a verdict.
  The verdict is *keep*, *depth*, *sold* or *upgrade*. Under a player worth replacing
  is the best upgrade in each spending band: a swap that costs nothing net of his sale,
  then up to 10%, 25%, 50% and all of your budget (`--bands`). Each shows the rating
  gain, the change in every skill, the net cost, and the club's country and continent.
- **Best buys** per position, rated above your current best, in the same spending bands.
- **Any club's squad**, with each skill averaged over its outfield players.
- **A search** over every club player in the world, by position, minimum skills, price
  and name, sorted by rating, value or any one skill.

```
$ swos-scout squad --pos RB
Pos Rtg  Name                   Pas Vel Hea Tck Ctl Spd Fin   Value  Status   Verdict
RB   30  Oskar Wojcik             1   1   4   5   1   1   1    200K           upgrade (405 candidates)
    +13  Erick Canales           +1   0  -3  -2  +1  +4  -1    200K  Rtg 43, net even, Dep. Garcilaso (Peru, S. America)  [swap]  *
    +19  Yomar Rocha             +1   0  -3   0  +1  +4  -1    300K  Rtg 49, net +100K, Bolivar (Bolivia, S. America)  [<= 113K]  *
    +25  Matheus Silva            0  -1  -1  -2  +4  +4  -1    350K  Rtg 55, net +150K, Qarabag (Russia, Europe)  [<= 284K]  *
    +36  Emanuel Coronel         +3  +2  -3  -1  +4  +5   0    750K  Rtg 66, net +550K, Rosario Central (Argentina, S. America)  [<= 569K]  *
    +47  Agustin Giay            +3  +3  -2  +2  +3  +6  +1    1.3M  Rtg 77, net +1.1M, Palmeiras (Brazil, S. America)  [<= 1.14M]  *

$ swos-scout find --pos A --min s=6 c=6 --max-price 1
Pos Rtg  Name                   Club               Pas Vel Hea Tck Ctl Spd Fin   Value  Status
A    75  Nicolas Fernandez      Belgrano             3   5   0   2   6   6   6      1M    *
A    72  Nestory Irankunda      Watford              4   5   1   1   6   7   3    950K    *
A    70  Antony                 Portland Timbers     4   3   2   2   7   6   3    950K    *
```

## Usage

```
swos-scout                       line-up, squad, then best buys
swos-scout lineup [--min-gain N] [--changes N]
swos-scout squad [--pos POS] [--budget M] [--bands P,P,..] [--options N]
swos-scout buy   [--pos POS] [--budget M] [--bands P,P,..] [--top N]
swos-scout team NAME
swos-scout find  [--pos POS] [--min SKILL=N ...] [--max-price M] [--name TEXT]
                 [--sort rating|value|SKILL] [--top N]
swos-scout --save PATH <command>
```

`swos-scout --help` lists everything. Prices are in £ millions.
Positions: `GK RB LB D RW LW M A`. Skills: `p` passing, `v` velocity (shot power),
`h` heading, `t` tackling, `c` ball control, `s` speed, `f` finishing.

Without `--save`, the newest `~/.swos/save/*.CAR` is read. The first line of the
report names the file and when it was saved. The script only sees what is in that
file, so save your career in the game before running it again.

## How the numbers are worked out

- **Rating** is the player's skills weighted for his position. Speed and ball
  control weigh most for every outfield player (4). The other skills count by
  position: tackling, then passing and heading at the back; passing, then tackling in
  midfield; passing on the wings; finishing, then shot power up front (1–3). The weights are a judgement call, not a game table: the
  game's own position-value formula sets prices and barely counts finishing for
  attackers. Goalkeepers have no skills in SWOS, so their rating is their price
  index.
- **Skills** are the 0–7 values the match engine uses. The save stores 0–15, but
  8–15 is the same skill as 0–7: the engine ignores the extra bit, which only raises
  the player's price.
- **Out of position** a player keeps 90% of his rating on the other side of the same
  line (RB/LB, RW/LW), 75% in a neighbouring role and 50% anywhere else. The game
  values a player by the pitch areas his own position covers, so he loses value in a
  different slot; these percentages are an estimate of that, not a game table.
- **Line-up roles** come from your tactic: each slot's average place on the pitch in
  OpenSWOS's tactic data. For your own tactics (A–F), the starters' own positions are
  used.
- A player you have sold stays in the squad record, named `*ERR* ...`, until the
  transfer completes. He is shown as SOLD and never picked.
- National sides and custom teams are never offered as buys. `team` still shows them.
- **Value** is the price the game displays, worked out from OpenSWOS's own value
  tables and form adjustment. It is not the asking price; clubs usually want more.
- Clubs in your save (your league and the European competitions) show current
  skills and form. Every other club comes from the team database in
  `~/.swos/assets/data_json/teams` and is marked `*`, with skills and value as the
  season started.

## Install

Only Python 3 is needed, with nothing beyond the standard library:

```
./swos-scout.py --help
```

With Nix:

```
nix run github:Dinth/swos-scout -- find --pos M --sort c
```

## Licence

GPL-3.0, like OpenSWOS, whose data tables it reuses.
