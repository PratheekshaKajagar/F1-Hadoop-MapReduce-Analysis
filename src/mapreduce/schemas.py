"""Column names of every MapReduce output (Hadoop output files are header-less TSV)."""
SCHEMAS = {
 "job0_race_baseline": "raceId n_laps n_drivers fastest_lap_sec baseline_median_sec n_racing_laps n_rep_laps n_pit_stops pit_median_sec usable".split(),
 "job1_driver_performance": "driverId races laps_total laps_led fastest_lap_sec slowest_lap_sec n_rep_laps avg_lap_sec std_lap_sec slowest_rep_lap_sec avg_rel_pace_pct consistency_cv_pct avg_fastest_gap_pct usable_races".split(),
 "job2_constructor_perf": "team scope races entries points_total points_gp points_sprint wins podiums poles fastest_laps avg_finish_classified avg_finish_all avg_grid not_classified points_per_race".split(),
 "job3_circuit_performance": "layoutId races first_year last_year avg_rep_lap_sec fastest_lap_sec fastest_lap_year avg_fastest_lap_speed_kmh pace_spread_pct dnf_rate_pct avg_abs_pos_change grid_finish_corr avg_winning_margin_sec pole_win_rate_pct".split(),
 "job4_qualifying_vs_race": "rtype key entries n_gain_races avg_qual_pos avg_grid avg_finish_classified avg_finish_all avg_gain_vs_grid std_gain pct_gained pct_lost pct_same avg_gain_vs_quali avg_grid_penalty wins podiums corr_grid_finish".split(),
 "job5_pitstop_performance": "team scope n_stops n_valid races avg_sec median_sec fastest_sec std_sec avg_rel_pct slow_stop_pct invalid_stops".split(),
 # Job 6 writes 4 record types
 "job6_SEASON": "rtype year races entries not_classified_pct distinct_winners distinct_winning_teams n_rep_laps avg_rep_lap_sec".split(),
 "job6_DRIVER": "rtype year driverId races_gp points_gp wins podiums avg_finish_all laps laps_led avg_rel_pace_pct final_pos final_points final_wins".split(),
 "job6_TEAM": "rtype year team races_gp points_gp wins podiums avg_finish_all final_pos final_points final_wins".split(),
 "job6_CIRCYEAR": "rtype layoutId year n_rep_laps avg_rep_lap_sec fastest_lap_sec".split(),
}


def load_job6(path="results/mapreduce/job6_seasonal_performance.tsv"):
    """Job 6 emits 4 record types with different widths -> split by the first column. Returns {rtype: DataFrame}."""
    import pandas as pd
    rows = {}
    for line in open(path):
        p = line.rstrip("\n").split("\t")
        rows.setdefault(p[0], []).append(p)
    out = {}
    for rt, r in rows.items():
        df = pd.DataFrame(r, columns=SCHEMAS["job6_" + rt])
        for c in df.columns[1:]:
            if c != "team":
                df[c] = pd.to_numeric(df[c].replace("", None))
        out[rt] = df
    return out
