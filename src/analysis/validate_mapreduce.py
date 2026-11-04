#!/usr/bin/env python3
"""VERIFICATION ONLY (not part of the pipeline): recompute selected metrics straight from the cleaned CSVs with pandas and
compare with the MapReduce output.  Proves the Hadoop jobs compute what they claim.  Writes results/validation_report.txt"""
import sys, os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mapreduce"))
from schemas import SCHEMAS, load_job6
C, M = "data/clean/", "results/mapreduce/"
def mr(name, key=None): return pd.read_csv(M + name + ".tsv", sep="\t", header=None, names=SCHEMAS[key or name], na_values=[""])
out = []; ok_all = True
def check(label, a, b, tol=1e-3):
    global ok_all
    d = float(np.nanmax(np.abs(np.asarray(a, float) - np.asarray(b, float)))) if len(a) else 0.0
    ok = d <= tol; ok_all &= ok
    out.append(f"[{'PASS' if ok else 'FAIL'}] {label:62s} max|diff| = {d:.6f}  (n={len(a)})")

laps = pd.read_csv(C + "laps/laps.csv"); res = pd.read_csv(C + "results/results.csv"); sp = pd.read_csv(C + "sprint_results/sprint_results.csv")
races = pd.read_csv(C + "races/races.csv"); con = pd.read_csv(C + "constructors/constructors.csv")
res = res.merge(races[["raceId", "year", "circuitId"]], on="raceId").merge(con[["constructorId", "team_group"]], on="constructorId")

# Job 1: laps / laps led / fastest / slowest per driver
j1 = mr("job1_driver_performance").set_index("driverId").sort_index()
g = laps.groupby("driverId").agg(n=("lap", "size"), led=("position", lambda s: (s == 1).sum()), fast=("lap_time_sec", "min"), slow=("lap_time_sec", "max")).sort_index()
check("Job1 total laps per driver", j1.laps_total.values, g.n.values, 0)
check("Job1 laps led per driver", j1.laps_led.values, g.led.values, 0)
check("Job1 fastest lap per driver", j1.fastest_lap_sec.values, g.fast.values, 1e-3)
check("Job1 slowest lap per driver", j1.slowest_lap_sec.values, g.slow.values, 1e-3)
out.append(f"       total laps in Job1 output = {int(j1.laps_total.sum())}  vs cleaned laps.csv rows = {len(laps)}")

# Job 2: team points / wins / podiums (ALL scope)
j2 = mr("job2_constructor_perf"); j2a = j2[j2.scope.astype(str) == "ALL"].set_index("team").sort_index()
pts = res.groupby("team_group").points.sum().add(sp.merge(con, on="constructorId").groupby("team_group").points.sum(), fill_value=0).sort_index()
check("Job2 career points per team (GP+sprint)", j2a.points_total.values, pts.values, 1e-6)
check("Job2 career wins per team", j2a.wins.values, res[res.positionOrder == 1].groupby("team_group").size().reindex(j2a.index).fillna(0).values, 0)
check("Job2 career podiums per team", j2a.podiums.values, res[res.positionOrder <= 3].groupby("team_group").size().reindex(j2a.index).fillna(0).values, 0)
check("Job2 avg grid per team", j2a.avg_grid.values, res[res.grid > 0].groupby("team_group").grid.mean().reindex(j2a.index).values, 1e-3)

# Job 4: per-driver average finish & avg gain
j4 = mr("job4_qualifying_vs_race"); j4d = j4[j4.rtype == "DRIVER"].copy(); j4d["key"] = j4d.key.astype(int); j4d = j4d.set_index("key").sort_index()
cl = res[(res.classified == 1) & (res.grid > 0)].copy(); cl["gain"] = cl.grid - cl.position
check("Job4 avg finish (all entries) per driver", j4d.avg_finish_all.values, res.groupby("driverId").positionOrder.mean().reindex(j4d.index).values, 1e-3)
check("Job4 avg positions gained per driver", j4d.avg_gain_vs_grid.values, cl.groupby("driverId").gain.mean().reindex(j4d.index).values, 1e-3)
qq = pd.read_csv(C + "qualifying/qualifying.csv")[["raceId", "driverId", "position"]].rename(columns={"position": "qpos"})
rq = res.merge(qq, on=["raceId", "driverId"], how="left")
check("Job4 avg qualifying position per driver", j4d.avg_qual_pos.values, rq.groupby("driverId").qpos.mean().reindex(j4d.index).values, 1e-3)
cq = rq[(rq.classified == 1) & (rq.grid > 0) & rq.qpos.notna()]
check("Job4 avg (qualifying - finish) per driver", j4d.avg_gain_vs_quali.values, (cq.qpos - cq.position).groupby(cq.driverId).mean().reindex(j4d.index).values, 1e-3)
check("Job2 not-classified count per team", j2a.not_classified.values, res[res.classified == 0].groupby("team_group").size().reindex(j2a.index).fillna(0).values, 0)
check("Job2 avg classified finish per team", j2a.avg_finish_classified.values, res[res.classified == 1].groupby("team_group").position.mean().reindex(j2a.index).values, 1e-3)
gl = j4[j4.rtype == "GLOBAL"].iloc[0]
out.append(f"       Job4 global grid-vs-finish Pearson r = {gl.corr_grid_finish:.4f}  (pandas: {np.corrcoef(cl.grid, cl.position)[0,1]:.4f})")
check("Job4 global correlation", [gl.corr_grid_finish], [np.corrcoef(cl.grid, cl.position)[0, 1]], 1e-3)

