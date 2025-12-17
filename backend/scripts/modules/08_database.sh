#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
source "$SCRIPT_DIR/modules/utils/logger.sh"

log_section "Database Initialization"

cd /opt/balaur/backend

# Create Alembic versions directory
log_step "Creating Alembic versions directory..."
sudo -u balaur-app mkdir -p alembic/versions
log_success "Versions directory created"

# Generate initial migration
log_step "Generating database migration..."
sudo -u balaur-app bash -c "source venv/bin/activate && alembic revision --autogenerate -m 'Initial schema'" >> "$LOG_FILE" 2>&1
log_success "Migration generated"

# Apply migrations
log_step "Applying database migrations..."
sudo -u balaur-app bash -c "source venv/bin/activate && alembic upgrade head" >> "$LOG_FILE" 2>&1
log_success "Migrations applied"

# Initialize sample data
if [ "$INSTALL_SAMPLE_DATA" = "yes" ]; then
    log_step "Initializing sample data..."
    sudo -u balaur-app bash -c "source venv/bin/activate && echo 'yes' | python3 scripts/init_db.py" >> "$LOG_FILE" 2>&1
    log_success "Sample data initialized"
else
    log_info "Skipping sample data initialization"
fi

# Start backend service
log_step "Starting backend service..."
systemctl start balaur-backend
wait_for_service balaur-backend 60
wait_for_port 8000 30
log_success "Backend service started"

# Test API health
log_step "Testing API health..."
sleep 5
if curl -f http://localhost:8000/health &>/dev/null; then
    log_success "API is responding"
else
    log_error "API health check failed"
    exit 1
fi

log_success "Database initialization complete"