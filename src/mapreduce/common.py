"""
Shared helpers for the Hadoop Streaming mappers/reducers (pure Python standard library - NO pandas).

Side tables (races, constructors, ...) are small dimension tables shipped to every task with
Hadoop's Distributed Cache (`-files`) and loaded into memory = classic MAP-SIDE (replicated) JOIN.
Files appear in the task's working directory under their base name.
"""
import math
import os
import sys

REP_FACTOR = 1.07        # a "representative" lap is within 107 % of the race's median racing lap
RACING_FACTOR = 1.25     # laps slower than 125 % of the fastest lap are treated as SC / VSC / red-flag laps
PIT_NORMAL_MAX = 60.0     # pit-lane times above 60 s are red-flag / repair events, not normal pit stops
MIN_REP_LAPS_USABLE = 200  # a race needs >= 200 representative laps (all drivers together) to be used for pace stats


def num(s):
    """string -> float or None (blank / invalid)."""
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def integer(s):
    v = num(s)
    return None if v is None else int(v)


def fmt(x, nd=4):
    """format a value for TSV output; None -> blank."""
    if x is None:
        return ""
    if isinstance(x, float):
        if math.isnan(x):
            return ""
        return ("%." + str(nd) + "f") % x
    return str(x)


def emit(*fields):
    sys.stdout.write("\t".join(fmt(f) for f in fields) + "\n")


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def stdev(xs):
    xs = list(xs)
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    if n == 0:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0 or syy == 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def input_file():
    """Name of the HDFS file the current map task is reading (Hadoop sets this env var)."""
    return os.environ.get("mapreduce_map_input_file", os.environ.get("map_input_file", ""))


def csv_rows(path):
    """Iterate rows of a (header + comma separated) side table."""
    with open(path) as fh:
        fh.readline()
        for line in fh:
            yield line.rstrip("\n").split(",")


def is_header(fields):
    return not fields[0].isdigit()


def load_races(path="races.csv"):
    """raceId -> (year, round, layoutId)   [layoutId = circuit + track-layout version, see preprocessing]"""
    return {int(r[0]): (int(r[1]), int(r[2]), int(r[6])) for r in csv_rows(path)}


def load_team_group(path="constructors.csv"):
    """constructorId -> team lineage name"""
    return {int(r[0]): r[4] for r in csv_rows(path)}


def load_baseline(path="race_baseline.tsv"):
    """Output of Job 0 (itself a MapReduce result!) -> raceId -> dict"""
    out = {}
    with open(path) as fh:
        for line in fh:
            p = line.rstrip("\n").split("\t")
            out[int(p[0])] = {
                "n_laps": int(p[1]), "n_drivers": int(p[2]), "fastest": float(p[3]), "median": float(p[4]),
                "n_racing": int(p[5]), "n_rep": int(p[6]), "n_pit": int(p[7]),
                "pit_median": num(p[8]), "usable": p[9] == "1",
            }
    return out


def load_pit_laps(path="pitstops.csv"):
    """set of (raceId, driverId, lap) that are pit IN-laps or OUT-laps (distorted lap times)."""
    s = set()
    for r in csv_rows(path):
        race, drv, lap = int(r[0]), int(r[1]), int(r[3])
        s.add((race, drv, lap))
        s.add((race, drv, lap + 1))
    return s


def groups(stream):
    """Yield (key, [value_fields...]) for consecutive identical keys (input is sorted by Hadoop's shuffle)."""
    cur, buf = None, []
    for line in stream:
        line = line.rstrip("\n")
        k, _, v = line.partition("\t")
        if k != cur:
            if cur is not None:
                yield cur, buf
            cur, buf = k, []
        buf.append(v.split("\t"))
    if cur is not None:
        yield cur, buf
