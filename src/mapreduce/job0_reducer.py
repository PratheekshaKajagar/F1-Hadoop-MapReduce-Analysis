#!/usr/bin/env python3
"""JOB 0 - REDUCE (one call per race): robust race-pace baseline.
   racing laps = lap>=2, not a pit in/out lap, time <= 125% of race fastest lap (removes SC / VSC / red-flag laps)
   baseline    = median of racing laps ; representative laps = racing laps <= 107% of baseline
   pit_median = median of stops <= 60 s (red-flag stops last minutes)
   Output: raceId n_laps n_drivers fastest baseline_median n_racing n_rep n_pit pit_median usable"""
import sys
from common import *

for race, rows in groups(sys.stdin):
    laps = [(int(r[1]), int(r[2]), float(r[3]), int(r[4])) for r in rows if r[0] == "L"]
    pits = [float(r[1]) for r in rows if r[0] == "P"]
    if not laps:
        continue
    fastest = min(l[2] for l in laps)
    racing = [l[2] for l in laps if l[1] >= 2 and l[3] == 0 and l[2] <= RACING_FACTOR * fastest]
    base = median(racing) if racing else median([l[2] for l in laps])
    n_rep = sum(1 for t in racing if t <= REP_FACTOR * base)
    drivers = len(set(l[0] for l in laps))
    usable = 1 if n_rep >= MIN_REP_LAPS_USABLE else 0
    normal_pits = [d for d in pits if d <= PIT_NORMAL_MAX]      # stops > 60 s = red-flag / repair events, would distort the median
    emit(race, len(laps), drivers, fastest, base, len(racing), n_rep, len(pits), median(normal_pits) if normal_pits else None, usable)
