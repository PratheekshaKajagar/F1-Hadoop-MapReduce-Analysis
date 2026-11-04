#!/usr/bin/env bash
# Whole pipeline:  F1 data -> cleaning -> HDFS -> MapReduce -> results -> analysis/figures -> K-Means
#   ./scripts/run_all.sh                  (MODE=local : bundled Hadoop libraries)
#   MODE=cluster HADOOP_HOME=/opt/hadoop ./scripts/run_all.sh   (real HDFS + YARN cluster)
set -e
D="$(dirname "$0")"
bash "$D/01_preprocess.sh"; bash "$D/02_hdfs_upload.sh" > /dev/null; bash "$D/03_run_mapreduce.sh"
bash "$D/04_fetch_results.sh" > /dev/null; bash "$D/05_analysis.sh"
