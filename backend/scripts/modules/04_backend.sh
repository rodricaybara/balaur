#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
source "$SCRIPT_DIR/utils/logger.sh"

log_section "Backend Installation"

# Clone repository
log_step "Cloning repository..."
if [ -d "/opt/balaur/.git" ]; then
    log_info "Repository already cloned, pulling latest changes..."
    cd /opt/balaur
    sudo -u balaur-app git pull origin "$GIT_BRANCH" >> "$LOG_FILE" 2>&1
else
    log_step "Cloning $GIT_REPO_URL..."
    sudo -u balaur-app git clone "$GIT_REPO_URL" /opt/balaur >> "$LOG_FILE" 2>&1
    cd /opt/balaur
    sudo -u balaur-app git checkout "$GIT_BRANCH" >> "$LOG_FILE" 2>&1
fi
log_success "Repository ready"

# Create virtual environment
log_step "Creating Python virtual environment..."
cd /opt/balaur/backend
if [ ! -d "venv" ]; then
    sudo -u balaur-app python3 -m venv venv >> "$LOG_FILE" 2>&1
    log_success "Virtual environment created"
else
    log_info "Virtual environment already exists"
fi

# Install dependencies
log_step "Installing Python dependencies..."
sudo -u balaur-app bash -c "source venv/bin/activate && pip install --upgrade pip >> '$LOG_FILE' 2>&1"
sudo -u balaur-app bash -c "source venv/bin/activate && pip install -r requirements.txt >> '$LOG_FILE' 2>&1"
log_success "Dependencies installed"

# Run setup_secrets.sh
log_step "Running setup_secrets.sh..."
log_info "This will prompt for passwords..."
cd /opt/balaur/backend
chmod +x scripts/setup_secrets.sh
./scripts/setup_secrets.sh

# Verify .env was created
if [ ! -f /opt/balaur/backend/.env ]; then
    log_error ".env file was not created by setup_secrets.sh"
    exit 1
fi

# Update LDAP configuration in .env
log_step "Updating LDAP configuration..."
cat >> /opt/balaur/backend/.env << EOF

# LDAP Configuration (added by installer)
LDAP_SERVER=$LDAP_SERVER
LDAP_BIND_DN=$LDAP_BIND_DN
LDAP_SEARCH_BASE=$LDAP_SEARCH_BASE
LDAP_SEARCH_FILTER=$LDAP_SEARCH_FILTER
LDAP_USE_TLS=$LDAP_USE_TLS

# CORS Origins
CORS_ORIGINS=$CORS_ORIGINS

# API Documentation
DOCS_ENABLED=false
EOF

chown balaur-app:balaur-app /opt/balaur/backend/.env
chmod 600 /opt/balaur/backend/.env
log_success "LDAP configuration added"

# Create gunicorn.conf.py
log_step "Creating gunicorn configuration..."
cat > /opt/balaur/backend/gunicorn.conf.py << 'EOF'
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "/var/log/balaur/backend/access.log"
errorlog = "/var/log/balaur/backend/error.log"
loglevel = "info"
timeout = 300
EOF

chown balaur-app:balaur-app /opt/balaur/backend/gunicorn.conf.py
log_success "Gunicorn configuration created"

# Create systemd service
log_step "Creating systemd service..."
cat > /etc/systemd/system/balaur-backend.service << 'EOF'
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
EOF

systemctl daemon-reload
log_success "Systemd service created"

# Enable service (but don't start yet, will start after database init)
systemctl enable balaur-backend
log_info "Service enabled (will start after database initialization)"

log_success "Backend installation complete"