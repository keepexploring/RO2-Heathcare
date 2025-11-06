#!/bin/bash
# Digital Ocean Droplet Deployment Script
# This script sets up your oxygen concentrator monitoring system on a fresh Ubuntu droplet

set -e  # Exit on any error

echo "🚀 Setting up Oxygen Concentrator Monitoring System..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
sudo apt-get install -y docker-compose-plugin

# Install Git if not present
echo "📥 Installing Git..."
sudo apt-get install -y git

# Clone repository
echo "📂 Cloning repository..."
read -p "Enter your GitHub repository URL (e.g., https://github.com/keepexploring/RO2-Heathcare.git): " REPO_URL
git clone $REPO_URL
cd $(basename $REPO_URL .git)/sensing

# Create .env file
echo "⚙️  Creating environment file..."
cat > .env << 'EOF'
# Database Configuration (using Railway PostgreSQL)
DATABASE_URL=your-railway-postgres-url-here

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-in-production

# User Authentication
USERS={"admin": "admin123", "user": "password"}

# MQTT Configuration (using local Mosquitto)
MQTT_BROKER_URL=mosquitto
MQTT_BROKER_PORT=1883

# FastAPI URL for Panel
FASTAPI_URL=http://fastapi:8000
EOF

echo "⚠️  IMPORTANT: Edit the .env file with your actual credentials"
echo "Run: nano .env"
read -p "Press Enter after you've updated .env file..."

# Start services
echo "🚀 Starting all services..."
docker compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Show status
echo "📊 Service Status:"
docker compose ps

# Show logs
echo "📝 Recent logs:"
docker compose logs --tail=20

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access your services:"
echo "   Panel Dashboard: http://$(curl -s ifconfig.me):5006"
echo "   FastAPI Backend: http://$(curl -s ifconfig.me):8000"
echo "   MQTT Broker: mqtt://$(curl -s ifconfig.me):1883"
echo ""
echo "🔧 Useful commands:"
echo "   View logs:        docker compose logs -f"
echo "   Restart services: docker compose restart"
echo "   Stop services:    docker compose down"
echo "   Update code:      git pull && docker compose up -d --build"
echo ""
