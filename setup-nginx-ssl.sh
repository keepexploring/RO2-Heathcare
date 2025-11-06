#!/bin/bash
# Nginx and SSL Setup Script for RO2 Oxygen Monitoring System
# Run this on your Digital Ocean droplet as root

set -e  # Exit on any error

echo "🚀 Setting up Nginx reverse proxy with SSL for ro2.co.uk subdomains..."

# Configuration variables
MONITOR_DOMAIN="monitor.ro2.co.uk"
API_DOMAIN="api.ro2.co.uk"
MQTT_DOMAIN="mqtt.ro2.co.uk"
EMAIL="your-email@example.com"  # Change this for Let's Encrypt notifications

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (use: sudo bash setup-nginx-ssl.sh)"
    exit 1
fi

# Install Nginx and Certbot if not already installed
echo "📦 Installing Nginx and Certbot..."
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx

# Create Nginx config for monitor.ro2.co.uk (Panel Dashboard)
echo "📝 Creating Nginx config for $MONITOR_DOMAIN..."
cat > /etc/nginx/sites-available/$MONITOR_DOMAIN << 'EOF'
server {
    listen 80;
    server_name monitor.ro2.co.uk;

    location / {
        proxy_pass http://localhost:5006;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support for Panel dashboard
        proxy_read_timeout 86400;
    }
}
EOF

# Create Nginx config for api.ro2.co.uk (FastAPI Backend)
echo "📝 Creating Nginx config for $API_DOMAIN..."
cat > /etc/nginx/sites-available/$API_DOMAIN << 'EOF'
server {
    listen 80;
    server_name api.ro2.co.uk;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Create Nginx config for mqtt.ro2.co.uk (WebSocket MQTT on port 9001)
echo "📝 Creating Nginx config for $MQTT_DOMAIN (WebSocket)..."
cat > /etc/nginx/sites-available/$MQTT_DOMAIN << 'EOF'
server {
    listen 80;
    server_name mqtt.ro2.co.uk;

    location / {
        proxy_pass http://localhost:9001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket timeout
        proxy_read_timeout 86400;
    }
}
EOF

# Enable sites by creating symbolic links
echo "🔗 Enabling sites..."
ln -sf /etc/nginx/sites-available/$MONITOR_DOMAIN /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/$API_DOMAIN /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/$MQTT_DOMAIN /etc/nginx/sites-enabled/

# Remove default site
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
echo "🧪 Testing Nginx configuration..."
nginx -t

# Restart Nginx
echo "🔄 Restarting Nginx..."
systemctl restart nginx
systemctl enable nginx

echo ""
echo "✅ Nginx configured successfully!"
echo ""
echo "🌐 Your sites are now available at:"
echo "   - http://$MONITOR_DOMAIN (Panel Dashboard)"
echo "   - http://$API_DOMAIN (FastAPI Backend)"
echo "   - http://$MQTT_DOMAIN (MQTT WebSocket)"
echo ""
echo "📡 Plain MQTT is available at:"
echo "   - mqtt://$MQTT_DOMAIN:1883 (direct connection, no proxy needed)"
echo ""
echo "🔒 Now setting up SSL certificates..."
echo ""

# Prompt for email if not set
if [ "$EMAIL" = "your-email@example.com" ]; then
    read -p "Enter your email for Let's Encrypt notifications: " EMAIL
fi

# Get SSL certificates for all domains
echo "🔐 Obtaining SSL certificates from Let's Encrypt..."
certbot --nginx -d $MONITOR_DOMAIN -d $API_DOMAIN -d $MQTT_DOMAIN \
    --non-interactive \
    --agree-tos \
    --email $EMAIL \
    --redirect

echo ""
echo "🎉 Setup complete!"
echo ""
echo "🔒 Your sites are now available with SSL:"
echo "   - https://$MONITOR_DOMAIN (Panel Dashboard)"
echo "   - https://$API_DOMAIN (FastAPI Backend)"
echo "   - wss://$MQTT_DOMAIN (Secure WebSocket MQTT)"
echo ""
echo "📡 Plain MQTT (for IoT devices):"
echo "   - mqtt://$MQTT_DOMAIN:1883"
echo ""
echo "🔄 SSL certificates will auto-renew via certbot timer"
echo ""
echo "💡 Test your setup:"
echo "   - Dashboard: https://$MONITOR_DOMAIN"
echo "   - API Docs:  https://$API_DOMAIN/docs"
echo ""
