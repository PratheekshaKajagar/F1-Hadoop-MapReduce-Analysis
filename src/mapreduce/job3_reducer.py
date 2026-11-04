#!/usr/bin/env python3
"""JOB 3 - REDUCE (one call per circuit).
Output: layoutId races first_year last_year avg_rep_lap_sec fastest_lap_sec fastest_lap_year avg_fastest_lap_speed_kmh
        pace_spread_pct dnf_rate_pct avg_abs_pos_change grid_finish_corr avg_winning_margin_sec pole_win_rate_pct"""
import sys
from common import *

races = load_races()
for cid, rows in groups(sys.stdin):
    race_set, years = set(), set()
    pace = {}          # race -> {driver: mean rel pace}
    n_rep = 0; s_sec = 0.0
    fastest, fl_year = 1e18, None
    entries = ncl = 0
    chg, gx, gy, speeds, margins = [], [], [], [], []
    pole_n = pole_w = 0
    for r in rows:
        if r[0] == "L":
            race, drv, n, ssec, srel, mn = int(r[1]), int(r[2]), int(r[3]), float(r[4]), float(r[5]), float(r[6])
            race_set.add(race); years.add(races[race][0])
            n_rep += n; s_sec += ssec
            if n >= 10:
                pace.setdefault(race, []).append(srel / n)
            if mn < fastest: fastest, fl_year = mn, races[race][0]
        else:
            race, grid, pos, order, classified, speed, gap = int(r[1]), integer(r[2]), integer(r[3]), int(r[4]), r[5], num(r[6]), num(r[7])
            race_set.add(race); years.add(races[race][0])
            entries += 1
            if classified != "1": ncl += 1
            if speed: speeds.append(speed)
            if classified == "1" and grid and grid > 0:
                chg.append(abs(grid - pos)); gx.append(grid); gy.append(pos)
            if order == 2 and gap is not None: margins.append(gap)
            if grid == 1:
                pole_n += 1
                if order == 1: pole_w += 1
    spreads = [stdev(v) for v in pace.values() if len(v) >= 5]
    emit(cid, len(race_set), min(years), max(years), (s_sec / n_rep) if n_rep else None, fastest if fastest < 1e17 else None, fl_year,
         mean(speeds), mean([s for s in spreads if s is not None]), ncl * 100.0 / entries if entries else None, mean(chg),
         pearson(gx, gy), mean(margins), pole_w * 100.0 / pole_n if pole_n else None)
