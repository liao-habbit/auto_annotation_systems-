#!/usr/bin/env bash
cd "$(dirname "$0")/.."

python3 clean_review_batch.py

echo ""
read -p "Press Enter to continue..."