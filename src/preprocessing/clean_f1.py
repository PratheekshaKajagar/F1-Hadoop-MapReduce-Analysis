#!/usr/bin/env python3
"""
STAGE 1 - Data cleaning / preprocessing (Python + Pandas)

Input : raw Ergast/Jolpica-style CSVs (data/raw)
Output: cleaned, season-filtered (2018-2025) CSVs laid out exactly like the HDFS tree (data/clean/<entity>/)
Also writes results/data_quality_report.json documenting every cleaning action.

Pandas is used ONLY for cleaning here. All aggregation/analytics is done later by Hadoop MapReduce.
Real column names were inspected first (see docs/DATASET_INSPECTION.md).
"""
import json, os, re, sys
import numpy as np
import pandas as pd

RAW = sys.argv[1] if len(sys.argv) > 1 else "data/raw"
OUT = sys.argv[2] if len(sys.argv) > 2 else "data/clean"
REPORT = sys.argv[3] if len(sys.argv) > 3 else "results/data_quality_report.json"
Y0, Y1 = 2018, 2025
NA = ["\\N", "", "NA", "NaN"]

report = {"season_range": [Y0, Y1], "tables": {}}


def read(name):
    return pd.read_csv(os.path.join(RAW, name + ".csv"), na_values=NA, keep_default_na=False)


def save(df, entity, fname):
    d = os.path.join(OUT, entity)
    os.makedirs(d, exist_ok=True)
    # Hadoop Streaming splits on ',' -> guarantee no embedded commas / tabs / newlines in text fields
    for c in df.select_dtypes(exclude="number").columns:
        df[c] = df[c].astype(str).str.replace(r"[,\t\r\n\"]", " ", regex=True).str.strip().replace({"nan": "", "<NA>": ""})
    df.to_csv(os.path.join(d, fname), index=False, na_rep="", float_format="%.3f")
    return len(df)


def log(table, **kw):
    report["tables"].setdefault(table, {}).update(kw)


def time_to_sec(s):
    """'1:26.572' -> 86.572 ; '49.111' -> 49.111 ; NaN -> NaN"""
    if pd.isna(s):
        return np.nan
    s = str(s).strip()
    m = re.fullmatch(r"(?:(\d+):)?(\d+(?:\.\d+)?)", s)
    if not m:
        return np.nan
    return (int(m.group(1)) * 60 if m.group(1) else 0) + float(m.group(2))


def to_int(s):
    return pd.to_numeric(s, errors="coerce").astype("Int64")


# ---------------------------------------------------------------- races
races = read("races")
n0 = len(races)
races = races.drop_duplicates("raceId")
races["year"] = to_int(races["year"])
races = races[(races.year >= Y0) & (races.year <= Y1)].copy()
races["date"] = pd.to_datetime(races["date"], errors="coerce").dt.strftime("%Y-%m-%d")
races["round"] = to_int(races["round"])
# --- track LAYOUT ids: several circuits changed layout during 2018-2025 (verified in the data: fastest-lap jumps of 5-15 %).
#     Lap times of different layouts must never be averaged together, so each (circuit, layout) gets its own layoutId.
#     default layout: layoutId = circuitId ; variants: layoutId = 1000 * k + circuitId
circ_ref = read("circuits").set_index("circuitId")["circuitRef"].to_dict()
def layout_of(row):
    ref, y, nm = circ_ref[row.circuitId], row.year, row["name"]
    if ref == "bahrain" and "Sakhir" in nm:      return 1, "outer layout (2020 Sakhir GP)"
    if ref == "yas_marina" and y <= 2020:        return 1, "pre-2021 layout"
    if ref == "albert_park" and y <= 2019:       return 1, "pre-2022 layout"
    if ref == "catalunya" and y <= 2022:         return 1, "pre-2023 layout (final chicane)"
    if ref == "marina_bay" and y <= 2022:        return 1, "pre-2023 layout"
    return 0, ""
