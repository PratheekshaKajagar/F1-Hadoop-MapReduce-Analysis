#!/usr/bin/env python3
"""JOB 4 - REDUCE.  Output: rtype key entries n_grid_race avg_qual_pos avg_grid avg_finish_classified avg_finish_all
   avg_gain_vs_grid std_gain pct_gained pct_lost pct_same avg_gain_vs_quali avg_grid_penalty wins podiums corr_grid_finish
   gain = grid - finish (positive = places gained).  Only classified finishers with a real grid slot (>0) are used for gains."""
import sys
from common import *

for key, rows in groups(sys.stdin):
    rtype, k = key.split("|")
    n = len(rows); gains, gq, qs, grids, fin_c, fin_a, pen, gx, gy = [], [], [], [], [], [], [], [], []
    wins = pod = 0
    for r in rows:
        grid, pos, order, cl, q = integer(r[0]), integer(r[1]), int(r[2]), r[3], integer(r[4])
        fin_a.append(order)
        if order == 1: wins += 1
        if order <= 3: pod += 1
        if q is not None: qs.append(q)
        if grid is not None and grid > 0: grids.append(grid)
        if cl == "1": fin_c.append(pos)
        if cl == "1" and grid and grid > 0:
            gains.append(grid - pos); gx.append(grid); gy.append(pos)
            if q is not None: gq.append(q - pos)
        if grid and grid > 0 and q is not None: pen.append(grid - q)
    m = len(gains)
    emit(rtype, k, n, m, mean(qs), mean(grids), mean(fin_c), mean(fin_a), mean(gains), stdev(gains),
         100.0 * sum(1 for g in gains if g > 0) / m if m else None, 100.0 * sum(1 for g in gains if g < 0) / m if m else None,
         100.0 * sum(1 for g in gains if g == 0) / m if m else None, mean(gq), mean(pen), wins, pod, pearson(gx, gy))
