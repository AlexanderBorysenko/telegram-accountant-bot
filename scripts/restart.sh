#!/bin/bash
set -e
cd "$(dirname "$0")/.."
bash scripts/stop.sh
bash scripts/start.sh
