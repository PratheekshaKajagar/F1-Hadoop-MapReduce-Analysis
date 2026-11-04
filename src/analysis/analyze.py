#!/usr/bin/env python3
"""
STAGE 5 - Secondary analysis & visualization (Python / Pandas / Matplotlib).

IMPORTANT: this script never touches lap-level / result-level raw data.  Its ONLY inputs are the (small) aggregated
outputs written by the Hadoop MapReduce jobs (results/mapreduce/*.tsv) plus tiny name look-up tables.
Hadoop = large-scale processing.  Python = interpretation and plots.

Outputs: figures/*.png, results/analysis/*.csv, results/analysis/insights.md, results/analysis/insights.json
"""
import json, os, sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mapreduce"))
from schemas import SCHEMAS, load_job6

M, C, FIG, OUT = "results/mapreduce/", "data/clean/", "figures/", "results/analysis/"
os.makedirs(FIG, exist_ok=True); os.makedirs(OUT, exist_ok=True)
MIN_RACES = 50                      # minimum race starts for a driver to be ranked
plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 150, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .25, "axes.titleweight": "bold", "axes.titlesize": 12, "figure.facecolor": "white"})
RED, DARK, GREY, BLUE = "#E10600", "#15151E", "#9a9aa5", "#2F6FDE"
TEAM_COL = {"Mercedes": "#00A19B", "Red Bull": "#3671C6", "Ferrari": "#E8002D", "McLaren": "#FF8000",
            "Aston Martin (Force India)": "#229971", "Alpine (Renault)": "#FF87BC", "Williams": "#37A8E0", "Haas": "#8C9196",
            "RB (Toro Rosso/AlphaTauri)": "#6C7FD8", "Sauber (Alfa Romeo)": "#52C41A"}


def mr(name):
    return pd.read_csv(M + name + ".tsv", sep="\t", header=None, names=SCHEMAS[name], na_values=[""])


def save(fig, name):
    fig.tight_layout(); fig.savefig(FIG + name); plt.close(fig); print("saved", FIG + name)


drivers = pd.read_csv(C + "drivers/drivers.csv")[["driverId", "full_name", "code"]]
circuits = pd.read_csv(C + "circuits/circuits.csv")[["layoutId", "name", "country"]]
short = {"Circuit de Spa-Francorchamps": "Spa-Francorchamps", "Autodromo Nazionale di Monza": "Monza", "Albert Park Grand Prix Circuit": "Albert Park",
         "Bahrain International Circuit": "Bahrain", "Circuit de Barcelona-Catalunya": "Barcelona", "Autódromo José Carlos Pace": "Interlagos",
         "Autódromo Hermanos Rodríguez": "Mexico City", "Circuit Gilles Villeneuve": "Montreal", "Marina Bay Street Circuit": "Marina Bay",
         "Circuit de Monaco": "Monaco", "Yas Marina Circuit": "Yas Marina", "Circuit of the Americas": "COTA", "Baku City Circuit": "Baku",
         "Jeddah Corniche Circuit": "Jeddah", "Las Vegas Strip Street Circuit": "Las Vegas", "Losail International Circuit": "Losail",
         "Miami International Autodrome": "Miami", "Shanghai International Circuit": "Shanghai", "Autodromo Enzo e Dino Ferrari": "Imola",
         "Circuit Park Zandvoort": "Zandvoort", "Silverstone Circuit": "Silverstone", "Suzuka Circuit": "Suzuka", "Sochi Autodrom": "Sochi",
         "Circuit Paul Ricard": "Paul Ricard", "Red Bull Ring": "Red Bull Ring", "Hungaroring": "Hungaroring", "Hockenheimring": "Hockenheim",
         "Istanbul Park": "Istanbul Park", "Nürburgring": "Nürburgring", "Autodromo Internazionale del Mugello": "Mugello",
         "Autódromo Internacional do Algarve": "Portimão"}
def cname(n):
    for k, v in short.items():
        if n.startswith(k):
            return v + n[len(k):].replace("(pre-2023 layout (final chicane))", "(pre-2023)").replace("(outer layout (2020 Sakhir GP))", "(2020 outer)")
    return n
