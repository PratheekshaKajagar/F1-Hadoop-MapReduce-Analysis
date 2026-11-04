#!/usr/bin/env python3
"""JOB 6 - Seasonal performance 2018-2025.  Inputs: /f1/results, /f1/laps, /f1/standings (driver+constructor files).
   Side files: races.csv, constructors.csv, race_baseline.tsv, pitstops.csv.
   Record types (key prefix): SEASON|y, DRIVER|y|id, TEAM|y|team, CIRCYEAR|layout|y."""
import sys
from common import *

races = load_races(); path = input_file()
if "/laps/" in path:
    base = load_baseline(); pit = load_pit_laps()
    season = {}; drv_s = {}; circ = {}
    for line in sys.stdin:
        f = line.rstrip("\n").split(",")
        if is_header(f): continue
        race, drv, lap, pos, sec = int(f[0]), int(f[1]), int(f[2]), integer(f[3]), float(f[4])
        b = base[race]; year, rnd, cid = races[race]
        d = drv_s.setdefault((year, drv), [0, 0, 0.0, 0.0])      # laps, led, n_rep, sum_rel
        c = circ.setdefault((cid, year), [0, 0.0, 1e18])         # n_rep, sum_sec, min_all
        s = season.setdefault(year, [0, 0, 0.0])                 # laps, n_rep, sum_sec
        d[0] += 1; s[0] += 1
        if pos == 1: d[1] += 1
        if sec < c[2]: c[2] = sec
        if b["usable"] and lap >= 2 and (race, drv, lap) not in pit and sec <= REP_FACTOR * b["median"]:
            d[2] += 1; d[3] += (sec / b["median"] - 1) * 100
            c[0] += 1; c[1] += sec
            s[1] += 1; s[2] += sec
    for y, s in season.items():  print("SEASON|%d\tL\t%d\t%d\t%.4f" % (y, s[0], s[1], s[2]))
    for (y, d), a in drv_s.items(): print("DRIVER|%d|%d\tL\t%d\t%d\t%d\t%.4f" % (y, d, a[0], a[1], a[2], a[3]))
    for (cid, y), a in circ.items(): print("CIRCYEAR|%d|%d\tL\t%d\t%.4f\t%.3f" % (cid, y, a[0], a[1], a[2]))
elif "/standings/" in path:
    tg = load_team_group()
    is_driver = "driver_standings" in path
    for line in sys.stdin:                # raceId,driverId|constructorId,points,position,wins
        f = line.rstrip("\n").split(",")
        if is_header(f): continue
        race = int(f[0]); year, rnd, cid = races[race]
        if is_driver:
            print("DRIVER|%d|%s\tS\t%d\t%s\t%s\t%s" % (year, f[1], rnd, f[3], f[2], f[4]))
        else:
            print("TEAM|%d|%s\tS\t%d\t%s\t%s\t%s" % (year, tg[int(f[1])], rnd, f[3], f[2], f[4]))
else:                                     # results
    tg = load_team_group()
    for line in sys.stdin:
        f = line.rstrip("\n").split(",")
        if is_header(f): continue
        race, drv, con = int(f[1]), int(f[2]), int(f[3]); year = races[race][0]
        pos, order, pts, cl = integer(f[5]), int(f[6]), num(f[7]) or 0.0, f[15]
        v = "R\t%d\t%.1f\t%d\t%s\t%s" % (race, pts, order, cl, pos if pos is not None else "")
        print("DRIVER|%d|%d\t%s" % (year, drv, v))
        print("TEAM|%d|%s\t%s" % (year, tg[con], v))
        print("SEASON|%d\t%s\t%s" % (year, v, tg[con] + "\t" + str(drv)))
