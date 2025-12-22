# Deployment Guide – Balaur SMS

## 📋 Prerequisites

### Required Software

* Python 3.12+
* PostgreSQL 15+
* LDAP/Active Directory server configured
* FTP/FTPS server (ProFTPD, vsftpd, or similar)
* nginx (recommended as reverse proxy)
* systemd (to run as a service)

### Recommended Hardware (on-premise)

* CPU: 4 cores
* RAM: minimum 8GB
* Disk: 500GB+ (depending on installer volume)
* Network: 1Gbps

## Pre-Installation Checklist

- [ ] Server with Ubuntu 22.04 LTS or newer
- [ ] Root/sudo access
- [ ] Domain name configured (A record pointing to server)
- [ ] Active Directory accessible from server
- [ ] Firewall ports open (80, 443, 21, 49152-65534)
- [ ] At least 8GB RAM and 4 CPU cores
- [ ] 500GB+ available disk space

---

## Architecture

```
┌─────────────┐
│   Clients   │
└──────┬──────┘
       │ HTTPS (443)
       ▼
┌─────────────┐
│   Nginx     │ ← Reverse Proxy
│  (SSL/TLS)  │
└──────┬──────┘
       │
       ├─────► /api → Backend (FastAPI:8000)
       │
       └─────► / → Frontend (Vue SPA)

┌─────────────┐
│  ProFTPD    │ ← FTP/FTPS (21, 990, passive)
│ + LDAP Auth │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│    File System              │
│  /srv/ftp/balaur/           │
│  ├── inbox/                 │
│  │   ├── pending/   ← FTP uploads
│  │   └── processing/ ← Watcher moves here
│  ├── repository/    ← Registered installers
│  └── quarantine/    ← Failed validations
└─────────────────────────────┘

┌─────────────┐
│ PostgreSQL  │ ← Database
└─────────────┘

┌─────────────┐
│ Active Dir. │ ← LDAP/AD for auth
└─────────────┘
```
---

## 🔧 Step-by-Step Installation

### 1. Prepare the System

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3 python3-venv python3-pip postgresql nginx git

# Create user app
sudo useradd -m -s /bin/bash balaur-app
```

---

### 2. Configure PostgreSQL

```bash
# Create user and database
sudo -u postgres psql

CREATE USER balaur WITH PASSWORD 'your_secure_password';
CREATE DATABASE balaur_sms OWNER balaur;
GRANT ALL PRIVILEGES ON DATABASE balaur_sms TO balaur;
\c balaur_sms
GRANT ALL ON SCHEMA public TO balaur;
\q
```

---

### 3. Configure FTP/FTPS

#### 3.1. Install ProFTPD

```bash
# Install ProFTPD with TLS support
sudo apt install -y proftpd openssl proftpd-mod-ldap

# Generate SSL certificate for FTPS (or use a real certificate)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/proftpd.key \
  -out /etc/ssl/certs/proftpd.crt \
  -subj "/CN=ftp.balaur.local"
```

#### 3.2. Create FTP users and groups

```bash
sudo useradd -m -d /srv/ftp/balaur -s /bin/bash balaur
sudo groupadd balaur-upload
sudo groupadd balaur-download
sudo usermod -a -G balaur-upload,balaur-download balaur
sudo usermod -a -G balaur-upload,balaur-download balaur-app
```

#### 3.3. Create directory structure

```bash
# Create FTP structure
sudo mkdir -p /srv/ftp/balaur/{inbox/{pending,processing},repository,quarantine}

# Adjust permissions (IMPORTANT for backend access)
sudo chown -R balaur:balaur /srv/ftp
sudo chmod 775 /srv/ftp
sudo chown -R balaur:balaur /srv/ftp/balaur
sudo chmod 775 /srv/ftp/balaur
sudo chown -R balaur:balaur-upload /srv/ftp/balaur/inbox
sudo chmod 775 /srv/ftp/balaur/inbox
sudo chmod 775 /srv/ftp/balaur/inbox/pending
sudo chmod 775 /srv/ftp/balaur/inbox/processing
sudo chown -R balaur:balaur-download /srv/ftp/balaur/repository
sudo chmod 775 /srv/ftp/balaur/repository
sudo chmod 775 /srv/ftp/balaur/quarantine
sudo chmod -R g+rw /srv/ftp/balaur
# Setgid for directory group inheritance
sudo chmod g+s /srv/ftp/balaur/inbox/pending
sudo chmod g+s /srv/ftp/balaur/inbox/processing
sudo chmod g+s /srv/ftp/balaur/quarantine
```

#### 3.4. Configure ProFTPD

Create `/etc/proftpd/proftpd.conf`:


```apache
Include /etc/proftpd/modules.conf

