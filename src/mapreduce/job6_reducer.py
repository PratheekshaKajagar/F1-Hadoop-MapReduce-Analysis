#!/usr/bin/env python3
"""JOB 6 - REDUCE.  Writes four record types (first column = rtype):
 SEASON   year races entries not_classified_pct distinct_winners distinct_winning_teams n_rep_laps avg_rep_lap_sec
 DRIVER   year driverId races_gp points_gp wins podiums avg_finish_all laps laps_led avg_rel_pace_pct final_pos final_points final_wins
 TEAM     year team races_gp points_gp wins podiums avg_finish_all final_pos final_points final_wins
 CIRCYEAR layoutId year n_rep_laps avg_rep_lap_sec fastest_lap_sec
 (final_* = OFFICIAL championship standing after the season's last round)"""
import sys
from common import *

for key, rows in groups(sys.stdin):
    p = key.split("|"); rt = p[0]
    res = [r for r in rows if r[0] == "R"]
    lap = [r for r in rows if r[0] == "L"]
    st = [r for r in rows if r[0] == "S"]
    final = max(st, key=lambda r: int(r[1])) if st else None      # standing after the LAST round of the season
    fpos, fpts, fwin = (integer(final[2]), num(final[3]), integer(final[4])) if final else (None, None, None)
    races = set(r[1] for r in res)
    pts = sum(float(r[2]) for r in res)
    wins = sum(1 for r in res if int(r[3]) == 1); pod = sum(1 for r in res if int(r[3]) <= 3)
    avg_fin = mean(int(r[3]) for r in res)
    if rt == "SEASON":
        nl = sum(int(r[2]) for r in lap); sl = sum(float(r[3]) for r in lap)   # L: laps n_rep sum_sec
        winners = set(r[7] for r in res if int(r[3]) == 1); wteams = set(r[6] for r in res if int(r[3]) == 1)   # R: race pts order cl pos team drv
        ncl = sum(1 for r in res if r[4] == "0")
        emit("SEASON", p[1], len(races), len(res), 100.0 * ncl / len(res) if res else None, len(winners), len(wteams), nl, sl / nl if nl else None)
    elif rt == "DRIVER":
        laps = sum(int(r[1]) for r in lap); led = sum(int(r[2]) for r in lap)
        n = sum(int(r[3]) for r in lap); sr = sum(float(r[4]) for r in lap)
        emit("DRIVER", p[1], p[2], len(races), pts, wins, pod, avg_fin, laps, led, sr / n if n else None, fpos, fpts, fwin)
    elif rt == "TEAM":
        emit("TEAM", p[1], p[2], len(races), pts, wins, pod, avg_fin, fpos, fpts, fwin)
    elif rt == "CIRCYEAR":
        n = sum(int(r[1]) for r in lap); s = sum(float(r[2]) for r in lap)
        emit("CIRCYEAR", p[1], p[2], n, s / n if n else None, min(float(r[3]) for r in lap))