# Job 5: pit-stop counts per team
p = pd.read_csv(C + "pitstops/pitstops.csv")
j5 = mr("job5_pitstop_performance"); j5a = j5[(j5.scope.astype(str) == "ALL") & (j5.team != "FIELD")].set_index("team").sort_index()
t = p.merge(res[["raceId", "driverId", "team_group"]], on=["raceId", "driverId"])
check("Job5 total pit stops per team", j5a.n_stops.values, t.groupby("team_group").size().reindex(j5a.index).values, 0)
fld = j5[(j5.team == "FIELD") & (j5.scope.astype(str) == "ALL")].iloc[0]
# independent re-implementation of the Job 5 validity rule in pandas
rm = p[p.duration_sec <= 60].groupby("raceId").duration_sec.median().rename("rmed")
vp = p.merge(rm, on="raceId", how="left").merge(res[["raceId", "driverId", "team_group"]], on=["raceId", "driverId"])
vp = vp[(vp.duration_sec >= 10) & (vp.duration_sec <= 3 * vp.rmed)]
check("Job5 valid stop count per team", j5a.n_valid.values, vp.groupby("team_group").size().reindex(j5a.index).values, 0)
check("Job5 mean valid stop time per team", j5a.avg_sec.values, vp.groupby("team_group").duration_sec.mean().reindex(j5a.index).values, 1e-3)
check("Job5 fastest stop per team", j5a.fastest_sec.values, vp.groupby("team_group").duration_sec.min().reindex(j5a.index).values, 1e-3)
out.append(f"       Job5 FIELD total stops={int(fld.n_stops)} (cleaned pitstops.csv rows={len(p)}), valid={int(fld.n_valid)}")

# Job 6: season totals vs official standings (computed points must equal official except documented penalties)
tm = load_job6()["TEAM"].copy()
for c in ["year", "points_gp", "final_points"]: tm[c] = pd.to_numeric(tm[c], errors="coerce")
sprint_pts = j2[j2.scope.astype(str) != "ALL"].copy(); sprint_pts["year"] = sprint_pts.scope.astype(int)
tm = tm.merge(sprint_pts[["team", "year", "points_sprint"]], on=["team", "year"], how="left").fillna({"points_sprint": 0})
tm["diff"] = tm.final_points - (tm.points_gp + tm.points_sprint)
bad = tm[tm["diff"].abs() > 0.01]
out.append(f"       Job6 official final standings vs (Job6 GP points + Job2 sprint points), {len(tm)} team-seasons:")
for _, r in bad.iterrows(): out.append(f"          MISMATCH {int(r.year)} {r.team}: official {r.final_points:.0f} vs computed {r.points_gp + r.points_sprint:.0f}  (diff {r['diff']:+.0f})")
out.append("          -> expected exactly 2 mismatches = real FIA penalties: Force India 2018 (-59, team restructured mid-season) and Racing Point 2020 (-15, brake-duct case)")
check("Job6+Job2 reproduce official standings points (all but 2 penalised team-seasons)", [len(bad)], [2], 0)
open("results/validation_report.txt", "w").write("\n".join(out) + "\n\nOVERALL: " + ("ALL CHECKS PASSED" if ok_all else "SOME CHECKS FAILED") + "\n")
print("\n".join(out)); print("OVERALL:", "ALL CHECKS PASSED" if ok_all else "SOME CHECKS FAILED")
