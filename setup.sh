#!/bin/bash
set -e

echo ">>> Deploying DAQ Stack from Docker Hub..."

# Pull the latest pre-compiled images (saves time on RPi/Production)
echo ">>> Updating images..."
docker compose pull

# Fully restart the stack
# Data history is safe as volumes are persistent
echo ">>> Recreating all containers..."
docker compose down --remove-orphans
docker compose up -d

echo ">>> Deployment complete."
docker compose ps