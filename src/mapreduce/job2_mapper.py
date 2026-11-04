#!/usr/bin/env python3
"""JOB 2 - Constructor performance.  Inputs: /f1/results and /f1/sprint_results.
   Side files: races.csv (year), constructors.csv (team lineage group).
   MAP: key = team|ALL and team|<year> so one pass yields career AND per-season rows."""
import sys
from common import *

races = load_races(); tg = load_team_group()
path = input_file()
sprint = "/sprint_results/" in path
for line in sys.stdin:
    f = line.rstrip("\n").split(",")
    if is_header(f):
        continue
    race, con = int(f[1]), int(f[3])
    year = races[race][0]; team = tg[con]
    grid, pos, order, pts = integer(f[4]), integer(f[5]), integer(f[6]), num(f[7]) or 0.0
    if sprint:
        v = "S\t%d\t%.1f" % (race, pts)
    else:
        classified = 1 if pos is not None else 0
        rank = integer(f[10])
        v = "R\t%d\t%.1f\t%s\t%s\t%s\t%d\t%d" % (race, pts, "" if grid is None else grid, order, pos if pos is not None else "", classified,
                                                1 if rank == 1 else 0)
    for scope in ("ALL", str(year)):
        print("%s|%s\t%s" % (team, scope, v))
