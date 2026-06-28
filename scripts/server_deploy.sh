#!/bin/bash
set -e

PROJECT_DIR="/home/d/doberalex/public_html/scheduling"

cd "$PROJECT_DIR"

PYTHON_BIN="python3"
PIP_BIN="python3 -m pip"
PIP_INSTALL_ARGS="--user"

if [ -d venv ] && { [ ! -x venv/bin/python ] || ! venv/bin/python -m pip --version >/dev/null 2>&1; }; then
    rm -rf venv
fi

if [ ! -d venv ]; then
    if python3 -m venv venv; then
        PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
        PIP_BIN="$PROJECT_DIR/venv/bin/python -m pip"
        PIP_INSTALL_ARGS=""
    fi
else
    PYTHON_BIN="$PROJECT_DIR/venv/bin/python"
    PIP_BIN="$PROJECT_DIR/venv/bin/python -m pip"
    PIP_INSTALL_ARGS=""
fi

$PIP_BIN install $PIP_INSTALL_ARGS -r requirements.txt
$PYTHON_BIN scripts/init_db.py
chmod +x run_bot.sh
./run_bot.sh

echo "Scheduling bot deploy finished"
