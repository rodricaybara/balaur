#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
source "$SCRIPT_DIR/utils/logger.sh"

log_section "Backend Installation"

# Copy repository files from local source
log_step "Copying repository files from local source..."
LOCAL_REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
if [ -d "/opt/balaur" ]; then
    log_info "Target /opt/balaur already exists, updating files..."
else
    log_step "Creating /opt/balaur..."
    mkdir -p /opt/balaur >> "$LOG_FILE" 2>&1
fi

# Copy contents (prefer rsync, fall back to tar)
if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete --exclude='.git' --exclude='venv' "$LOCAL_REPO_DIR/" /opt/balaur >> "$LOG_FILE" 2>&1
else
    (cd "$LOCAL_REPO_DIR" && tar cf - --exclude='.git' --exclude='venv' .) | (cd /opt/balaur && tar xf -) >> "$LOG_FILE" 2>&1
fi

chown -R balaur-app:balaur-app /opt/balaur >> "$LOG_FILE" 2>&1
log_success "Repository files copied"

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
# Use sudo tee to append logs as root while running commands as balaur-app
if ! sudo -u balaur-app bash -lc "source venv/bin/activate && pip install --upgrade pip" 2>&1 | sudo tee -a "$LOG_FILE" >/dev/null; then
    log_error "Failed to upgrade pip"
    exit 1
fi
if ! sudo -u balaur-app bash -lc "source venv/bin/activate && pip install -r requirements.txt" 2>&1 | sudo tee -a "$LOG_FILE" >/dev/null; then
    log_error "Failed to install Python requirements"
    exit 1
fi
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
# Helper to write safe single-quoted env entries (escapes single quotes)
env_write() {
    local name=$1
    local val=${2:-}
    local esc
    esc=$(printf "%s" "$val" | sed "s/'/'\"'\"'/g")
    printf "%s='%s'\n" "$name" "$esc" >> /opt/balaur/backend/.env
}

# Add header
cat >> /opt/balaur/backend/.env << EOF

# LDAP Configuration (added by installer)
EOF

# Write entries safely
env_write LDAP_SERVER "$LDAP_SERVER"
env_write LDAP_PORT "$LDAP_PORT"
env_write LDAP_USE_SSL "$LDAP_USE_SSL"
env_write LDAP_USE_TLS "$LDAP_USE_TLS"
env_write LDAP_BIND_DN "$LDAP_BIND_DN"
env_write LDAP_BIND_PASSWORD "$LDAP_BIND_PASSWORD"
env_write LDAP_BASE_DN "$LDAP_BASE_DN"
# Backwards compatibility
env_write LDAP_SEARCH_BASE "$LDAP_SEARCH_BASE"
env_write LDAP_USER_SEARCH_BASE "$LDAP_USER_SEARCH_BASE"
env_write LDAP_USER_SEARCH_FILTER "$LDAP_USER_SEARCH_FILTER"
env_write LDAP_USER_OBJECT_CLASS "$LDAP_USER_OBJECT_CLASS"
env_write LDAP_GROUP_ADMIN "$LDAP_GROUP_ADMIN"
env_write LDAP_GROUP_MANAGER "$LDAP_GROUP_MANAGER"
env_write LDAP_GROUP_USER "$LDAP_GROUP_USER"

env_write CORS_ORIGINS "$CORS_ORIGINS"
env_write DOCS_ENABLED "false"

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