#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
source "$SCRIPT_DIR/modules/utils/logger.sh"

log_section "System Preparation"

# Update system
log_step "Updating package lists..."
apt-get update >> "$LOG_FILE" 2>&1
log_success "Package lists updated"

log_step "Upgrading system packages..."
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y >> "$LOG_FILE" 2>&1
log_success "System packages upgraded"

# Install essential packages
log_step "Installing essential packages..."
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-venv \
    python3-pip \
    git \
    curl \
    wget \
    gnupg2 \
    ca-certificates \
    openssl \
    netcat \
    >> "$LOG_FILE" 2>&1
log_success "Essential packages installed"

# Create balaur-app user
log_step "Creating balaur-app user..."
if id "balaur-app" &>/dev/null; then
    log_info "User balaur-app already exists"
else
    useradd -m -s /bin/bash balaur-app
    log_success "User balaur-app created"
fi

# Create directory structure
log_step "Creating directory structure..."
safe_create_dir "/opt/balaur" "balaur-app:balaur-app" "755"
safe_create_dir "/var/log/balaur/backend" "balaur-app:balaur-app" "755"
safe_create_dir "/var/log/balaur/frontend" "balaur-app:balaur-app" "755"

log_success "System preparation complete"