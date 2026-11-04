#!/usr/bin/env python3
"""JOB 5 - Pit-stop performance.  Input: /f1/pitstops.
   Side files: results.csv (driver->constructor per race: map-side join), races.csv, constructors.csv, race_baseline.tsv.
   A stop is VALID if 10s <= duration <= 3 x the race's median NORMAL stop (stops <= 60 s; drops red-flag/repair stops).
   Keys: <team>|ALL, <team>|<year>, and FIELD|<year> (whole-grid reference)."""
import sys
from common import *

team_of = {}
tg = load_team_group()
for r in csv_rows("results.csv"):
    team_of[(int(r[1]), int(r[2]))] = tg[int(r[3])]
races = load_races(); base = load_baseline()
for line in sys.stdin:
    f = line.rstrip("\n").split(",")
    if is_header(f): continue
    race, drv, dur = int(f[0]), int(f[1]), float(f[4])
    team = team_of.get((race, drv)); b = base.get(race)
    if team is None or b is None: continue
    year = races[race][0]; med = b["pit_median"]
    valid = 1 if (med and 10.0 <= dur <= 3 * med) else 0       # no normal stop in the race -> cannot judge -> invalid
    slow = 1 if (valid and dur > 1.5 * med) else 0
    rel = (dur / med - 1) * 100 if valid else ""
    v = "%d\t%.3f\t%d\t%d\t%s" % (race, dur, valid, slow, rel if rel == "" else "%.3f" % rel)
    for k in ("%s|ALL" % team, "%s|%d" % (team, year), "FIELD|%d" % year, "FIELD|ALL"):
        print("%s\t%s" % (k, v))
