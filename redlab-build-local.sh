#!/bin/bash
set -e

echo ">>> Starting local build and container refresh..."

# 1. Clean up old local image to prevent using stale cache
echo ">>> Removing old image..."
docker rmi nomad375/redlab-daq:latest 2>/dev/null || true

# 2. Build the image locally using the override file
echo ">>> Compiling new image..."
docker compose -f docker-compose.yml -f docker-compose.override.yml build daq-collector

# 3. Remove dangling build layers
echo ">>> Cleaning up system..."
docker image prune -f

# 4. Restart only the collector to apply changes while keeping DB volumes intact
echo ">>> Restarting daq-collector (keeping data history)..."
docker compose up -d --no-deps daq-collector

echo ">>> Local build successfully applied."