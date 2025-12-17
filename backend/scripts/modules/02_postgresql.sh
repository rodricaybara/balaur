#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
source "$SCRIPT_DIR/modules/utils/logger.sh"

log_section "PostgreSQL Setup"

# Add PostgreSQL repository
log_step "Adding PostgreSQL repository..."
if [ ! -f /etc/apt/sources.list.d/pgdg.list ]; then
    sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
    wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
    apt-get update >> "$LOG_FILE" 2>&1
    log_success "PostgreSQL repository added"
else
    log_info "PostgreSQL repository already configured"
fi

# Install PostgreSQL
log_step "Installing PostgreSQL 15..."
DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql-15 postgresql-contrib-15 >> "$LOG_FILE" 2>&1
log_success "PostgreSQL installed"

# Start PostgreSQL
log_step "Starting PostgreSQL..."
systemctl start postgresql
systemctl enable postgresql
wait_for_service postgresql 30
log_success "PostgreSQL started"

# Note: Database creation will be done by setup_secrets.sh
log_info "Database will be created by setup_secrets.sh script"

log_success "PostgreSQL setup complete"