circuits["label"] = circuits["name"].map(cname)

# ----------------------------------------------------------------------------------------- load MapReduce outputs
j0 = mr("job0_race_baseline")
j1 = mr("job1_driver_performance").merge(drivers, on="driverId")
j2 = mr("job2_constructor_perf")
j3 = mr("job3_circuit_performance").merge(circuits, on="layoutId")
j4 = mr("job4_qualifying_vs_race")
j5 = mr("job5_pitstop_performance")
j6 = load_job6()
j4d = j4[j4.rtype == "DRIVER"].copy(); j4d["driverId"] = j4d.key.astype(int); j4d = j4d.merge(drivers, on="driverId")
j4g = j4[j4.rtype == "GRIDSLOT"].copy(); j4g["slot"] = j4g.key.astype(int)
j4all = j4[j4.rtype == "GLOBAL"].iloc[0]
drv = j1.merge(j4d.drop(columns=["full_name", "code", "rtype", "key", "wins", "podiums"]).rename(columns={"entries": "race_starts"}), on="driverId")
drv = drv.merge(j4d[["driverId", "wins", "podiums"]], on="driverId")
ranked = drv[drv.race_starts >= MIN_RACES].copy()
ins = {}                                                      # insights, every value computed from data


def top(df, col, n=1, asc=True):
    return df.sort_values(col, ascending=asc).head(n)


# =========================================================================================== FIG 1 average finishing position
r = ranked.sort_values("avg_finish_all").head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(8.5, 5.6))
ax.barh(r.full_name, r.avg_finish_all, color=[RED if i >= len(r) - 3 else GREY for i in range(len(r))])
ax.scatter(r.avg_finish_classified, r.full_name, color=DARK, zorder=3, s=22, label="classified finishes only (excl. DNFs)")
for y, (v, n) in enumerate(zip(r.avg_finish_all, r.race_starts)): ax.text(v + .1, y, f"{v:.2f}  ({int(n)} starts)", va="center", fontsize=8)
ax.set_xlabel("Average finishing position (lower = better) - bars include retirements"); ax.set_xlim(0, r.avg_finish_all.max() * 1.35)
ax.set_title(f"Q: Who finishes highest? Average finishing position, 2018-2025 (min {MIN_RACES} starts)"); ax.legend(loc="lower right", fontsize=8)
save(fig, "01_driver_avg_finish_position.png")
ins["best_avg_finish"] = top(ranked, "avg_finish_all", 5)[["full_name", "avg_finish_all", "avg_finish_classified", "race_starts"]].round(2).to_dict("records")

# =========================================================================================== FIG 2 pace & consistency
fig, ax = plt.subplots(1, 2, figsize=(13, 5.8))
r = ranked.sort_values("avg_rel_pace_pct").head(15).iloc[::-1]
ax[0].barh(r.full_name, r.avg_rel_pace_pct, color=[RED if i >= len(r) - 3 else GREY for i in range(len(r))])
for y, v in enumerate(r.avg_rel_pace_pct): ax[0].text(v - .02, y, f"{v:+.2f}%", va="center", ha="right", fontsize=8)
ax[0].set_xlabel("Mean lap time vs. that race's median racing lap  (negative = faster than the field)")
ax[0].set_title("Q: Who has the fastest average lap times?\n(normalised per race - raw seconds are not comparable across circuits)", fontsize=10.5)
ax[0].set_xlim(r.avg_rel_pace_pct.min() * 1.35, 0.05)
a = ax[1]
a.scatter(ranked.avg_rel_pace_pct, ranked.consistency_cv_pct, s=ranked.race_starts * .9, c=BLUE, alpha=.55, edgecolor="white")
for _, x in ranked.iterrows(): a.annotate(x.code, (x.avg_rel_pace_pct, x.consistency_cv_pct), fontsize=7.5, ha="center", va="center")
a.set_xlabel("Average pace vs field (%, left = faster)"); a.set_ylabel("Lap-time variation within a race (CV %, lower = more consistent)")
a.set_title("Q: Who is most consistent - and are the fastest also consistent?\n(bubble size = race starts)", fontsize=10.5); a.invert_yaxis()
save(fig, "02_driver_pace_and_consistency.png")
ins["fastest_pace"] = top(ranked, "avg_rel_pace_pct", 5)[["full_name", "avg_rel_pace_pct"]].round(3).to_dict("records")
ins["most_consistent"] = top(ranked, "consistency_cv_pct", 5)[["full_name", "consistency_cv_pct"]].round(3).to_dict("records")
ins["least_consistent"] = top(ranked, "consistency_cv_pct", 3, asc=False)[["full_name", "consistency_cv_pct"]].round(3).to_dict("records")
ins["pace_vs_consistency_corr"] = round(float(np.corrcoef(ranked.avg_rel_pace_pct, ranked.consistency_cv_pct)[0, 1]), 3)
ins["consistency_cv_range"] = [round(float(ranked.consistency_cv_pct.min()), 3), round(float(ranked.consistency_cv_pct.max()), 3)]

