#!/bin/bash
cd "$(dirname "$0")/.."
python3 prepare_and_predict.py
read -p "Press Enter to continue..."