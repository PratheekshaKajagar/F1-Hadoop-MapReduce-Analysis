#!/usr/bin/env python3
"""JOB 5 - REDUCE.  Output: team scope n_stops n_valid races avg_sec median_sec fastest_sec std_sec avg_rel_pct slow_stop_pct invalid_stops"""
import sys
from common import *

for key, rows in groups(sys.stdin):
    team, scope = key.split("|")
    races = set(); valid, rel = [], []; slow = inval = 0
    for r in rows:
        races.add(r[0])
        if r[2] == "1":
            valid.append(float(r[1])); rel.append(float(r[4]))
            slow += int(r[3])
        else:
            inval += 1
    emit(team, scope, len(rows), len(valid), len(races), mean(valid), median(valid), min(valid) if valid else None, stdev(valid),
         mean(rel), 100.0 * slow / len(valid) if valid else None, inval)
