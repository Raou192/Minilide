#!/bin/bash

PROJECT_DIR="$HOME/minilide"
PYTHON_PATH="/usr/bin/python3"

EXTRACT_SCRIPT="$PYTHON_PATH $PROJECT_DIR/extract_minilide.py"
SEND_SCRIPT="$PYTHON_PATH $PROJECT_DIR/send_report.py"

CRON_ENTRIES="
*/15 * * * * $EXTRACT_SCRIPT
0 18 * * * $SEND_SCRIPT
"

crontab -l > old_crontab.bak 2>/dev/null
(echo "$CRON_ENTRIES" && crontab -l 2>/dev/null) | sort | uniq | crontab -