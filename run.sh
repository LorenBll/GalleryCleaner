#!/bin/bash

echo "Starting GalleryCleaner Application..."
echo

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run ./setup.sh first to create the virtual environment."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment"
    exit 1
fi

# Check if main.py exists
if [ ! -f "src/main.py" ]; then
    echo "ERROR: main.py not found in src directory"
    exit 1
fi

# Run the application
echo "Running GalleryCleaner..."
python src/main.py

# Check if the application ran successfully
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo
    echo "Application exited with an error (code $exit_code)"
    exit $exit_code
fi
