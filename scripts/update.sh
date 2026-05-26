#!/bin/bash
set -e
cd "$(dirname "$0")/.."
echo "Pulling latest changes..."
git pull
echo "Rebuilding and restarting..."
docker compose up -d --build
echo "Accounter Bot updated and restarted."
