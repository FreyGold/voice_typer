#!/bin/bash
# Navigate to the script's directory
cd "$(dirname "$0")"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Please ensure dependencies are installed."
    exit 1
fi

# Run the application
python3 main.py