UseIPv6 on
ServerName "Balaur SMS FTP Server"
ServerType standalone
DefaultServer on
ShowSymlinks on

Port 21
PassivePorts 49152 65534

TimeoutNoTransfer 600
TimeoutStalled 600
TimeoutIdle 1200

MaxInstances 30
User proftpd
Group nogroup
Umask 022 022
AllowOverwrite on
RequireValidShell off

TransferLog /var/log/proftpd/xferlog
SystemLog /var/log/proftpd/proftpd.log

# TLS
Include /etc/proftpd/tls.conf

# Root del FTP
DefaultRoot /srv/ftp/balaur

# Logs Balaur
ExtendedLog /var/log/proftpd/balaur-access.log WRITE,READ
ExtendedLog /var/log/proftpd/balaur-auth.log AUTH auth

# ==========================
# inbox/pending (uploads)
# ==========================
<Directory /srv/ftp/balaur/inbox/pending>
  <Limit ALL>
    AllowUser balaur
    AllowGroup balaur-upload
  </Limit>

  <Limit STOR STOU>
    AllowAll
  </Limit>

  <Limit DELE RNFR RNTO>
    DenyAll
  </Limit>

  <Limit LIST NLST>
    DenyAll
  </Limit>
</Directory>

# ==========================
# processing (backend only)
# ==========================
<Directory /srv/ftp/balaur/inbox/processing>
  <Limit ALL>
    DenyAll
  </Limit>
</Directory>

# ==========================
# repository (downloads)
# ==========================
<Directory /srv/ftp/balaur/repository>
  <Limit ALL>
    AllowUser balaur
    AllowGroup balaur-download
  </Limit>

  <Limit RETR>
    AllowAll
  </Limit>

  <Limit WRITE STOR STOU DELE RNFR RNTO MKD RMD>
    DenyAll
  </Limit>

  <Limit LIST NLST>
    AllowAll
  </Limit>
</Directory>

# ==========================
# quarantine (admin)
# ==========================
<Directory /srv/ftp/balaur/quarantine>
  <Limit ALL>
    AllowUser root
    DenyAll
  </Limit>
</Directory>

# Seguridad
PathDenyFilter "(\\.\\./|/\\.\\./)"
PathDenyFilter "^\\."