# =========================================================================================== FIG 3 laps led
tot_led = int(drv.laps_led.sum()); tot_laps = int(drv.laps_total.sum())
r = drv.sort_values("laps_led", ascending=False).head(12).iloc[::-1]
fig, ax = plt.subplots(figsize=(8.5, 5.2))
ax.barh(r.full_name, r.laps_led, color=[RED if i >= len(r) - 1 else (BLUE if i >= len(r) - 3 else GREY) for i in range(len(r))])
for y, (v, n) in enumerate(zip(r.laps_led, r.laps_total)):
    ax.text(v + 20, y, f"{int(v):,}  ({v / tot_led * 100:.1f}% of all laps led)", va="center", fontsize=8)
ax.set_xlim(0, r.laps_led.max() * 1.4); ax.set_xlabel("Laps led (running P1 at the end of the lap)")
ax.set_title("Q: Who has led the most laps, 2018-2025?")
save(fig, "03_laps_led.png")
ins["laps_led_top"] = top(drv, "laps_led", 5, asc=False)[["full_name", "laps_led"]].assign(share_pct=lambda d: (d.laps_led / tot_led * 100).round(1)).to_dict("records")
ins["laps_led_total"] = tot_led; ins["total_laps_processed"] = tot_laps
ins["drivers_who_led_laps"] = int((drv.laps_led > 0).sum())

# =========================================================================================== constructor tables
c_all = j2[j2.scope.astype(str) == "ALL"].copy().sort_values("points_total", ascending=False)
c_all.to_csv(OUT + "constructor_career_2018_2025.csv", index=False)
fig, ax = plt.subplots(1, 3, figsize=(15, 5.3), gridspec_kw={"width_ratios": [1.15, .8, .8]})
cc = c_all.iloc[::-1]
ax[0].barh(cc.team, cc.points_total, color=[TEAM_COL[t] for t in cc.team])
for y, v in enumerate(cc.points_total): ax[0].text(v + 40, y, f"{v:,.0f}", va="center", fontsize=8)
ax[0].set_xlim(0, c_all.points_total.max() * 1.15); ax[0].set_title("Total points (GP + sprint)")
w = c_all.sort_values("wins", ascending=True)
ax[1].barh(w.team, w.wins, color=[TEAM_COL[t] for t in w.team]); ax[1].set_title("Grand Prix wins"); ax[1].set_yticklabels([])
for y, v in enumerate(w.wins): ax[1].text(v + .8, y, str(int(v)), va="center", fontsize=8)
f = c_all.sort_values("avg_finish_classified", ascending=False)
ax[2].barh(f.team, f.avg_finish_classified, color=[TEAM_COL[t] for t in f.team]); ax[2].set_title("Avg classified finish (lower = better)"); ax[2].set_yticklabels([])
for y, v in enumerate(f.avg_finish_classified): ax[2].text(v + .2, y, f"{v:.1f}", va="center", fontsize=8)
fig.suptitle("Q: Which constructors performed best from 2018 to 2025?", fontweight="bold", y=1.0)
save(fig, "04_constructor_career_performance.png")
ins["constructor_points"] = c_all[["team", "points_total", "wins", "podiums", "poles", "avg_finish_classified", "avg_grid", "points_per_race"]].round(2).to_dict("records")

