#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "==========================================="
echo "   Raspberry Pi DAQ Stack Setup Utility    "
echo "==========================================="

# 1. Update the system
echo ">>> Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install Docker using the official convenience script
if ! command -v docker &> /dev/null; then
    echo ">>> Installing Docker..."
    curl -sSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo ">>> Docker installed. User added to 'docker' group."
else
    echo ">>> Docker is already installed."
fi

# 3. Install git (required to clone the project)
if ! command -v git &> /dev/null; then
    echo ">>> Installing git..."
    sudo apt-get install -y git
fi

# 4. Clone the repository (Placeholder - replace with your actual repo URL)
# If the folder already exists, we skip this step
PROJECT_DIR="redlab-daq-project"
if [ ! -d "$PROJECT_DIR" ]; then
    echo ">>> Please enter your Git Repository URL:"
    read REPO_URL
    git clone "$REPO_URL" "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# 5. Handle environment variables (.env)
if [ ! -f ".env" ]; then
    echo ">>> .env file not found. Creating from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "!!! IMPORTANT: Please edit the .env file with your InfluxDB tokens now."
        echo ">>> Command: nano .env"
    else
        echo "!!! WARNING: .env.example not found. You will need to create .env manually."
    fi
fi

# 6. Ensure scripts are executable
chmod +x *.sh

# 7. Final deployment
echo ">>> Initializing the stack..."
# We use our previously created setup.sh to pull images and start
./setup.sh

echo "==========================================="
echo "   Setup finished! Check logs: ./logs.sh   "
echo "==========================================="