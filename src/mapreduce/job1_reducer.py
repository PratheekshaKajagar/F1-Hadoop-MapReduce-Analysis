#!/usr/bin/env python3
"""JOB 1 - REDUCE (one call per driver).
Output: driverId races laps_total laps_led fastest_lap_sec slowest_lap_sec n_rep_laps avg_lap_sec std_lap_sec
        slowest_rep_lap_sec avg_rel_pace_pct consistency_cv_pct avg_fastest_gap_pct usable_races"""
import math, sys
from common import *

base = load_baseline()
for drv, rows in groups(sys.stdin):
    per_race = {}
    for r in rows:
        race = int(r[0]); v = [int(r[1]), int(r[2]), float(r[3]), float(r[4]), int(r[5]), float(r[6]), float(r[7]), float(r[8]), float(r[9])]
        p = per_race.get(race)
        if p is None:
            per_race[race] = v
        else:
            p[0] += v[0]; p[1] += v[1]; p[2] = min(p[2], v[2]); p[3] = max(p[3], v[3])
            p[4] += v[4]; p[5] += v[5]; p[6] += v[6]; p[7] += v[7]; p[8] = max(p[8], v[8])
    laps = sum(p[0] for p in per_race.values()); led = sum(p[1] for p in per_race.values())
    fast = min(p[2] for p in per_race.values()); slow = max(p[3] for p in per_race.values())
    n = sum(p[4] for p in per_race.values())
    s = sum(p[5] for p in per_race.values()); ss = sum(p[6] for p in per_race.values()); sr = sum(p[7] for p in per_race.values())
    avg = s / n if n else None
    std = math.sqrt(max(0.0, (ss - s * s / n) / (n - 1))) if n > 1 else None
    cvs, gaps = [], []
    for race, p in per_race.items():
        if p[4] >= 15:                                   # within-race consistency (coefficient of variation, %)
            m = p[5] / p[4]
            cvs.append(math.sqrt(max(0.0, p[6] / p[4] - m * m)) / m * 100.0)
        if p[4] >= 5:                                    # how close the driver's best lap was to the race's best lap
            gaps.append((p[2] / base[race]["fastest"] - 1.0) * 100.0)
    emit(drv, len(per_race), laps, led, fast, slow, n, avg, std, max(p[8] for p in per_race.values()) or None,
         (sr / n) if n else None, mean(cvs), mean(gaps), len(cvs))
