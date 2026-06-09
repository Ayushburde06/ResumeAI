#!/bin/bash
set -e

echo "=============================="
echo " ResumeAI EC2 Setup Script"
echo "=============================="

# Step 1: Swap
echo "[1/4] Setting up swap memory..."
if free | awk '/^Swap:/{exit !$2}'; then
    echo "Swap already active, skipping..."
else
    sudo dd if=/dev/zero of=/swapfile bs=1M count=2048 status=progress
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi
echo "Swap status:"; free -h | grep Swap
echo "SWAP DONE"

# Step 2: Docker
echo "[2/4] Installing Docker..."
sudo apt update -y
sudo apt install -y docker.io docker-compose git
sudo usermod -aG docker ubuntu
sudo systemctl enable docker
sudo systemctl start docker
echo "DOCKER DONE"

# Step 3: Clone repo
echo "[3/4] Cloning ResumeAI repo..."
if [ -d "/home/ubuntu/app" ]; then
    echo "Repo already exists, pulling latest..."
    cd /home/ubuntu/app && git pull origin main
else
    git clone https://github.com/Ayushburde06/ResumeAI.git /home/ubuntu/app
fi
echo "CLONE DONE"

echo ""
echo "=============================="
echo "STEP 1-3 COMPLETE!"
echo ""
echo "NOW run this next:"
echo "  nano /home/ubuntu/app/backend/.env"
echo "=============================="
