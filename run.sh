#!/bin/sh

PROJECT="$PWD"
VENV="$PROJECT/.venv/bin/python3"

LOG_DIR="$PROJECT/logs"
timestamp=$(date '+%Y%m%d %H%M')
export LOG_FILE="$LOG_DIR/$timestamp.csv"

mkdir -p "$LOG_DIR"
find "$LOG_DIR" -maxdepth 1 -name "*.csv" -print0 \
  | xargs -0 ls -1t \
  | tail -n +9 \
  | xargs -I {} rm -f "$LOG_DIR/{}"

echo "Script start @ $(date)"
$VENV -u run.py
echo "Script done @ $(date)"
