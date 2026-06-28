#!/bin/bash

PROJECT_DIR="/home/d/doberalex/public_html/scheduling"

if ! pgrep -f "$PROJECT_DIR/run.py" > /dev/null
then
    cd "$PROJECT_DIR" || exit 1
    nohup python3 "$PROJECT_DIR/run.py" > "$PROJECT_DIR/bot.log" 2>&1 &
fi