lay = races.apply(layout_of, axis=1, result_type="expand"); races["layout_k"], races["layout_label"] = lay[0], lay[1]
races["layoutId"] = races["layout_k"] * 1000 + races["circuitId"]
races = races[["raceId", "year", "round", "circuitId", "name", "date", "layoutId"]].sort_values(["year", "round"]) if False else races
layout_rows = races[races.layout_k > 0][["layoutId", "circuitId", "layout_label"]].drop_duplicates("layoutId")
races = races[["raceId", "year", "round", "circuitId", "name", "date", "layoutId"]].sort_values(["year", "round"])
race_ids = set(races.raceId)
log("races", raw_rows=n0, clean_rows=save(races, "races", "races.csv"), missing_dates=int(races.date.isna().sum()))

# ---------------------------------------------------------------- circuits
circ = read("circuits")
circ = circ[circ.circuitId.isin(set(races.circuitId))].drop_duplicates("circuitId")
circ = circ[["circuitId", "circuitRef", "name", "location", "country", "lat", "lng"]].copy()
circ.insert(0, "layoutId", circ["circuitId"])
variants = layout_rows.merge(circ.drop(columns="layoutId"), on="circuitId")
variants["layoutId_"] = variants["layoutId"]; variants["name"] = variants["name"] + " (" + variants["layout_label"] + ")"
variants = variants[["layoutId_", "circuitId", "circuitRef", "name", "location", "country", "lat", "lng"]].rename(columns={"layoutId_": "layoutId"})
circ = pd.concat([circ, variants], ignore_index=True)
log("circuits", clean_rows=save(circ, "circuits", "circuits.csv"), layout_variants=int(len(variants)))

# ---------------------------------------------------------------- results
res = read("results")
status = read("status").rename(columns={"status": "status_text"})
n0 = len(res)
res = res[res.raceId.isin(race_ids)]
n_scope = len(res)
res = res.drop_duplicates(["raceId", "driverId"])
dups = n_scope - len(res)
for c in ["grid", "position", "positionOrder", "laps", "rank", "fastestLap", "statusId", "milliseconds"]:
    res[c] = to_int(res[c])
for c in ["points", "fastestLapSpeed"]:
    res[c] = pd.to_numeric(res[c], errors="coerce")
res["fastestLapTime_sec"] = res["fastestLapTime"].map(time_to_sec)
res = res.merge(status, on="statusId", how="left")
# classified = official finishing position exists (retirements/DSQ have no 'position')
# SOURCE INCONSISTENCY found during inspection: in 2025 rows `position` is filled even for retirements (positionText = R/D/W),
# while 2018-2024 leave it empty. positionText is consistent in all seasons: numeric = classified, R/D/W/N = not classified.
res["position"] = pd.to_numeric(res["positionText"], errors="coerce").astype("Int64")
res["classified"] = res["position"].notna().astype(int)
# gap to winner in seconds: '+5.036' -> 5.036 ; winner -> 0 ; lapped ('+1 Lap') -> missing (not comparable)
def gap(row):
    t = row["time"]
    if row["positionOrder"] == 1 and pd.notna(row["milliseconds"]):
        return 0.0
    if isinstance(t, str) and t.startswith("+") and re.fullmatch(r"\+[\d:.]+", t):
        return time_to_sec(t[1:])
    return np.nan
res["gap_to_winner_sec"] = res.apply(gap, axis=1)
res["year_check"] = res.merge(races[["raceId", "year"]], on="raceId", how="left")["year"].values
res = res[["resultId", "raceId", "driverId", "constructorId", "grid", "position", "positionOrder", "points", "laps",
           "fastestLap", "rank", "fastestLapTime_sec", "fastestLapSpeed", "statusId", "status_text", "classified",
           "gap_to_winner_sec"]]
log("results", raw_rows_all_years=n0, rows_in_scope=n_scope, duplicates_removed=int(dups), clean_rows=save(res, "results", "results.csv"),
    grid_missing_kept_blank=int(res.grid.isna().sum()), pit_lane_starts_grid0=int((res.grid == 0).sum()),
    not_classified=int((res.classified == 0).sum()), position_rule="classified <=> positionText is numeric (2025 source fills position for retirees)", fastest_speed_missing=int(res.fastestLapSpeed.isna().sum()))

