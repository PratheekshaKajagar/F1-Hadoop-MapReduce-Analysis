#!/usr/bin/env bash
# STAGE 3: run the 7 MapReduce jobs (Job 0 baseline + Jobs 1-6).  Each job's Hadoop log (counters etc.) goes to logs/jobN.log
source "$(dirname "$0")/env.sh"
cd "$PROJECT"
S() { echo "file://$MR/$1"; }                         # local script shipped to tasks
OUT="$(H output)"
PY="env PYTHONPATH=. python3"   # distributed-cache files are symlinks in separate dirs -> make cwd importable (also needed on YARN)
run_job() {   # name  mapper  reducer  reduces  "inputs..."  "files..."
  local name=$1 mapper=$2 reducer=$3 nred=$4 inputs=$5 files=$6 args=()
  for i in $inputs; do args+=(-input "$i"); done
  hdfs_dfs -rm -r -f -skipTrash "$OUT/$name" >/dev/null 2>&1
  local t0=$(date +%s)
  echo ">>> $name  ($(date +%T))"
  run_streaming -files "$files,$(S common.py),$(S $mapper),$(S $reducer)" "${args[@]}" -output "$OUT/$name" \
      -mapper "$PY $mapper" -reducer "$PY $reducer" -numReduceTasks "$nred" -name "$name" > "$LOGS/$name.log" 2>&1 \
      || { echo "JOB FAILED: $name (see $LOGS/$name.log)"; tail -20 "$LOGS/$name.log"; exit 1; }
  echo "    done in $(( $(date +%s) - t0 ))s   map-in=$(grep 'Map input records' $LOGS/$name.log | tail -1 | sed 's/.*=//')  map-out=$(grep 'Map output records' $LOGS/$name.log | tail -1 | sed 's/.*=//')  reduce-groups=$(grep 'Reduce input groups' $LOGS/$name.log | tail -1 | sed 's/.*=//')  reduce-out=$(grep 'Reduce output records' $LOGS/$name.log | tail -1 | sed 's/.*=//')"
}
RACES="$(H races)/races.csv"; CONS="$(H constructors)/constructors.csv"; PITS="$(H pitstops)/pitstops.csv"
RES="$(H results)/results.csv"; QUAL="$(H qualifying)/qualifying.csv"
BASE="$OUT/job0_race_baseline/part-r-00000#race_baseline.tsv"

run_job job0_race_baseline        job0_mapper.py job0_reducer.py 1 "$(H laps) $(H pitstops)"                                   "$PITS"
run_job job1_driver_performance   job1_mapper.py job1_reducer.py 2 "$(H laps)"                                                 "$BASE,$PITS"
run_job job2_constructor_perf     job2_mapper.py job2_reducer.py 2 "$(H results) $(H sprint_results)"                          "$RACES,$CONS"
run_job job3_circuit_performance  job3_mapper.py job3_reducer.py 2 "$(H laps) $(H results)"                                    "$RACES,$BASE,$PITS"
run_job job4_qualifying_vs_race   job4_mapper.py job4_reducer.py 2 "$(H results)"                                              "$QUAL"
run_job job5_pitstop_performance  job5_mapper.py job5_reducer.py 2 "$(H pitstops)"                                             "$RES,$RACES,$CONS,$BASE"
run_job job6_seasonal_performance job6_mapper.py job6_reducer.py 2 "$(H results) $(H laps) $(H standings)"                     "$RACES,$CONS,$BASE,$PITS"
echo "ALL JOBS FINISHED"