# =========================================================================================== FIG 5 constructor points by season (official standings)
tm = j6["TEAM"].copy()
hp = tm.pivot_table(index="team", columns="year", values="final_points", aggfunc="sum").fillna(0)
hp = hp.loc[c_all.team.tolist()]
champ_t = tm[tm.final_pos == 1].set_index("year").team.to_dict()
fig, ax = plt.subplots(figsize=(11, 5.6))
im = ax.imshow(hp.values, cmap="YlOrRd", aspect="auto")
ax.set_xticks(range(hp.shape[1])); ax.set_xticklabels(hp.columns); ax.set_yticks(range(hp.shape[0])); ax.set_yticklabels(hp.index); ax.grid(False)
for i in range(hp.shape[0]):
    for k, y in enumerate(hp.columns):
        v = hp.values[i, k]; is_ch = champ_t.get(y) == hp.index[i]
        ax.text(k, i, f"{v:.0f}" if v else "-", ha="center", va="center", fontsize=8.5, fontweight="bold" if is_ch else None,
                color="white" if v > hp.values.max() * .55 else DARK)
        if is_ch: ax.add_patch(plt.Rectangle((k - .5, i - .5), 1, 1, fill=False, edgecolor=DARK, lw=2))
ax.set_title("Q: Which constructors dominated which seasons?  Official championship points (boxed = Constructors' Champion)")
fig.colorbar(im, ax=ax, label="points", shrink=.8)
save(fig, "05_constructor_points_by_season.png")
hp.to_csv(OUT + "constructor_points_by_season_official.csv")
ins["constructor_champions"] = {int(y): champ_t[y] for y in sorted(champ_t)}

# =========================================================================================== circuits
cr = j3[j3.races >= 3].copy()
cr["speed"] = cr.avg_fastest_lap_speed_kmh
j3.sort_values("avg_fastest_lap_speed_kmh", ascending=False).drop(columns=["layoutId"]).to_csv(OUT + "circuit_performance.csv", index=False)
fig, ax = plt.subplots(1, 2, figsize=(13, 5.8))
a = cr.sort_values("avg_rep_lap_sec").head(10).iloc[::-1]
ax[0].barh(a.label, a.avg_rep_lap_sec, color=BLUE); ax[0].set_xlabel("Average race lap time (s)")
for y, v in enumerate(a.avg_rep_lap_sec): ax[0].text(v + .4, y, f"{v:.1f}s", va="center", fontsize=8)
ax[0].set_title("Shortest average lap times\n(reflects track length as much as speed)", fontsize=10.5)
b = cr.sort_values("speed", ascending=False).head(10).iloc[::-1]
ax[1].barh(b.label, b.speed, color=RED); ax[1].set_xlabel("Average speed of the race's fastest laps (km/h)")
for y, v in enumerate(b.speed): ax[1].text(v + .8, y, f"{v:.0f}", va="center", fontsize=8)
ax[1].set_xlim(b.speed.min() * .9, b.speed.max() * 1.03)
ax[1].set_title("Q: Which circuits are the fastest?\nHighest average fastest-lap speed (layouts with >= 3 races)", fontsize=10.5)
save(fig, "06_circuit_lap_times_and_speed.png")
ins["circuits_shortest_lap"] = a.iloc[::-1][["label", "avg_rep_lap_sec"]].round(2).head(3).to_dict("records")
ins["circuits_fastest_speed"] = b.iloc[::-1][["label", "speed"]].round(1).head(3).to_dict("records")
ins["circuits_slowest_speed"] = cr.sort_values("speed").head(3)[["label", "speed"]].round(1).to_dict("records")

