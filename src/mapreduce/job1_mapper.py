#!/usr/bin/env python3
"""JOB 1 - Driver performance.  MAP over lap-level records (in-mapper combining).
   Side files: race_baseline.tsv (output of Job 0), pitstops.csv.
   Emits per (driver, race) partial sums -> key = driverId."""
import sys
from common import *

base = load_baseline()
pit = load_pit_laps()
acc = {}   # (driver, race) -> [n_all, led, min_all, max_all, n_rep, sum_sec, sumsq_sec, sum_rel, max_rep]

for line in sys.stdin:
    f = line.rstrip("\n").split(",")
    if is_header(f):
        continue
    race, drv, lap, pos, sec = int(f[0]), int(f[1]), int(f[2]), integer(f[3]), float(f[4])
    b = base.get(race)
    if b is None:
        continue
    a = acc.get((drv, race))
    if a is None:
        a = acc[(drv, race)] = [0, 0, 1e18, 0.0, 0, 0.0, 0.0, 0.0, 0.0]
    a[0] += 1
    if pos == 1:
        a[1] += 1
    if sec < a[2]: a[2] = sec
    if sec > a[3]: a[3] = sec
    if b["usable"] and lap >= 2 and (race, drv, lap) not in pit and sec <= REP_FACTOR * b["median"]:
        a[4] += 1; a[5] += sec; a[6] += sec * sec
        a[7] += (sec / b["median"] - 1.0) * 100.0
        if sec > a[8]: a[8] = sec

for (drv, race), a in acc.items():          # in-mapper combiner output
    print("%d\t%d\t%d\t%d\t%.3f\t%.3f\t%d\t%.4f\t%.4f\t%.4f\t%.3f" % (drv, race, a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7], a[8]))
