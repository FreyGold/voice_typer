#!/bin/bash
# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR/.."

# Check for venv
if [ ! -d "venv" ]; then
    osascript -e 'display dialog "Virtual environment not found. Please run install instructions first." buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Activate and run
source venv/bin/activate
python3 main.py