cs = j3[j3.races >= 4].copy()
fig, ax = plt.subplots(figsize=(10, 6.3))
sc = ax.scatter(cs.pace_spread_pct, cs.grid_finish_corr, s=cs.races * 35, c=cs.dnf_rate_pct, cmap="RdYlBu_r", edgecolor=DARK, alpha=.85)
for _, x in cs.iterrows(): ax.annotate(x.label, (x.pace_spread_pct, x.grid_finish_corr), fontsize=7.5, xytext=(5, 4), textcoords="offset points")
ax.set_xlabel("Pace spread between drivers (std-dev of mean lap pace within a race, %)  -> bigger = larger performance differences")
ax.set_ylabel("Correlation: grid slot vs finishing position\n(high = hard to overtake / qualifying decides)")
ax.set_title("Q: Which circuits produce the largest performance gaps - and where does qualifying matter most?\n(layouts with >= 4 races; bubble = races, colour = DNF rate %)", fontsize=10.5)
fig.colorbar(sc, label="DNF rate (%)")
save(fig, "07_circuit_performance_differences.png")
ins["circuits_largest_spread"] = cs.sort_values("pace_spread_pct", ascending=False).head(3)[["label", "pace_spread_pct"]].round(2).to_dict("records")
ins["circuits_smallest_spread"] = cs.sort_values("pace_spread_pct").head(3)[["label", "pace_spread_pct"]].round(2).to_dict("records")
ins["circuits_grid_matters_most"] = cs.sort_values("grid_finish_corr", ascending=False).head(3)[["label", "grid_finish_corr"]].round(3).to_dict("records")
ins["circuits_grid_matters_least"] = cs.sort_values("grid_finish_corr").head(3)[["label", "grid_finish_corr"]].round(3).to_dict("records")
ins["circuits_highest_dnf"] = cs.sort_values("dnf_rate_pct", ascending=False).head(3)[["label", "dnf_rate_pct"]].round(1).to_dict("records")
ins["circuits_biggest_win_margin"] = cs.sort_values("avg_winning_margin_sec", ascending=False).head(3)[["label", "avg_winning_margin_sec"]].round(1).to_dict("records")

# =========================================================================================== FIG 8 qualifying vs race
fig, ax = plt.subplots(1, 2, figsize=(13.5, 5.8))
g = j4g.sort_values("slot")
ax[0].plot([1, 20], [1, 20], "--", color=GREY, label="finish = grid (no change)")
ax[0].plot(g.slot, g.avg_finish_all, "-o", color=RED, label="average finish incl. DNFs")
ax[0].plot(g.slot, g.avg_finish_classified, "-s", color=DARK, ms=4, label="average finish, classified only")
ax[0].set_xlabel("Starting grid slot"); ax[0].set_ylabel("Average finishing position"); ax[0].xaxis.set_major_locator(MaxNLocator(integer=True))
ax[0].set_title(f"Q: Does a better grid slot mean a better finish?\nPearson r = {j4all.corr_grid_finish:.2f} over {int(j4all.n_gain_races):,} classified starts", fontsize=10.5)
ax[0].legend(fontsize=8)
r = ranked.sort_values("avg_gain_vs_grid")
cols = [RED if v > 0 else BLUE for v in r.avg_gain_vs_grid]
ax[1].barh(r.full_name, r.avg_gain_vs_grid, color=cols); ax[1].axvline(0, color=DARK, lw=.8)
ax[1].set_xlabel("Average positions gained from grid to finish (classified finishes; + = gained)")
ax[1].set_title("Q: Who gains (or loses) the most places?", fontsize=10.5); ax[1].tick_params(axis="y", labelsize=8)
save(fig, "08_qualifying_vs_race.png")
ins["grid_finish_corr"] = round(float(j4all.corr_grid_finish), 3)
ins["pct_gained"] = round(float(j4all.pct_gained), 1); ins["pct_lost"] = round(float(j4all.pct_lost), 1); ins["pct_same"] = round(float(j4all.pct_same), 1)
ins["pole_to_win_pct"] = round(float(g[g.slot == 1].wins.iloc[0] / g[g.slot == 1].entries.iloc[0] * 100), 1)
ins["avg_finish_by_slot"] = g[g.slot.isin([1, 2, 3, 5, 10, 15, 20])][["slot", "avg_finish_classified"]].round(2).to_dict("records")
ins["top_gainers"] = top(ranked, "avg_gain_vs_grid", 5, asc=False)[["full_name", "avg_gain_vs_grid", "avg_grid", "pct_gained"]].round(2).to_dict("records")
ins["top_losers"] = top(ranked, "avg_gain_vs_grid", 4)[["full_name", "avg_gain_vs_grid", "avg_grid", "pct_gained"]].round(2).to_dict("records")
ins["quali_vs_grid_penalty_avg"] = round(float(j4all.avg_grid_penalty), 3)