<Directory /srv/ftp/balaur/*>
  HideFiles ^\.
</Directory>
```

Create `/etc/proftpd/tls.conf`:

```apache
#
# ProFTPD TLS/FTPS Configuration
#

<IfModule mod_tls.c>
  TLSEngine                     on
  TLSLog                        /var/log/proftpd/tls.log
  TLSProtocol                   TLSv1.2 TLSv1.3
  TLSCipherSuite                HIGH:!aNULL:!MD5:!DES:!3DES:!RC4
  TLSRSACertificateFile         /etc/ssl/certs/proftpd.crt
  TLSRSACertificateKeyFile      /etc/ssl/private/proftpd.key
  TLSVerifyClient               off
  TLSRequired                   on
  TLSOptions                    NoSessionReuseRequired
  TLSRenegotiate                none
  TLSSessionCache               shm:/file=/var/run/proftpd/tls-sesscache
  TLSTimeoutHandshake           30
</IfModule>
```

#### 3.5. Restart ProFTPD

```bash
# Check configuration
sudo proftpd -t

# Restart service
sudo systemctl restart proftpd
sudo systemctl enable proftpd
sudo systemctl status proftpd
```

#### 3.6. Manual Test

```bash
# As user balaur-app (created in step 1)
sudo -u balaur-app bash

# Try to create a file in pending
touch /srv/ftp/balaur/inbox/pending/test.txt

# Try to move to processing
mv /srv/ftp/balaur/inbox/pending/test.txt /srv/ftp/balaur/inbox/processing/

# If it works, permissions are OK
```

#### 3.7. FTP Permission Summary

```bash
System users:
  balaur-app (run FastAPI/Gunicorn)
  balaur (owner of FTP files)

Groups:
  balaur-upload (FTP user + balaur-app)
  balaur-download (FTP user + balaur-app)

Directories:
  /srv/ftp/balaur/inbox/pending/     → 2775 (rwxrwsr-x) balaur:balaur-upload
  /srv/ftp/balaur/inbox/processing/  → 2775 (rwxrwsr-x) balaur:balaur-upload  
  /srv/ftp/balaur/repository/        → 0755 (rwxr-xr-x) balaur:balaur-download
  /srv/ftp/balaur/quarantine/        → 2775 (rwxrwsr-x) balaur:balaur-upload
```

---

### 4. Install Backend Application

# 4.1 Create directories

```bash
sudo mkdir -p /var/log/balaur/{backend,frontend}
sudo mkdir -p /opt/balaur

# Dar permisos
sudo chown -R balaur-app:balaur-app /var/log/balaur
sudo chown -R balaur-app:balaur-app /opt/balaur
```

# 4.2 Clone the repository

```bash
sudo su - balaur-app
cd /opt

# Clone repository
git clone https://github.com/rodricaybara/balaur.git .

```

# 4.3 Create the virtual environment and install dependencies

```bash
cd /opt/balaur/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Update pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# logout
exit
```

**Important:** Specific versions of `bcrypt` and `passlib` are required due to incompatibilities between bcrypt 5.0+ and passlib.

### 5. Configure Application with Secure Secrets Management

#### 5.1. Run Automatic Setup Script

```bash
cd /opt/balaur/backend
sudo chmod +x scripts/setup_secrets.sh
sudo ./scripts/setup_secrets.sh

# Requests encryption and verification password
# Generates a random password for the database user balaur and one for the FTP user balaur
```

This script:
- ✅ Automatically generates secure passwords
- ✅ Generates security keys (SECRET_KEY, ENCRYPTION_KEY)
- ✅ Configures PostgreSQL with the credentials
- ✅ Configures the FTP user
- ✅ Creates a complete `.env` file
- ✅ Saves everything to a vault encrypted with AES-256

**Note:** Save the vault password in a secure location (password manager). You will need it to decrypt the credentials later.

```bash
openssl enc -aes-256-cbc -d -pbkdf2 -in /opt/balaur/secrets/credentials.vault
```

#### 5.2. Configure LDAP/Active Directory

Edit the `.env` file with your organization's settings:

```bash
sudo nano /opt/balaur/backend/.env
```
**Example**

```bash
# LDAP Configuration
LDAP_SERVER=ldaps://dc.university.edu:636
LDAP_BIND_DN=cn=balaur-service,ou=Service Accounts,dc=university,dc=edu
LDAP_BIND_PASSWORD=<generado por setup_secrets.sh>
LDAP_SEARCH_BASE=dc=university,dc=edu
LDAP_SEARCH_FILTER=(sAMAccountName={username})
LDAP_USE_TLS=true
```

**Note:** For Microsoft Active Directory:
- Use `sAMAccountName` as a search filter (not `uid`)
- The object class is `user` (not `inetOrgPerson`)
- If using LDAPS (port 636), configure SSL certificates appropriately

#### 5.3. Test LDAP configuration

```bash
sudo su - balaur-app
cd /opt/balaur/backend
source venv/bin/activate
python3 scripts/test_ldap.py <your_user> <your_password>
exit
```

You should see:
```
✓ Service account bind successful
✓ User found!
✓ User authentication successful!
✓ ALL TESTS PASSED
```

#### 5.4. Secrets Management Scripts

**View Credentials (when necessary):**
```bash
sudo chmod 775 /opt/balaur/backend/scripts/view_secrets.sh
sudo /opt/balaur/backend/scripts/view_secrets.sh
```

**Rotate Passwords Periodically:**
```bash
sudo chmod 775 /opt/balaur/backend/scripts/rotate_password.sh
# Rotate database only
sudo /opt/balaur/backend/scripts/rotate_password.sh db

# Rotate FTP only
sudo /opt/balaur/backend/scripts/rotate_password.sh ftp

# Rotate everything
sudo /opt/balaur/backend/scripts/rotate_password.sh all
```

#### 5.5 Protect .env file

```bash
sudo chown balaur-app:balaur-app /opt/balaur/backend/.env
sudo chmod 600 /opt/balaur/backend/.env
```

---

### 6. Initialize Database

#### 6.1. Configure Alembic

The configuration files should already be in the repository. Verify:

```bash
ls -la /opt/balaur/backend/alembic/env.py
ls -la /opt/balaur/backend/alembic.ini
```

#### 6.2. Create Initial Migration

```bash
sudo su - balaur-app
cd /opt/balaur/backend
source venv/bin/activate
mkdir alembic/versions
```

```bash
# Run migrations
alembic upgrade head

# Generate migration from models
alembic revision --autogenerate -m "Initial schema"
exit
```

**Important Note:** The `DATABASE_URL` variable in `.env` must be in **plain text** for Alembic to read it. This is a known limitation of Alembic (it cannot read encrypted credentials from the vault).

#### 6.3. Apply migrations

```bash
alembic upgrade head
```

You should see:
```
INFO [alembic.runtime.migration] Running upgrade -> abc123, Initial schema
```

#### 6.4. Verify database structure

```bash
sudo -u postgres psql balaur_sms

# List tables
\dt

# View table structure
\d users

\q
```

#### 6.5. Initializing Sample Data

You need to install the following libraries: aiofiles and apscheduler

```bash
sudo su - balaur-app
cd /opt/balaur/backend
source venv/bin/activate
python3 scripts/init_db.py
exit
```

Answer `yes` when prompted. The script will create:
- 4 test users (admin, manager, user, guest)
- 5 sample software applications
- 3 sample licenses

**Default Credentials:**
- Admin: `admin / Admin123!`
- Manager: `manager / Manager123!`
- User: `user / User123!`
- Guest: `guest / Guest123!`

⚠️ **IMPORTANT:** Change these passwords in production.

#### 6.6. Cleanup Script (Development)

If you need to reset the data during development:

```bash
sudo -u postgres psql balaur_sms << EOF
TRUNCATE TABLE users RESTART IDENTITY CASCADE;

TRUNCATE TABLE software RESTART IDENTITY CASCADE;

TRUNCATE TABLE licenses RESTART IDENTITY CASCADE;

EOF
```

Then run `python3 scripts/init_db.py` again.

---

### 7. Configure systemd Service

#### 7.1. Create service file

```bash
sudo nano /etc/systemd/system/balaur-backend.service
```

Content:

```ini
[Unit]
Description=Balaur SMS Backend - Software Management System
After=network.target postgresql.service

[Service]
Type=notify
User=balaur-app
Group=balaur-app
WorkingDirectory=/opt/balaur/backend
Environment="PATH=/opt/balaur/backend/venv/bin"
Environment="PYTHONPATH=/opt/balaur/backend"

ExecStart=/opt/balaur/backend/venv/bin/gunicorn -c /opt/balaur/backend/gunicorn.conf.py app.main:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target


Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

The /opt/balaur/backend/gunicorn.conf.py configuration file :

```bash
sudo nano /opt/balaur/backend/gunicorn.conf.py
```

```bash
bind="0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "/var/log/balaur/backend/access.log"
errorlog = "/var/log/balaur/backend/error.log"
loglevel="info"
timeout = 300

```

```bash
sudo chown balaur-app:balaur-app /opt/balaur/backend/gunicorn.conf.py
```

#### 7.2. Enable and start service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto start
sudo systemctl enable balaur-backend

# Start service
sudo systemctl start balaur-backend

# Check status
sudo systemctl status balaur-backend
```

You should see:
```
● balaur-backend.service – Balaur SMS Backend 
Loaded: loaded 
Active: active (running)
```

#### 7.3. View logs

```bash
# Systemd service logs
sudo journalctl -u balaur-backend -f

# Application logs
tail -f /var/log/balaur/backend/access.log
tail -f /var/log/balaur/backend/error.log
```

#### 7.4. Testing the API

```bash
# Health check
`curl http://localhost:8000/health

# Interactive documentation (ONLY in development environments)
`curl http://localhost:8000/docs
```

Or open in browser: `http://localhost:8000/docs`

---

### 8. Install frontend (Vue + Vite)

# 8.1 Install Node.js 20

```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
```

# 8.2 build the frontend

```bash
sudo su - balaur-app
cd /opt/balaur/frontend
npm install
npm run build
exit
```

Make sure you have a valid .env file:

```bash
VITE_API_BASE_URL=/api/v1
VITE_APP_NAME=Balaur SMS
```

⚠️ Very important: delete .env.production and .env.development if they are not in use, as Vite prioritizes them.

# 8.3 SSL certificate autogenerated (test only)

```bash
sudo openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout /etc/ssl/private/balaur-selfsigned.key \
  -out /etc/ssl/certs/balaur-selfsigned.crt
```

# 8.4 Nginx configuration

Create the /etc/nginx/sites-available/balaur-sms file

```bash
sudo nano /etc/nginx/sites-available/balaur-sms
```

```bash
# /etc/nginx/sites-available/balaur-sms
upstream balaur_backend {
    server 127.0.0.1:8000;
    keepalive 16;
}

server {
    listen 80;
    server_name <SERVER_NAME OR IP>;

    # Redirect all HTTP to HTTPS
    location /.well-known/acme-challenge/ {
        # allow certbot to verify challenges
        root /var/www/letsencrypt;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name <SERVER_NAME OR IP>;

    ssl_certificate /etc/ssl/certs/balaur-selfsigned.crt;
    ssl_certificate_key /etc/ssl/private/balaur-selfsigned.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Logs
    access_log /var/log/nginx/balaur-access.log;
    error_log  /var/log/nginx/balaur-error.log warn;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    # Optionally add a Content-Security-Policy (adapt to your assets/domains)
    # add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:;connect-src 'self' https://balaur.university.edu;" always;

    # Frontend (SPA) - serve static files
    root /opt/balaur/frontend/dist;
    index index.html;

    # Serve static assets with long cache (assume assets fingerprinted)
    location ~* \.(?:css|js|svg|ico|png|jpg|jpeg|webp|woff2?|ttf|otf)$ {
        try_files $uri =404;
        expires 365d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # HTML and SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy to FastAPI
    location /api/ {
        proxy_pass http://balaur_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_buffering off;

        # Uploads/timeouts for large files
        client_max_body_size 10G;
        client_body_timeout 300s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;

        # Websocket support (if backend uses websockets)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Optional docs endpoints (disable in production if DOCS_ENABLED=False)
    location /docs {
        proxy_pass http://balaur_backend/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /redoc {
        proxy_pass http://balaur_backend/redoc;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Health check (internal)
    location = /health {
        proxy_pass http://balaur_backend/health;
        proxy_set_header Host $host;
    }

    # Deny access to sensitive files
    location ~ (^|/)\.env$ {
        deny all;
        access_log off;
        log_not_found off;
    }

    # Rate limiting (optional)
    # limit_req_zone $binary_remote_addr zone=one:10m rate=30r/m;
    # location /api/ {
    #     limit_req zone=one burst=20 nodelay;
    # }
}
```

#### 8.5. Enable Site

```bash
# Create symbolic link
sudo ln -s /etc/nginx/sites-available/balaur-sms /etc/nginx/sites-enabled/

# Verify configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## 9. Post-Installation Security

### 9.1. Firewall

```bash
# Configure UFW
sudo ufw allow 22/tcp # SSH
sudo ufw allow 80/tcp # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw allow 21/tcp # FTP control
sudo ufw allow 49152:65534/tcp # FTP passive ports
sudo ufw enable
sudo ufw status
```

### 9.2. Fail2ban

```bash
sudo apt install -y fail2ban

# Configure jail for nginx, SSH and ProFTPD
sudo nano /etc/fail2ban/jail.local
```

Content:

```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[proftpd]
enabled = true
```

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 10. Monitoring & Maintenance

### 10.1. Log Rotation

```bash
sudo nano /etc/logrotate.d/balaur-sms
```

Contents:

```
/var/log/balaur/backend/*.log {
daily
rotate 30
compress
delaycompress
notifempty
create 0640 balaur-app balaur-app
sharedscripts
postrotate
systemctl reload balaur-backend > /dev/null 2>&1 || true
endscript
}

/var/log/proftpd/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 proftpd proftpd
    sharedscripts
    postrotate
        systemctl reload proftpd > /dev/null 2>&1 || true
    endscript
}

/var/log/nginx/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}
```


### 10.2. Health Checks

```bash
# Verify that the API is responding
curl -f http://localhost:8000/health || echo "API is down!"

# Create systemd timer for automatic health check (optional)
```

### 10.3 CORS
You need to configure de CORS in the backend .env file. Add the IP of the server:

```bash
CORS_ORIGINS=["http://localhost:3000","https://localhost:3000", "http://<IP_SERVER or SERVER_NAME>", "https://<IP_SERVER or SERVER_NAME>"]
```

### 10.4. View logs in real time

```bash
# Backend logs
sudo journalctl -u balaur-backend -f

# nginx logs
sudo tail -f /var/log/nginx/balaur-error.log

# PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-15-main.log

# ProFTPD logs
sudo tail -f /var/log/proftpd/proftpd.log
```

### 10.5. Check service status

```bash
sudo systemctl status balaur-backend
sudo systemctl status postgresql
sudo systemctl status nginx
sudo systemctl status proftpd
```

---

## 11. Updates

```bash
#1. Stop service
sudo systemctl stop balaur-backend

#2. As a balaur-app user
sudo su - balaur-app
cd /opt/balaur/

#3. Pull changes
git pull origin $(git branch --show-current)

#4. Activate venv and update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

#5. Run migrations
alembic upgrade head

#6. Exit and restart service
exit
sudo systemctl start balaur-backend
sudo systemctl status balaur-backend
```

---

## 12. Troubleshooting

### 12.1. Problem: Service does not start

```bash
# View detailed logs
sudo journalctl -u balaur-backend -n 100 --no-pager

# Verify that the .env exists and has correct permissions
ls -la /opt/balaur/backend/.env

# Test manual import
sudo su - balaur-app
cd /opt/balaur/backend
source venv/bin/activate
python -c "from app.main import app; print('OK')"
```

### 12.2. Problem: FTP permissions error

```bash
# Check groups
groups balaur-app
# Must include: balaur

# Check directory permissions
ls -la /srv/ftp/balaur/

# Reapply permissions if necessary
sudo chown -R balaur:balaur /srv/ftp/balaur
sudo chmod -R 775 /srv/ftp/balaur
```

### 12.3. Problem: LDAP not connecting

```bash
# Test LDAP connection
cd /opt/balaur/backend
source venv/bin/activate
python3 scripts/test_ldap.py <username> <password>

# Verify that the server is accessible
ping <LDAP_SERVER_NAME>
telnet <LDAP_SERVER_NAME> 636 # For LDAP
```

### 12.4. Problem: Database with inconsistent data

```bash
# Reset tables (DEVELOPMENT ONLY)
sudo -u postgres psql balaur_sms << EOF
TRUNCATE TABLE users RESTART IDENTITY CASCADE;

TRUNCATE TABLE software RESTART IDENTITY CASCADE; TRUNCATE TABLE licenses RESTART IDENTITY CASCADE;

EOF

# Reinitialize
python3 scripts/init_db.py
```

### 12.5. Problem: Port 8000 is already in use

```bash
# See which process is using the port
sudo lsof -i :8000

# If there is an old process, kill it
sudo kill -9 <PID>

# Restart service
sudo systemctl restart balaur-backend
```

---

## 13 Backup & Recovery

### 13.1. Database Backup

```bash
# Create backup directory
sudo mkdir -p /var/backups/balaur
sudo chown postgres:postgres /var/backups/balaur

# Manual backup
sudo -u postgres pg_dump balaur_sms > /var/backups/balaur/balaur_sms_$(date +%Y%m%d).sql

# Automate with cron (daily at 2 AM)
sudo crontab -e -u postgres
# Add:
0 2 * * * pg_dump balaur_sms > /var/backups/balaur/balaur_sms_$(date +%Y%m%d).sql
```

### 13.2. Credential vault backup

```bash
# Copy vault to secure location
sudo cp /opt/balaur/secrets/credentials.vault

/secure/path/balaur-credentials-$(date +%Y%m%d).vault
```

### 13.3. Restore

```bash
# Restore database
sudo -u postgres psql balaur_sms < /var/backups/balaur/balaur_sms_YYYYMMDD.sql

# Restore vault
sudo cp /secure/path/balaur-credentials-YYYYMMDD.vault

/opt/balaur/secrets/credentials.vault
```
---
