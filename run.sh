#!/bin/sh

PROJECT="$(cd "$(dirname "$0")" && pwd)"
VENV="$PROJECT/.venv/bin/python3"

LOG_DIR="$PROJECT/logs"
timestamp=$(date '+%Y%m%d_%H%M')
export LOG_FILE="$LOG_DIR/$timestamp.csv"

mkdir -p "$LOG_DIR"

# keep the 7 most recent logs; prune before adding new one so max = 7 after run
ls -1t "$LOG_DIR"/*.csv 2>/dev/null | tail -n +8 | while IFS= read -r f; do
  rm -f "$f"
done

echo "Script start @ $(date)"
$VENV -u "$PROJECT/run.py"
echo "Script done @ $(date)"