# =========================================================================================== FIG 9 pit stops
p_all = j5[(j5.scope.astype(str) == "ALL") & (j5.team != "FIELD")].copy().sort_values("avg_sec")
fld = j5[(j5.scope.astype(str) == "ALL") & (j5.team == "FIELD")].iloc[0]
p_all.to_csv(OUT + "pitstop_by_constructor.csv", index=False)
fig, ax = plt.subplots(1, 3, figsize=(15, 5.2), gridspec_kw={"width_ratios": [1.1, .8, .8]})
pp = p_all.iloc[::-1]
ax[0].barh(pp.team, pp.avg_sec, xerr=pp.std_sec / np.sqrt(pp.n_valid) * 1.96, color=[TEAM_COL[t] for t in pp.team], capsize=3)
ax[0].axvline(fld.avg_sec, color=DARK, ls="--", lw=1, label=f"field average {fld.avg_sec:.2f}s"); ax[0].legend(fontsize=8)
ax[0].set_xlim(22.5, 27); ax[0].set_xlabel("Mean pit-lane time (s)  +/- 95% CI"); ax[0].set_title("Q: Who has the fastest pit stops?")
for y, v in enumerate(pp.avg_sec): ax[0].text(26.9, y, f"{v:.2f}", va="center", ha="right", fontsize=8)
q = p_all.sort_values("std_sec", ascending=False)
ax[1].barh(q.team, q.std_sec, color=[TEAM_COL[t] for t in q.team]); ax[1].set_yticklabels([]); ax[1].set_xlabel("Std-dev of pit-lane time (s)")
ax[1].set_title("Consistency (lower = better)")
for y, v in enumerate(q.std_sec): ax[1].text(v + .05, y, f"{v:.1f}", va="center", fontsize=8)
s_ = p_all.sort_values("slow_stop_pct", ascending=False)
ax[2].barh(s_.team, s_.slow_stop_pct, color=[TEAM_COL[t] for t in s_.team]); ax[2].set_yticklabels([]); ax[2].set_xlabel("% of stops > 1.5x the race's median stop")
ax[2].set_title("Slow / problem stops")
for y, v in enumerate(s_.slow_stop_pct): ax[2].text(v + .08, y, f"{v:.1f}%", va="center", fontsize=8)
save(fig, "09_pitstop_performance_by_constructor.png")
ins["pit_field"] = {"avg_sec": round(float(fld.avg_sec), 2), "median_sec": round(float(fld.median_sec), 2), "n_stops": int(fld.n_stops), "n_valid": int(fld.n_valid), "fastest_sec": round(float(fld.fastest_sec), 2)}
ins["pit_ranking"] = p_all[["team", "avg_sec", "median_sec", "std_sec", "fastest_sec", "slow_stop_pct", "avg_rel_pct", "n_valid"]].round(2).to_dict("records")
pf = j5[(j5.team == "FIELD") & (j5.scope.astype(str) != "ALL")].copy(); pf["year"] = pf.scope.astype(int); pf = pf.sort_values("year")
ins["pit_field_by_year"] = pf[["year", "avg_sec", "median_sec", "fastest_sec", "n_valid"]].round(2).to_dict("records")

