# Production Deployment Guide

## Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Python 3.10+
- MongoDB 5.0+
- Redis 6.0+
- Nginx
- SSL certificate (Let's Encrypt recommended)
- Domain name

## Step 1: Server Setup

### Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### Install Dependencies
```bash
# Python and pip
sudo apt install python3.10 python3.10-venv python3-pip -y

# MongoDB
wget -qO - https://www.mongodb.org/static/pgp/server-5.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/5.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-5.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod

# Redis
sudo apt install redis-server -y
sudo systemctl start redis
sudo systemctl enable redis

# Nginx
sudo apt install nginx -y
sudo systemctl start nginx
sudo systemctl enable nginx
```

## Step 2: Application Setup

### Create Application User
```bash
sudo useradd -m -s /bin/bash auction
sudo su - auction
```

### Clone and Setup Application
```bash
cd /home/auction
git clone <your-repo-url> cricket-auction
cd cricket-auction

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements-prod.txt
```

### Configure Environment
```bash
# Copy production environment template
cp .env.production .env

# Edit with your values
nano .env
```

**Important `.env` values to set:**
```bash
ENVIRONMENT=production
DEBUG=false
JWT_SECRET=<generate-strong-random-secret>
MONGODB_URL=mongodb://localhost:27017/cricket_auction
REDIS_URL=redis://localhost:6379/0
COOKIE_SECURE=true
COOKIE_SAMESITE=strict
CORS_ORIGINS=https://yourdomain.com
```

### Generate Strong JWT Secret
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Step 3: Database Setup

### Create MongoDB User
```bash
mongosh
```

```javascript
use cricket_auction

db.createUser({
  user: "auction_user",
  pwd: "STRONG_PASSWORD_HERE",
  roles: [
    { role: "readWrite", db: "cricket_auction" }
  ]
})

exit
```

### Update MongoDB URL in .env
```bash
MONGODB_URL=mongodb://auction_user:STRONG_PASSWORD_HERE@localhost:27017/cricket_auction
```

### Create Initial Admin User
```bash
source venv/bin/activate
python create_admin.py
```

## Step 4: Systemd Service

### Create Service File
```bash
sudo nano /etc/systemd/system/cricket-auction.service
```

```ini
[Unit]
Description=Cricket Auction Platform
After=network.target mongodb.service redis.service

[Service]
Type=notify
User=auction
Group=auction
WorkingDirectory=/home/auction/cricket-auction
Environment="PATH=/home/auction/cricket-auction/venv/bin"
ExecStart=/home/auction/cricket-auction/venv/bin/gunicorn main_new:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/auction/access.log \
    --error-logfile /var/log/auction/error.log \
    --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Create Log Directory
```bash
sudo mkdir -p /var/log/auction
sudo chown auction:auction /var/log/auction
```

### Enable and Start Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable cricket-auction
sudo systemctl start cricket-auction
sudo systemctl status cricket-auction
```

## Step 5: Nginx Configuration

### Create Nginx Config
```bash
sudo nano /etc/nginx/sites-available/cricket-auction
```

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=auction_limit:10m rate=10r/s;

# Upstream
upstream auction_backend {
    server 127.0.0.1:8000;
}

# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/auction_access.log;
    error_log /var/log/nginx/auction_error.log;

    # Max upload size
    client_max_body_size 10M;

    # Rate limiting
    limit_req zone=auction_limit burst=20 nodelay;

    # Static files
    location /static/ {
        alias /home/auction/cricket-auction/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # WebSocket
    location /auction/ws {
        proxy_pass http://auction_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # API
    location / {
        proxy_pass http://auction_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

### Enable Site
```bash
sudo ln -s /etc/nginx/sites-available/cricket-auction /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Step 6: SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## Step 7: Firewall Configuration

```bash
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

## Step 8: Database Backups

### Setup Cron Job
```bash
crontab -e
```

Add:
```cron
# Daily backup at 2 AM
0 2 * * * /home/auction/cricket-auction/venv/bin/python /home/auction/cricket-auction/scripts/backup_database.py >> /var/log/auction/backup.log 2>&1
```

### Test Backup
```bash
source venv/bin/activate
python scripts/backup_database.py
```

## Step 9: Monitoring Setup

### Install Monitoring Tools
```bash
# Prometheus Node Exporter
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvfz node_exporter-1.7.0.linux-amd64.tar.gz
sudo mv node_exporter-1.7.0.linux-amd64/node_exporter /usr/local/bin/
sudo useradd -rs /bin/false node_exporter

# Create systemd service
sudo nano /etc/systemd/system/node_exporter.service
```

```ini
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter
```

## Step 10: Health Checks

### Test Application
```bash
# Health check
curl https://yourdomain.com/health

# API test
curl https://yourdomain.com/auction/status
```

### Monitor Logs
```bash
# Application logs
sudo journalctl -u cricket-auction -f

# Nginx logs
sudo tail -f /var/log/nginx/auction_access.log
sudo tail -f /var/log/nginx/auction_error.log
```

## Maintenance

### Update Application
```bash
cd /home/auction/cricket-auction
git pull
source venv/bin/activate
pip install -r requirements-prod.txt
sudo systemctl restart cricket-auction
```

### View Service Status
```bash
sudo systemctl status cricket-auction
sudo systemctl status nginx
sudo systemctl status mongod
sudo systemctl status redis
```

### Database Maintenance
```bash
# Compact database
mongosh cricket_auction --eval "db.runCommand({compact: 'users'})"

# Check indexes
mongosh cricket_auction --eval "db.users.getIndexes()"
```

## Troubleshooting

### Application Won't Start
```bash
# Check logs
sudo journalctl -u cricket-auction -n 100

# Check permissions
ls -la /home/auction/cricket-auction

# Test manually
cd /home/auction/cricket-auction
source venv/bin/activate
python main_new.py
```

### Database Connection Issues
```bash
# Check MongoDB status
sudo systemctl status mongod

# Test connection
mongosh cricket_auction

# Check authentication
mongosh -u auction_user -p --authenticationDatabase cricket_auction
```

### High Memory Usage
```bash
# Check processes
htop

# Restart services
sudo systemctl restart cricket-auction
sudo systemctl restart redis
```

## Security Checklist

- [ ] Strong JWT secret generated
- [ ] HTTPS enabled with valid certificate
- [ ] Firewall configured
- [ ] MongoDB authentication enabled
- [ ] Redis password set (if exposed)
- [ ] Regular backups configured
- [ ] Log rotation configured
- [ ] Monitoring setup
- [ ] Rate limiting active
- [ ] Security headers configured
- [ ] File permissions correct
- [ ] Default passwords changed
- [ ] Admin accounts secured

## Performance Tuning

### Gunicorn Workers
```bash
# Calculate optimal workers: (2 x CPU cores) + 1
# For 4 cores: 9 workers
--workers 9
```

### MongoDB Indexes
```bash
mongosh cricket_auction
db.users.createIndex({"email": 1}, {unique: true})
db.players.createIndex({"status": 1, "auction_round": 1})
db.bid_history.createIndex({"player_id": 1, "timestamp": -1})
```

### Redis Configuration
```bash
sudo nano /etc/redis/redis.conf
```

```conf
maxmemory 256mb
maxmemory-policy allkeys-lru
```

## Support

For issues or questions:
- Check logs: `/var/log/auction/`
- Review documentation: `README.md`
- Contact: your-email@example.com
