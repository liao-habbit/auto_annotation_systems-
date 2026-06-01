#!/usr/bin/env bash

cd "$(dirname "$0")/.."

echo "Starting application..."
python3 app.py

echo ""
echo "Program finished."
read -p "Press Enter to continue..."