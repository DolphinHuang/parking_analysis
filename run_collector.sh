#!/bin/bash

PROJECT_DIR="$HOME/parking_analysis"

cd "$PROJECT_DIR" || exit 1

set -a
source "$PROJECT_DIR/env.docker"
set +a

"$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/collector.py"
