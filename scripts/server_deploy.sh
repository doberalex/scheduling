#!/bin/bash
set -e

PROJECT_DIR="/home/d/doberalex/public_html/scheduling"

cd "$PROJECT_DIR"

if [ ! -d venv ]; then
    python3 -m venv venv
fi

venv/bin/pip install -r requirements.txt
venv/bin/python scripts/init_db.py
chmod +x run_bot.sh
./run_bot.sh

echo "Scheduling bot deploy finished"

