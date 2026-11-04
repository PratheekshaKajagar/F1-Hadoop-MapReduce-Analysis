#!/usr/bin/env python3
"""JOB 4 - Qualifying vs race.  Input: /f1/results.  Side file: qualifying.csv (map-side join on raceId+driverId).
   Emits each race entry under THREE keys: DRIVER|id, GRIDSLOT|n, GLOBAL|ALL."""
import sys
from common import *

qual = {(int(r[1]), int(r[2])): integer(r[4]) for r in csv_rows("qualifying.csv")}   # columns: qualifyId,raceId,driverId,constructorId,position,q1_sec,...
for line in sys.stdin:
    f = line.rstrip("\n").split(",")
    if is_header(f): continue
    race, drv = int(f[1]), int(f[2])
    grid, pos, order, classified = integer(f[4]), integer(f[5]), int(f[6]), f[15]
    q = qual.get((race, drv))
    v = "%s\t%s\t%d\t%s\t%s" % ("" if grid is None else grid, "" if pos is None else pos, order, classified, "" if q is None else q)
    print("DRIVER|%d\t%s" % (drv, v))
    if grid and grid > 0:
        print("GRIDSLOT|%02d\t%s" % (grid, v))
    print("GLOBAL|ALL\t%s" % v)
