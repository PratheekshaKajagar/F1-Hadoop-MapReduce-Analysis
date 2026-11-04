#!/usr/bin/env python3
"""JOB 3 - Circuit performance.  Inputs: /f1/laps + /f1/results (told apart by input path).
   Side files: races.csv, race_baseline.tsv, pitstops.csv.   MAP: key = layoutId (circuit + track-layout version)."""
import sys
from common import *

races = load_races(); path = input_file()
if "/laps/" in path:
    base = load_baseline(); pit = load_pit_laps()
    acc = {}   # (race, driver) -> [n_rep, sum_sec, sum_rel, min_all]
    for line in sys.stdin:
        f = line.rstrip("\n").split(",")
        if is_header(f): continue
        race, drv, lap, sec = int(f[0]), int(f[1]), int(f[2]), float(f[4])
        b = base[race]
        a = acc.setdefault((race, drv), [0, 0.0, 0.0, 1e18])
        if sec < a[3]: a[3] = sec
        if b["usable"] and lap >= 2 and (race, drv, lap) not in pit and sec <= REP_FACTOR * b["median"]:
            a[0] += 1; a[1] += sec; a[2] += (sec / b["median"] - 1) * 100
    for (race, drv), a in acc.items():
        print("%d\tL\t%d\t%d\t%d\t%.4f\t%.4f\t%.3f" % (races[race][2], race, drv, a[0], a[1], a[2], a[3]))
else:                                           # results: resultId,raceId,driverId,constructorId,grid,position,positionOrder,points,laps,fastestLap,rank,flTime,flSpeed,statusId,status,classified,gap
    for line in sys.stdin:
        f = line.rstrip("\n").split(",")
        if is_header(f): continue
        race = int(f[1])
        print("%d\tR\t%d\t%s\t%s\t%s\t%s\t%s\t%s" % (races[race][2], race, f[4], f[5], f[6], f[15], f[12], f[16]))
