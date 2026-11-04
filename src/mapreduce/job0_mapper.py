#!/usr/bin/env python3
"""JOB 0 - Race baseline.  MAP: key = raceId.  Inputs: /f1/laps and /f1/pitstops (distinguished by input path).
Side file (distributed cache): pitstops.csv -> used to flag pit in/out laps."""
import sys
from common import *

path = input_file()
pit_laps = load_pit_laps() if "/laps/" in path else set()

for line in sys.stdin:
    f = line.rstrip("\n").split(",")
    if is_header(f):
        continue
    if "/laps/" in path:                       # raceId,driverId,lap,position,lap_time_sec
        race, drv, lap, sec = int(f[0]), int(f[1]), int(f[2]), float(f[4])
        pl = 1 if (race, drv, lap) in pit_laps else 0
        print("%d\tL\t%d\t%d\t%.3f\t%d" % (race, drv, lap, sec, pl))
    elif "/pitstops/" in path:                 # raceId,driverId,stop,lap,duration_sec
        print("%s\tP\t%s" % (f[0], f[4]))
