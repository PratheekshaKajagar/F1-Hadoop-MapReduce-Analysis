# Formula 1 Race Performance Analysis using Hadoop & MapReduce (2018-2025)

**Pipeline:** F1 data -> Python cleaning -> HDFS (`/f1/...`) -> Hadoop MapReduce (7 jobs) -> aggregated metrics -> Python analysis -> 12 figures -> insights -> K-Means

## READ THIS FIRST - what is real and what is not
* **Real Apache Hadoop 3.3.4 code is used**: the genuine MapReduce engine (job submission, input splits, map tasks, sort/shuffle, partitioner, reduce tasks, counters, `_SUCCESS`, `part-r-0000N` files), the genuine `hdfs dfs` shell (`FsShell`), and the distributed cache (`-files`).
* **Mappers/reducers are Python Hadoop-Streaming scripts** (stdin/stdout, `key<TAB>value`). No pandas in any job.
* **Limitation (be upfront in your viva):** the sandbox where this was built could not download a full Hadoop distribution (Apache mirrors blocked), so there was **no NameNode/DataNode/YARN**. In `MODE=local` the "HDFS" is Hadoop's FileSystem API on the local disk (`file://.../hdfs_local/f1/...`), not a distributed filesystem, and the streaming driver is `hadoop_local/src/PyStreaming.java`, a small re-implementation of `hadoop-streaming.jar` on the real MapReduce API. **`MODE=cluster` runs the identical scripts on a real HDFS/YARN cluster with the official streaming jar - it was NOT tested here.** See `docs/HADOOP_SETUP.md`. Run it on your machine before the viva so you can show real HDFS output / fsck / YARN UI.
* **Data size is honest:** 189,105 laps (3.8 MB) + 5,941 pit stops + 3,458 results. This is *not* "big" by volume; Hadoop is used for the paradigm and scalability, nothing was duplicated or inflated.
* All results come from the real 2018-2025 dataset; nothing is invented. Mapper outputs are cross-checked by `src/analysis/validate_mapreduce.py` (all checks pass; `results/validation_report.txt`).

## Run
```bash
pip install pandas numpy matplotlib scikit-learn      # Java 8+ required
./scripts/run_all.sh                                  # local mode (bundled Hadoop libs), ~1 min
python3 src/analysis/validate_mapreduce.py            # independent verification
# real cluster:  MODE=cluster HADOOP_HOME=/opt/hadoop ./scripts/run_all.sh
```
Stages: `01_preprocess.sh`, `02_hdfs_upload.sh` (mkdir/put/ls/du/stat/cat), `03_run_mapreduce.sh`, `04_fetch_results.sh` (getmerge), `05_analysis.sh`.

## MapReduce jobs
| Job | Input (HDFS) | Side tables (distributed cache) | Output |
|---|---|---|---|
| 0 race baseline | laps, pitstops | pitstops | per-race median racing lap, usable flag, pit median |
| 1 driver performance | laps | baseline, pitstops | laps, laps led, fastest/slowest, avg, std, relative pace, consistency |
| 2 constructor performance | results, sprint_results | races, constructors | points, wins, podiums, poles, avg finish/grid, per season + ALL |
| 3 circuit performance | laps, results | races, baseline, pitstops | lap time, speed, pace spread, DNF, grid-finish corr, margin |
| 4 qualifying vs race | results | qualifying | per driver / per grid slot / global gains and correlation |
| 5 pit stops | pitstops | results, races, constructors, baseline | per team and season: avg, median, fastest, std, slow-stop % |
| 6 seasonal | results, laps, standings | races, constructors, baseline, pitstops | season, driver-season, team-season (official standings), circuit-year |

Techniques: map-side (replicated) joins, in-mapper combining, job chaining (Job 0 -> 1,3,5,6), multi-input jobs, 2 reducers with hash partitioning.

## Data-quality decisions (found by inspecting the data)
* 2018-2025 only (raw file also contains 2026 rows - excluded).
* 2025 source fills `position` for retirees; rule `classified <=> positionText numeric` is applied to all seasons.
* Track layouts changed (Yas Marina 2021, Albert Park 2022, Barcelona 2023, Marina Bay 2023, 2020 Sakhir outer loop) -> separate `layoutId`s.
* Raw lap seconds are not comparable between circuits, so driver pace = lap time relative to that race's median racing lap; safety-car/red-flag laps and pit in/out laps are excluded inside Hadoop (Job 0/1). Belgian GP 2021 (3 laps behind the safety car) is flagged unusable for pace.
* Pit times are pit-LANE times; stops > 60 s (red flags/repairs) are excluded from the median and flagged invalid.
* Computed points equal official standings in 78/80 team-seasons; the 2 exceptions are FIA penalties (Force India 2018, Racing Point 2020).
* Team lineages are grouped (Toro Rosso/AlphaTauri/RB; Force India/Racing Point/Aston Martin; Sauber/Alfa Romeo; Renault/Alpine).

## Layout
`src/preprocessing`, `src/mapreduce` (scripts), `src/analysis`, `hadoop_local` (libs + Java driver), `scripts`, `data/raw|clean`, `hdfs_local/f1` (HDFS tree incl. job outputs), `results`, `figures`, `logs` (HDFS commands + Hadoop job logs/counters), `docs`.