# ---------------------------------------------------------------- sprint results
sp = read("sprint_results")
sp = sp[sp.raceId.isin(race_ids)].drop_duplicates(["raceId", "driverId"])
sp["position"] = pd.to_numeric(sp["positionText"], errors="coerce").astype("Int64")   # same rule as race results
for c in ["grid", "positionOrder", "laps"]:
    sp[c] = to_int(sp[c])
sp["points"] = pd.to_numeric(sp["points"], errors="coerce")
sp = sp[["resultId", "raceId", "driverId", "constructorId", "grid", "position", "positionOrder", "points", "laps"]]
log("sprint_results", clean_rows=save(sp, "sprint_results", "sprint_results.csv"))

# ---------------------------------------------------------------- drivers / constructors (clean IDs)
drv = read("drivers")
used_drivers = set(res.driverId) | set(sp.driverId)
drv = drv[drv.driverId.isin(used_drivers)].drop_duplicates("driverId").copy()
drv["driverRef"] = drv["driverRef"].str.lower().str.strip()
drv["forename"] = drv["forename"].str.strip(); drv["surname"] = drv["surname"].str.strip()
drv["full_name"] = drv["forename"] + " " + drv["surname"]
drv["dob"] = pd.to_datetime(drv["dob"], errors="coerce").dt.strftime("%Y-%m-%d")
drv = drv[["driverId", "driverRef", "code", "forename", "surname", "full_name", "nationality", "dob"]]
log("drivers", clean_rows=save(drv, "drivers", "drivers.csv"))

# constructor lineage: the same team entity raced under different names in 2018-2025.
TEAM_GROUP = {
    "red_bull": "Red Bull", "mercedes": "Mercedes", "ferrari": "Ferrari", "mclaren": "McLaren",
    "williams": "Williams", "haas": "Haas",
    "renault": "Alpine (Renault)", "alpine": "Alpine (Renault)",
    "toro_rosso": "RB (Toro Rosso/AlphaTauri)", "alphatauri": "RB (Toro Rosso/AlphaTauri)", "rb": "RB (Toro Rosso/AlphaTauri)",
    "force_india": "Aston Martin (Force India)", "racing_point": "Aston Martin (Force India)", "aston_martin": "Aston Martin (Force India)",
    "sauber": "Sauber (Alfa Romeo)", "alfa": "Sauber (Alfa Romeo)",
}
con = read("constructors")
con = con[con.constructorId.isin(set(res.constructorId) | set(sp.constructorId))].drop_duplicates("constructorId").copy()
con["constructorRef"] = con["constructorRef"].str.lower().str.strip()
con["team_group"] = con["constructorRef"].map(TEAM_GROUP)
assert con.team_group.notna().all(), con[con.team_group.isna()]
con = con[["constructorId", "constructorRef", "name", "nationality", "team_group"]]
log("constructors", clean_rows=save(con, "constructors", "constructors.csv"), lineage_groups=int(con.team_group.nunique()))

# ---------------------------------------------------------------- qualifying
q = read("qualifying")
q = q[q.raceId.isin(race_ids)]
n_scope = len(q)
q = q.drop_duplicates(["raceId", "driverId"])
q["position"] = to_int(q["position"])
for c in ["q1", "q2", "q3"]:
    q[c + "_sec"] = q[c].map(time_to_sec)
q = q[["qualifyId", "raceId", "driverId", "constructorId", "position", "q1_sec", "q2_sec", "q3_sec"]]
log("qualifying", rows_in_scope=n_scope, clean_rows=save(q, "qualifying", "qualifying.csv"),
    q2_missing_eliminated_in_Q1=int(q.q2_sec.isna().sum()), q3_missing=int(q.q3_sec.isna().sum()),
    note="missing Q2/Q3 are structural (driver eliminated) -> NOT imputed")

