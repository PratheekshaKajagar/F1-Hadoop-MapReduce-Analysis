#!/usr/bin/env bash
# STAGE 4: pull MapReduce output out of HDFS (`hdfs dfs -getmerge`) into results/mapreduce/*.tsv
source "$(dirname "$0")/env.sh"
cd "$PROJECT"; mkdir -p results/mapreduce
LOG="$LOGS/04_fetch_results.log"; : > "$LOG"
hdfs_dfs -ls -R "$(H output)" 2>&1 | grep -v SLF4J | sed "s#${HDFS_ROOT}##g" | tee -a "$LOG"
for j in $(hdfs_dfs -ls "$(H output)" 2>/dev/null | awk '{print $NF}' | grep '/job' | xargs -n1 basename); do
  rm -f "results/mapreduce/$j.tsv"
  hdfs_dfs -getmerge "$(H output)/$j" "results/mapreduce/$j.tsv" 2>/dev/null
  echo "getmerge $j -> results/mapreduce/$j.tsv ($(wc -l < results/mapreduce/$j.tsv) rows)" | tee -a "$LOG"
done
find results/mapreduce -name '.*.crc' -delete
