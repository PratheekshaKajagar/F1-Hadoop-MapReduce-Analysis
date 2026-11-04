#!/usr/bin/env python3
"""JOB 2 - REDUCE (per team x scope).
Output: team scope races entries points_total points_gp points_sprint wins podiums poles fastest_laps
        avg_finish_classified avg_finish_all avg_grid not_classified points_per_race"""
import sys
from common import *

for key, rows in groups(sys.stdin):
    team, scope = key.split("|")
    races, entries, gp, sp = set(), 0, 0.0, 0.0
    wins = pod = poles = fl = ncl = 0
    fin_c, fin_a, grids = [], [], []
    for r in rows:
        if r[0] == "S":
            sp += float(r[2]); continue
        # R race pts grid order pos classified fl
        races.add(r[1]); entries += 1; gp += float(r[2])
        grid = integer(r[3]); order = int(r[4]); pos = integer(r[5])
        if order == 1: wins += 1
        if order <= 3: pod += 1
        if grid == 1: poles += 1
        if r[7] == "1": fl += 1
        fin_a.append(order)
        if r[6] == "1": fin_c.append(pos)
        else: ncl += 1
        if grid is not None and grid > 0: grids.append(grid)
    tot = gp + sp
    emit(team, scope, len(races), entries, tot, gp, sp, wins, pod, poles, fl, mean(fin_c), mean(fin_a), mean(grids), ncl,
         tot / len(races) if races else None)
