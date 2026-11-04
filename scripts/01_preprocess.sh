#!/usr/bin/env bash
source "$(dirname "$0")/env.sh"
cd "$PROJECT"
python3 src/preprocessing/clean_f1.py data/raw data/clean results/data_quality_report.json 2>&1 | tee "$LOGS/01_preprocess.log" | tail -5