# =========================================================================================== FIG 10 historical trends
se = j6["SEASON"].sort_values("year")
cy = j6["CIRCYEAR"]; cy = cy[cy.n_rep_laps >= 300].copy()
nyears = cy.groupby("layoutId").year.nunique(); stable = nyears[nyears >= 5].index
cy = cy[cy.layoutId.isin(stable)]
cy["ref"] = cy.groupby("layoutId").avg_rep_lap_sec.transform("median")
cy["idx"] = cy.avg_rep_lap_sec / cy.ref * 100
idx = cy.groupby("year").idx.median()                                             # median over circuits = robust to wet races
base_idx = idx.loc[2018]; idx_rel = (idx / base_idx * 100)
ci_cnt = cy.groupby("year").layoutId.nunique()
champ_share = tm[tm.final_pos == 1].set_index("year").final_points / tm.groupby("year").final_points.sum()
top2_gap = (tm[tm.final_pos == 1].set_index("year").final_points - tm[tm.final_pos == 2].set_index("year").final_points)
dr6 = j6["DRIVER"].merge(drivers, on="driverId")
champ_d = dr6[dr6.final_pos == 1].set_index("year")
fig, ax = plt.subplots(1, 3, figsize=(16, 5))
ax[0].plot(idx_rel.index, idx_rel.values, "-o", color=RED); ax[0].set_ylabel("Race-pace index (2018 = 100)")
for x, y in idx_rel.items(): ax[0].annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8)
ax[0].set_title(f"Q: Did cars get faster?\nlike-for-like lap-time index ({ci_cnt.min()}-{ci_cnt.max()} stable layouts / season)", fontsize=10.5); ax[0].invert_yaxis()
ax[0].set_xlabel("season")
yrs = sorted(champ_t)
ax[1].bar(yrs, [champ_share[y] * 100 for y in yrs], color=[TEAM_COL[champ_t[y]] for y in yrs])
for y in yrs: ax[1].text(y, champ_share[y] * 100 + .6, champ_t[y].split(" (")[0], ha="center", fontsize=7.5, rotation=0)
ax[1].set_ylabel("Champion team's share of ALL points scored (%)"); ax[1].set_title("Q: Which teams dominated which periods?", fontsize=10.5); ax[1].set_ylim(0, 45)
ax[1].set_xlabel("season")
a2 = ax[2]; a2.bar(se.year, se.distinct_winners, color=GREY, label="different race winners"); a2.set_ylabel("distinct Grand Prix winners")
a3 = a2.twinx(); a3.plot(se.year, se.not_classified_pct, "-o", color=RED, label="not-classified rate (%)"); a3.set_ylabel("% of starts not classified", color=RED); a3.grid(False)
a3.spines["right"].set_visible(True); a2.set_title("Competitiveness & reliability by season", fontsize=10.5); a2.set_xlabel("season")
save(fig, "10_historical_trends_2018_2025.png")
ins["lap_index"] = {int(k): round(float(v), 2) for k, v in idx_rel.items()}
ins["lap_index_layouts"] = int(len(stable))
ins["champion_team_share_pct"] = {int(k): round(float(v * 100), 1) for k, v in champ_share.items()}
ins["champion_points_gap_to_P2"] = {int(k): float(v) for k, v in top2_gap.items()}
ins["driver_champions"] = {int(y): {"driver": champ_d.loc[y, "full_name"], "points": float(champ_d.loc[y, "final_points"]), "wins": int(champ_d.loc[y, "final_wins"])} for y in champ_d.index}
ins["season_summary"] = se[["year", "races", "distinct_winners", "distinct_winning_teams", "not_classified_pct"]].round(1).to_dict("records")

# per-season table for dominant drivers / teams
wins_by_year_team = tm.pivot_table(index="year", columns="team", values="wins", aggfunc="sum").fillna(0).astype(int)
wins_by_year_team.to_csv(OUT + "team_wins_by_season.csv")
dr6.sort_values(["year", "final_pos"]).to_csv(OUT + "driver_season_results.csv", index=False)
drv.drop(columns=["rtype"], errors="ignore").sort_values("avg_finish_all").to_csv(OUT + "driver_master_table.csv", index=False)
j0.to_csv(OUT + "race_baseline.csv", index=False)
ins["races_unusable_for_pace"] = j0[j0.usable == 0].raceId.tolist()
ins["mapreduce_scale"] = {"races": int(len(j0)), "laps": int(j0.n_laps.sum()), "pit_stops": int(j0.n_pit_stops.sum()), "drivers": int(len(drv))}

json.dump(ins, open(OUT + "insights.json", "w"), indent=2, default=str)
print("analysis done; insights ->", OUT + "insights.json")
