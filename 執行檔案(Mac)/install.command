#!/usr/bin/env bash

cd "$(dirname "$0")/.."

echo "Installing packages..."
python3 -m pip install -r requirements.txt

echo ""
echo "Installation finished."
read -p "Press Enter to continue..."