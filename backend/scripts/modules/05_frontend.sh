#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
source "$SCRIPT_DIR/modules/utils/logger.sh"

log_section "Frontend Build"

# Install Node.js 22
log_step "Installing Node.js 22..."
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - >> "$LOG_FILE" 2>&1
    DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs >> "$LOG_FILE" 2>&1
    log_success "Node.js installed"
else
    log_info "Node.js already installed ($(node --version))"
fi

# Create frontend .env
log_step "Creating frontend .env..."
cat > /opt/balaur/frontend/.env << EOF
VITE_API_BASE_URL=/api/v1
VITE_APP_NAME=Balaur SMS
EOF

chown balaur-app:balaur-app /opt/balaur/frontend/.env
log_success "Frontend .env created"

# Remove conflicting env files
rm -f /opt/balaur/frontend/.env.production
rm -f /opt/balaur/frontend/.env.development

# Install dependencies
log_step "Installing npm dependencies..."
cd /opt/balaur/frontend
sudo -u balaur-app npm install >> "$LOG_FILE" 2>&1
log_success "Dependencies installed"

# Build frontend
log_step "Building frontend (this may take a few minutes)..."
sudo -u balaur-app npm run build >> "$LOG_FILE" 2>&1
log_success "Frontend built"

# Verify dist directory
if [ ! -d /opt/balaur/frontend/dist ]; then
    log_error "Frontend build failed - dist directory not found"
    exit 1
fi

log_success "Frontend build complete"