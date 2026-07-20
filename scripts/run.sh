#!/bin/bash

# Start GalleryCleaner.

set -euo pipefail

VERBOSE=0
if [ "${1:-}" = "--verbose" ]; then
  VERBOSE=1
fi

cd "$(dirname "$0")/.." || exit 1

# Check Python 3.10+.
if ! command -v python3 &>/dev/null; then
  [ $VERBOSE -eq 1 ] && echo "ERROR: Python 3 not installed or not on PATH."
  exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]; }; then
  [ $VERBOSE -eq 1 ] && echo "ERROR: Python 3.10+ required; found $PYTHON_VERSION"
  exit 1
fi

[ $VERBOSE -eq 1 ] && echo "Python $PYTHON_VERSION detected."

# Create or reuse virtual environment.
if [ ! -d ".venv" ]; then
  [ $VERBOSE -eq 1 ] && echo "Creating virtual environment..."
  python3 -m venv .venv
  [ $VERBOSE -eq 1 ] && echo "Virtual environment created."
fi

# Activate virtual environment.
source .venv/bin/activate
[ $VERBOSE -eq 1 ] && echo "Virtual environment activated."

# Install or upgrade dependencies.
[ $VERBOSE -eq 1 ] && echo "Installing dependencies..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
[ $VERBOSE -eq 1 ] && echo "Dependencies installed."

# Start GalleryCleaner.
[ $VERBOSE -eq 1 ] && echo "" && echo "GalleryCleaner starting..." && echo ""
python src/main.py
