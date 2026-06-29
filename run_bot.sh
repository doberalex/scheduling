#!/bin/bash

PROJECT_DIR="/home/d/doberalex/public_html/scheduling"
PYTHON_BIN="$PROJECT_DIR/venv/bin/python"

if [ ! -x "$PYTHON_BIN" ] || ! "$PYTHON_BIN" -c "import aiogram" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

if ! pgrep -f "$PROJECT_DIR/run.py" > /dev/null
then
    cd "$PROJECT_DIR" || exit 1
    nohup "$PYTHON_BIN" "$PROJECT_DIR/run.py" > "$PROJECT_DIR/bot.log" 2>&1 &
fi
