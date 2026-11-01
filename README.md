# swos-scout

A read-only scouting report for [OpenSWOS](https://github.com/benbaker76/OpenSWOS)
career saves (Sensible World of Soccer 96/97). It shows which players in your squad
are worth keeping and who is worth buying. That includes players at every club in
the game, whether they are on the transfer list or not.

It never writes to your save. It is for looking, not cheating.

## What it shows

- **Your squad** by position: a 0–100 rating, each skill (0–7), the market value
  the game shows, status (form, injury, cards, trialist/reserve), and a verdict.
  The verdict is *keep*, *depth*, or *upgrade* (the best clearly better player your
  balance plus his sale price would buy).
- **Best buys** per position, rated above your current best and within budget.
- **Any club's squad**, with each skill averaged over its outfield players.
- **A search** over every player in the world, by position, minimum skills, price
  and name, sorted by rating, value or any one skill.

```
$ swos-scout find --pos A --min s=6 c=6 --max-price 1
Pos Rtg  Name                   Club               Pas Vel Hea Tck Ctl Spd Fin   Value  Status
A    75  Nicolas Fernandez      Belgrano             3   5   0   2   6   6   6      1M    *
A    72  Nestory Irankunda      Watford              4   5   1   1   6   7   3    950K    *
A    70  Antony                 Portland Timbers     4   3   2   2   7   6   3    950K    *
```

## Usage

```
swos-scout                       squad, then best buys
swos-scout squad [--pos POS] [--budget M]
swos-scout buy   [--pos POS] [--budget M] [--top N]
swos-scout team NAME
swos-scout find  [--pos POS] [--min SKILL=N ...] [--max-price M] [--name TEXT]
                 [--sort rating|value|SKILL] [--top N]
swos-scout --save PATH <command>
```

`swos-scout --help` lists everything. Prices are in £ millions.
Positions: `GK RB LB D RW LW M A`. Skills: `p` passing, `v` velocity (shot power),
`h` heading, `t` tackling, `c` ball control, `s` speed, `f` finishing.

Without `--save`, the newest `~/.swos/save/*.CAR` is read. The first line of the
report names the file. Save your career in the game before running it again.

## How the numbers are worked out

- **Rating** is the player's skills weighted for his position. Speed and ball
  control weigh most for every outfield player, and the rest separate players who
  are otherwise level. The weights are a judgement call, not a game table: the
  game's own position-value formula sets prices and barely counts finishing for
  attackers. Goalkeepers have no skills in SWOS, so their rating is their price
  index.
- **Skills** are the 0–7 values the match engine uses.
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
