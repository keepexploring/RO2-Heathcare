# Deployment Guide - Digital Ocean Droplet

Complete guide for deploying the RO2 Oxygen Concentrator Monitoring System to a Digital Ocean Droplet.

## 🎯 Overview

This guide will help you deploy the complete monitoring system on a **$6/month Digital Ocean Droplet** with:
- ✅ Custom domain with SSL (ro2.co.uk subdomains)
- ✅ All 4 services (PostgreSQL, Mosquitto, FastAPI, Panel)
- ✅ Automated SSL certificate management
- ✅ Production-ready configuration

**Estimated setup time:** 30 minutes

---

## 📋 Prerequisites

### Required
- Digital Ocean account ([sign up here](https://www.digitalocean.com/))
- Domain name with Cloudflare DNS (we use ro2.co.uk)
- SSH client (Terminal on Mac/Linux, PuTTY on Windows)
- Basic command line knowledge

### Optional but Recommended
- SSH key pair for secure access
- Email address for SSL certificate notifications

---

## 🚀 Step 1: Create Digital Ocean Droplet

### Via Digital Ocean Dashboard

1. **Login** to [DigitalOcean Cloud](https://cloud.digitalocean.com/)

2. **Create Droplet**
   - Click **"Create"** → **"Droplets"**

3. **Choose Configuration:**
   - **Image**: Ubuntu 24.04 LTS (or 22.04 LTS)
   - **Plan**: Basic
   - **CPU Options**: Regular
   - **Size**: $6/month (1GB RAM, 25GB SSD, 1TB transfer)
   - **Datacenter**: Choose closest to your location
     - London (lon1) for UK
     - New York (nyc1/nyc3) for US East
     - San Francisco (sfo3) for US West

4. **Authentication**
   - **Recommended**: Add SSH Key
     - [How to add SSH keys](https://docs.digitalocean.com/products/droplets/how-to/add-ssh-keys/)
   - **Alternative**: Use password (sent via email)

5. **Additional Options**
   - **Hostname**: `oxygen-monitor` (or your preference)
   - **Tags**: `production`, `ro2`, `monitoring`

6. **Create Droplet**
   - Click "Create Droplet"
   - Wait ~60 seconds for provisioning

7. **Note your IP address** (e.g., `159.65.48.40`)

### Via CLI (Advanced)

```bash
# Install doctl
brew install doctl  # Mac
# OR: snap install doctl  # Linux

# Authenticate
doctl auth init

# Create droplet
doctl compute droplet create oxygen-monitor \
  --image ubuntu-24-04-x64 \
  --size s-1vcpu-1gb \
  --region lon1 \
  --ssh-keys $(doctl compute ssh-key list --format ID --no-header)

# Get IP address
doctl compute droplet list
```

---

## 🌐 Step 2: Configure DNS with Cloudflare

### Add Subdomains

1. **Login to Cloudflare**
   - Go to https://dash.cloudflare.com
   - Select your domain (ro2.co.uk)

2. **Navigate to DNS**
   - Click **"DNS"** in left sidebar

3. **Add A Records**

   Add these three records:

   | Type | Name | IPv4 Address | Proxy Status | TTL |
   |------|------|--------------|--------------|-----|
   | A | `monitor` | `YOUR_DROPLET_IP` | 🌥️ Proxied | Auto |
   | A | `api` | `YOUR_DROPLET_IP` | 🌥️ Proxied | Auto |
   | A | `mqtt` | `YOUR_DROPLET_IP` | ☁️ DNS only ⚠️ | Auto |

   **IMPORTANT:**
   - Replace `YOUR_DROPLET_IP` with actual IP (e.g., `159.65.48.40`)
   - **`mqtt` must be DNS only** (grey cloud) - MQTT protocol doesn't work through Cloudflare proxy
   - Click the orange cloud next to `mqtt` to toggle it to grey

4. **Save**

5. **Wait for DNS Propagation** (5-10 minutes)
   - Test with: `dig monitor.ro2.co.uk` or `nslookup monitor.ro2.co.uk`

---

## 🔐 Step 3: Connect to Droplet

### SSH into Droplet

```bash
ssh root@YOUR_DROPLET_IP
```

Replace `YOUR_DROPLET_IP` with your actual IP.

**First-time connection:**
- Type `yes` when asked about host authenticity
- Enter password if using password authentication (check email from DO)
- SSH key users connect automatically

**You should see:**
```
root@oxygen-monitor:~#
```

---

## 📦 Step 4: Initial Server Setup

### Update System & Install Docker

```bash
# Update package lists and upgrade system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose plugin
apt-get install -y docker-compose-plugin

# Install Git
apt-get install -y git

# Verify installations
docker --version
docker compose version
git --version
```

**Expected output:**
```
Docker version 24.x.x
Docker Compose version v2.x.x
git version 2.x.x
```

---

## 📥 Step 5: Clone Repository

```bash
# Clone the repository
git clone https://github.com/keepexploring/RO2-Heathcare.git

# Navigate to project directory
cd RO2-Heathcare/sensing

# List files to verify
ls -la
```

**You should see:**
```
docker-compose.production.yml
setup-nginx-ssl.sh
.env.production
fastapi/
panel/
mosquitto/
```

---

## ⚙️ Step 6: Configure Environment Variables

### Create Production Environment File

```bash
# Copy template to .env
cp .env.production .env

# Edit with nano
nano .env
```

### Set Your Values

Update these critical values:

```env
# PostgreSQL Database Password
# Use a strong random password
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE

# JWT Secret for Authentication
# Generate with: openssl rand -base64 32
JWT_SECRET=YOUR_JWT_SECRET_HERE

# User Credentials (JSON format)
# Change admin and user passwords
USERS={"admin": "YOUR_ADMIN_PASSWORD", "user": "YOUR_USER_PASSWORD"}
```

### Generate Secure Secrets

```bash
# Generate PostgreSQL password
openssl rand -base64 32

# Generate JWT secret
openssl rand -base64 32
```

Copy the outputs and paste into `.env` file.

### Save and Exit

- Press `Ctrl+O` to save
- Press `Enter` to confirm
- Press `Ctrl+X` to exit

### Verify Configuration

```bash
cat .env
```

Ensure no `CHANGE_ME` placeholders remain.

---

## 🐳 Step 7: Start Docker Services

```bash
# Start all services (PostgreSQL, Mosquitto, FastAPI, Panel)
docker compose -f docker-compose.production.yml up -d --build
```

**This will:**
1. Build FastAPI and Panel Docker images (~2-3 minutes)
2. Pull PostgreSQL and Mosquitto images
3. Create Docker network and volumes
4. Start all 4 containers

**Expected output:**
```
✔ Network ro2-heathcare_app-network    Created
✔ Volume ro2-heathcare_pgdata          Created
✔ Volume ro2-heathcare_mosquitto-data  Created
✔ Container postgres                   Healthy
✔ Container mosquitto                  Healthy
✔ Container fastapi                    Started
✔ Container panel                      Started
```

### Verify Services Running

```bash
docker compose -f docker-compose.production.yml ps
```

All services should show **"running"** status.

### Check Logs

```bash
# View all logs
docker compose -f docker-compose.production.yml logs

# Follow specific service logs
docker compose -f docker-compose.production.yml logs -f fastapi
docker compose -f docker-compose.production.yml logs -f panel
```

Look for:
- ✅ "Connected to MQTT broker" in FastAPI logs
- ✅ No error messages

Press `Ctrl+C` to stop following logs.

---

## 🔒 Step 8: Set Up Nginx Reverse Proxy & SSL

### Run Automated Setup Script

```bash
# Make script executable
chmod +x setup-nginx-ssl.sh

# Run the setup script
bash setup-nginx-ssl.sh
```

**The script will:**
1. Install Nginx and Certbot
2. Configure reverse proxy for all 3 domains
3. Ask for your email (for SSL certificate notifications)
4. Obtain free SSL certificates from Let's Encrypt
5. Set up automatic HTTP → HTTPS redirect
6. Configure auto-renewal for certificates

**When prompted for email:**
```
Enter your email for Let's Encrypt notifications: your-email@example.com
```

**Expected output:**
```
✅ Nginx configured successfully!
🔒 Obtaining SSL certificates...
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/monitor.ro2.co.uk/fullchain.pem

🎉 Setup complete!
```

### Manual Setup (Alternative)

If the script fails, see [Manual Nginx Setup](#manual-nginx-setup) section below.

---

## 🔥 Step 9: Configure Firewall

Secure your droplet by restricting open ports:

```bash
# Allow SSH (IMPORTANT: Do this first!)
ufw allow OpenSSH

# Allow HTTP and HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow MQTT
ufw allow 1883/tcp
ufw allow 9001/tcp

# Enable firewall
ufw enable

# Verify status
ufw status
```

**Expected output:**
```
Status: active

To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
1883/tcp                   ALLOW       Anywhere
9001/tcp                   ALLOW       Anywhere
```

---

## ✅ Step 10: Verify Deployment

### Test Web Interfaces

**Open in your browser:**

1. **Dashboard**: https://monitor.ro2.co.uk
   - Should show login page
   - Login with credentials from `.env`
   - Should display empty dashboard (no data yet)

2. **API Documentation**: https://api.ro2.co.uk/docs
   - Should show Swagger UI
   - Interactive API documentation

3. **Health Check**: https://api.ro2.co.uk/health
   - Should return: `{"status": "healthy"}`

### Test MQTT Connection

From your **local machine**:

```bash
# Using Python script (recommended)
python test_mqtt_publish.py

# Using mosquitto_pub
mosquitto_pub -h mqtt.ro2.co.uk -t "sensors/comprehensive" -m '{
  "temperature": 25.3,
  "humidity": 65.2,
  "system_in_use": true,
  "oxygen_level": 95.5,
  "oxygen_concentrator_id": "OXY-001"
}'
```

**Refresh dashboard** - data should appear!

### Check Logs for Errors

```bash
# Check FastAPI received MQTT message
docker compose -f docker-compose.production.yml logs fastapi | grep "Saved"

# Should show:
# 📥 Saved from sensors/comprehensive: temp: 25.3°C, humidity: 65.2%, IN USE, O2: 95.5% (ID: OXY-001)
```

---

## 🎉 Deployment Complete!

Your oxygen concentrator monitoring system is now live!

### Access Points

- 🌐 **Dashboard**: https://monitor.ro2.co.uk
- 🌐 **API**: https://api.ro2.co.uk/docs
- 📡 **MQTT**: `mqtt://mqtt.ro2.co.uk:1883`
- 🔒 **MQTT WebSocket**: `wss://mqtt.ro2.co.uk`

### Next Steps

1. ✅ Send test data using `test_mqtt_publish.py`
2. ✅ Configure your IoT devices to publish to `mqtt.ro2.co.uk:1883`
3. ✅ Set up monitoring/alerting (optional)
4. ✅ Configure automated backups (optional)

---

## 🛠️ Maintenance & Operations

### Update Application Code

```bash
cd ~/RO2-Heathcare/sensing
git pull
docker compose -f docker-compose.production.yml up -d --build
```

### View Logs

```bash
# All services
docker compose -f docker-compose.production.yml logs -f

# Specific service
docker compose -f docker-compose.production.yml logs -f fastapi
docker compose -f docker-compose.production.yml logs -f panel
docker compose -f docker-compose.production.yml logs -f mosquitto
docker compose -f docker-compose.production.yml logs -f postgres
```

### Restart Services

```bash
# Restart all
docker compose -f docker-compose.production.yml restart

# Restart specific service
docker compose -f docker-compose.production.yml restart fastapi
```

### Stop Services

```bash
# Stop all (data persists in volumes)
docker compose -f docker-compose.production.yml down

# Start again
docker compose -f docker-compose.production.yml up -d
```

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
df -h

# Memory usage
free -h

# System monitor
htop  # Install with: apt-get install htop
```

---

## 💾 Backup & Restore

### Backup Database

```bash
# Create backup
docker compose -f docker-compose.production.yml exec postgres pg_dump \
  -U postgres sensordb > backup-$(date +%Y%m%d-%H%M%S).sql

# List backups
ls -lh backup-*.sql
```

### Restore Database

```bash
# Restore from backup
docker compose -f docker-compose.production.yml exec -T postgres psql \
  -U postgres sensordb < backup-20250106-120000.sql
```

### Automated Backups (Optional)

Create a cron job for daily backups:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd ~/RO2-Heathcare/sensing && docker compose -f docker-compose.production.yml exec -T postgres pg_dump -U postgres sensordb > ~/backups/sensor-$(date +\%Y\%m\%d).sql
```

---

## 🔍 Troubleshooting

### Services Won't Start

```bash
# Check container status
docker compose -f docker-compose.production.yml ps

# View full logs
docker compose -f docker-compose.production.yml logs

# Check specific service
docker compose -f docker-compose.production.yml logs postgres
```

### Port Already in Use

```bash
# Check what's using a port
sudo lsof -i :5006
sudo lsof -i :8000
sudo lsof -i :1883

# Kill process if needed
sudo kill -9 PID
```

### SSL Certificate Issues

```bash
# Test SSL certificate
certbot certificates

# Renew manually
certbot renew --dry-run

# Force renewal
certbot renew --force-renewal
```

### Database Connection Errors

```bash
# Test database connection
docker compose -f docker-compose.production.yml exec postgres psql -U postgres -c "SELECT version();"

# Check if database exists
docker compose -f docker-compose.production.yml exec postgres psql -U postgres -c "\l"

# Recreate database
docker compose -f docker-compose.production.yml exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS sensordb;"
docker compose -f docker-compose.production.yml exec postgres psql -U postgres -c "CREATE DATABASE sensordb;"
```

### MQTT Not Receiving Messages

```bash
# Check Mosquitto logs
docker compose -f docker-compose.production.yml logs mosquitto

# Test MQTT locally on droplet
docker compose -f docker-compose.production.yml exec mosquitto mosquitto_sub -h localhost -t "sensors/#" -v

# Check FastAPI MQTT connection
docker compose -f docker-compose.production.yml logs fastapi | grep MQTT
```

### Domain Not Resolving

```bash
# Check DNS from droplet
dig monitor.ro2.co.uk
nslookup monitor.ro2.co.uk

# Check Nginx configuration
nginx -t

# Restart Nginx
systemctl restart nginx
```

---

## 📊 Monitoring (Optional)

### Set Up DigitalOcean Monitoring

1. Go to droplet dashboard
2. Click **"Monitoring"**
3. Enable monitoring and alerts
4. Set up alerts for:
   - CPU usage > 80%
   - Memory usage > 80%
   - Disk usage > 80%

### Log Monitoring

```bash
# Install logwatch
apt-get install -y logwatch

# Run daily report
logwatch --detail high --mailto your-email@example.com
```

---

## 💰 Cost Breakdown

| Component | Monthly Cost |
|-----------|--------------|
| DO Droplet (1GB RAM) | $6.00 |
| SSL Certificates | Free (Let's Encrypt) |
| Domain DNS | $0 (using existing ro2.co.uk) |
| **Total** | **$6.00/month** |

---

## 🔒 Security Checklist

- [x] Strong passwords in `.env`
- [x] Random JWT secret (32+ characters)
- [x] UFW firewall enabled
- [x] SSH key authentication (recommended)
- [x] SSL/TLS certificates installed
- [x] HTTP→HTTPS redirect enabled
- [ ] Set up fail2ban (optional)
- [ ] Regular security updates (`apt-get update && apt-get upgrade`)
- [ ] Database backups automated
- [ ] Monitoring alerts configured

---

## 📞 Support

- **GitHub Issues**: https://github.com/keepexploring/RO2-Heathcare/issues
- **DigitalOcean Docs**: https://docs.digitalocean.com
- **Let's Encrypt**: https://letsencrypt.org/docs

---

## 📎 Appendices

### Manual Nginx Setup

If the automated script fails, configure manually:

```bash
# Create monitor.ro2.co.uk config
nano /etc/nginx/sites-available/monitor.ro2.co.uk
```

Paste:
```nginx
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
        proxy_read_timeout 86400;
    }
}
```

Repeat for `api.ro2.co.uk` and `mqtt.ro2.co.uk`, then:

```bash
# Enable sites
ln -s /etc/nginx/sites-available/monitor.ro2.co.uk /etc/nginx/sites-enabled/
ln -s /etc/nginx/sites-available/api.ro2.co.uk /etc/nginx/sites-enabled/
ln -s /etc/nginx/sites-available/mqtt.ro2.co.uk /etc/nginx/sites-enabled/

# Test and restart
nginx -t
systemctl restart nginx

# Get SSL certificates
certbot --nginx -d monitor.ro2.co.uk -d api.ro2.co.uk -d mqtt.ro2.co.uk \
  --email your-email@example.com --agree-tos --redirect
```

### Environment Variables Reference

**Complete list of environment variables:**

```env
# Database
POSTGRES_PASSWORD=secure-password-here
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/sensordb

# JWT Authentication
JWT_SECRET=random-32-char-secret
USERS={"admin": "admin-password", "user": "user-password"}

# MQTT
MQTT_BROKER_URL=mosquitto
MQTT_BROKER_PORT=1883

# FastAPI (Panel needs this)
FASTAPI_URL=https://api.ro2.co.uk
```

---

**Your RO2 Oxygen Concentrator Monitoring System is now deployed and running! 🚀**