# ---------------------------------------------------------------- laps (the big table)
lap = pd.read_csv(os.path.join(RAW, "lap_times.csv"), na_values=NA, keep_default_na=False)
n0 = len(lap)
lap = lap[lap.raceId.isin(race_ids)]
n_scope = len(lap)
lap = lap.drop_duplicates(["raceId", "driverId", "lap"])
dups = n_scope - len(lap)
lap["lap_time_sec"] = lap["milliseconds"].astype(float) / 1000.0
chk = lap["time"].map(time_to_sec)
mismatch = int(((chk - lap.lap_time_sec).abs() > 0.002).sum())
lap = lap.dropna(subset=["lap_time_sec"])
lap["position"] = to_int(lap["position"])
lap = lap[["raceId", "driverId", "lap", "position", "lap_time_sec"]].sort_values(["raceId", "driverId", "lap"])
log("laps", raw_rows_all_years=n0, rows_in_scope=n_scope, duplicates_removed=int(dups),
    string_vs_ms_mismatches=mismatch, clean_rows=save(lap, "laps", "laps.csv"),
    races_covered=int(lap.raceId.nunique()), min_sec=float(lap.lap_time_sec.min()), max_sec=float(lap.lap_time_sec.max()))

# ---------------------------------------------------------------- pit stops
p = read("pit_stops")
p = p[p.raceId.isin(race_ids)]
n_scope = len(p)
p = p.drop_duplicates(["raceId", "driverId", "stop"])
dur_str = p["duration"].map(time_to_sec)           # handles '1:03.2' style values
ms_sec = pd.to_numeric(p["milliseconds"], errors="coerce") / 1000.0
log("pitstops", ms_null_filled_from_duration_string=int(ms_sec.isna().sum()),
    ms_vs_duration_disagreements=int(((ms_sec - dur_str).abs() > 0.002).sum()))
p["duration_sec"] = ms_sec.fillna(dur_str)
p = p.dropna(subset=["duration_sec"])
p = p[["raceId", "driverId", "stop", "lap", "duration_sec"]]
log("pitstops", rows_in_scope=n_scope, clean_rows=save(p, "pitstops", "pitstops.csv"),
    races_without_pit_data=sorted(race_ids - set(p.raceId)),
    note="durations are pit-LANE time; red-flag stops (minutes long) are kept raw and filtered inside Hadoop job")

# ---------------------------------------------------------------- standings
ds = read("driver_standings"); ds = ds[ds.raceId.isin(race_ids)].drop_duplicates(["raceId", "driverId"])
ds["position"] = to_int(ds["position"]); ds["wins"] = to_int(ds["wins"]); ds["points"] = pd.to_numeric(ds["points"], errors="coerce")
log("driver_standings", position_missing=int(ds.position.isna().sum()))
ds = ds[["raceId", "driverId", "points", "position", "wins"]]
cs = read("constructor_standings"); cs = cs[cs.raceId.isin(race_ids)].drop_duplicates(["raceId", "constructorId"])
cs["position"] = to_int(cs["position"]); cs["wins"] = to_int(cs["wins"]); cs["points"] = pd.to_numeric(cs["points"], errors="coerce")
log("constructor_standings", position_missing=int(cs.position.isna().sum()))
cs = cs[["raceId", "constructorId", "points", "position", "wins"]]
log("driver_standings", clean_rows=save(ds, "standings", "driver_standings.csv"))
log("constructor_standings", clean_rows=save(cs, "standings", "constructor_standings.csv"))

# ---------------------------------------------------------------- referential integrity checks
checks = {
    "results.raceId in races": bool(res.raceId.isin(races.raceId).all()),
    "results.driverId in drivers": bool(res.driverId.isin(drv.driverId).all()),
    "results.constructorId in constructors": bool(res.constructorId.isin(con.constructorId).all()),
    "laps.driverId in drivers": bool(lap.driverId.isin(drv.driverId).all()),
    "pitstops.driverId in drivers": bool(p.driverId.isin(drv.driverId).all()),
    "qualifying.driverId in drivers": bool(q.driverId.isin(drv.driverId).all()),
}
report["integrity_checks"] = checks
assert all(checks.values()), checks
os.makedirs(os.path.dirname(REPORT), exist_ok=True)
json.dump(report, open(REPORT, "w"), indent=2, default=str)
print(json.dumps(report, indent=2, default=str))
