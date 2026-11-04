#!/usr/bin/env bash
# STAGE 2: create the /f1 directory tree and upload the cleaned data with real `hdfs dfs` (FsShell) commands.
source "$(dirname "$0")/env.sh"
cd "$PROJECT"
LOG="$LOGS/02_hdfs_commands.log"; : > "$LOG"
run() { echo "\$ hdfs dfs $*" | sed "s#${HDFS_ROOT}##g" | tee -a "$LOG"; hdfs_dfs "$@" 2>&1 | grep -v "^SLF4J" | sed "s#${HDFS_ROOT}##g" | tee -a "$LOG"; }
echo "MODE=$MODE  filesystem root: ${HDFS_ROOT:-<default hdfs://>}" | tee -a "$LOG"
hdfs_dfs -rm -r -f -skipTrash "$(H '')" >/dev/null 2>&1
for d in races circuits drivers constructors results sprint_results qualifying laps pitstops standings output; do run -mkdir -p "$(H $d)"; done
run -ls "$(H '')"
run -put -f data/clean/races/races.csv                       "$(H races)/"
run -put -f data/clean/circuits/circuits.csv                 "$(H circuits)/"
run -put -f data/clean/drivers/drivers.csv                   "$(H drivers)/"
run -put -f data/clean/constructors/constructors.csv         "$(H constructors)/"
run -put -f data/clean/results/results.csv                   "$(H results)/"
run -put -f data/clean/sprint_results/sprint_results.csv     "$(H sprint_results)/"
run -put -f data/clean/qualifying/qualifying.csv             "$(H qualifying)/"
run -put -f data/clean/laps/laps.csv                         "$(H laps)/"
run -put -f data/clean/pitstops/pitstops.csv                 "$(H pitstops)/"
run -put -f data/clean/standings/driver_standings.csv        "$(H standings)/"
run -put -f data/clean/standings/constructor_standings.csv   "$(H standings)/"
echo "----- verification -----" | tee -a "$LOG"
run -ls -R -h "$(H '')"
run -du -h "$(H '')"
run -count -h "$(H laps)"
run -stat "%n  size=%b bytes  blocksize=%o  replication=%r" "$(H laps)/laps.csv"
echo "\$ hdfs dfs -cat /f1/laps/laps.csv | head -5" | tee -a "$LOG"; hdfs_dfs -cat "$(H laps)/laps.csv" 2>/dev/null | head -5 | tee -a "$LOG"
if [ "$MODE" = "cluster" ]; then
  echo "\$ hdfs fsck /f1 -files -blocks" | tee -a "$LOG"; "$HADOOP_HOME/bin/hdfs" fsck /f1 -files -blocks 2>&1 | tail -30 | tee -a "$LOG"
fi
