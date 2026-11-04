#!/usr/bin/env bash
source "$(dirname "$0")/env.sh"
cd "$PROJECT"
python3 src/analysis/analyze.py 2>&1 | tee "$LOGS/05_analysis.log"
python3 src/analysis/kmeans_drivers.py 2>&1 | tee "$LOGS/06_kmeans.log"
