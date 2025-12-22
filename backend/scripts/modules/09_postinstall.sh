#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
source "$SCRIPT_DIR/utils/logger.sh"

log_section "Post-Installation Verification"

################################################################################
# Service checks
################################################################################
log_step "Checking services status..."

SERVICES=(
    "postgresql"
    "proftpd"
    "balaur-backend"
    "nginx"
    "fail2ban"
)

SERVICES_OK=true
for service in "${SERVICES[@]}"; do
    if check_service "$service"; then
        echo -n ""
    else
        SERVICES_OK=false
    fi
done

if [ "$SERVICES_OK" = false ]; then
    log_error "Some services are not running"
    exit 1
fi

################################################################################
# Port checks
################################################################################
log_step "Checking ports..."

PORTS=(
    [80]="HTTP"
    [443]="HTTPS"
    [8000]="Backend API"
    [21]="FTP"
    [5432]="PostgreSQL"
)

PORTS_OK=true
for port in "${!PORTS[@]}"; do
    if nc -z localhost "$port" 2>/dev/null; then
        log_success "${PORTS[$port]} port $port is listening"
    else
        log_error "${PORTS[$port]} port $port is not listening"
        PORTS_OK=false
    fi
done

if [ "$PORTS_OK" = false ]; then
    log_error "Some ports are not accessible"
    exit 1
fi

################################################################################
# API endpoint checks
################################################################################
log_step "Testing API endpoints..."

# Health check
if curl -f http://localhost:8000/health &>/dev/null; then
    log_success "Health endpoint OK"
else
    log_error "Health endpoint failed"
    exit 1
fi

# API docs
if curl -f http://localhost:8000/docs &>/dev/null; then
    log_success "API docs accessible"
else
    log_warn "API docs not accessible (may be disabled)"
fi

################################################################################
# Frontend check
################################################################################
log_step "Testing frontend..."

if curl -f http://localhost/ &>/dev/null; then
    log_success "Frontend accessible via HTTP"
else
    log_error "Frontend not accessible via HTTP"
    exit 1
fi

################################################################################
# Database check
################################################################################
log_step "Verifying database..."

cd /opt/balaur/backend
# Use a temporary python script to avoid complex shell quoting issues and support async engines
TMP_PY=$(mktemp /tmp/balaur_check_db.XXXX.py)
cat > "$TMP_PY" << 'PY'
import asyncio
import sys
from app.database import engine
from sqlalchemy import text

async def main():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("DB_OK")
    except Exception as e:
        print("DB_ERROR:", repr(e), file=sys.stderr)
        raise

if __name__ == '__main__':
    asyncio.run(main())
PY

# Run the check and capture output to log for diagnostics
if sudo -u balaur-app bash -c "cd /opt/balaur/backend && source venv/bin/activate && python3 \"$TMP_PY\"" >> "$LOG_FILE" 2>&1; then
    log_success "Database connection OK"
else
    log_error "Database connection failed (see $LOG_FILE for details)"
    rm -f "$TMP_PY"
    exit 1
fi

rm -f "$TMP_PY"

# Check if tables exist
TABLES=$(sudo -u postgres psql -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null | tr -d ' ')
if [ "$TABLES" -gt 0 ]; then
    log_success "Database has $TABLES tables"
else
    log_error "No tables found in database"
    exit 1
fi

################################################################################
# FTP check
################################################################################
log_step "Testing FTP permissions..."

if sudo -u balaur-app bash -c "touch /srv/ftp/balaur/inbox/pending/.test && rm /srv/ftp/balaur/inbox/pending/.test" &>/dev/null; then
    log_success "FTP write permissions OK"
else
    log_error "FTP write permissions failed"
    exit 1
fi

################################################################################
# File permissions check
################################################################################
log_step "Checking file permissions..."

if [ "$(stat -c '%a' /opt/balaur/backend/.env)" = "600" ]; then
    log_success ".env file permissions OK"
else
    log_warn ".env file permissions should be 600"
fi

################################################################################
# System resources check
################################################################################
log_step "Checking system resources..."

# Memory usage
MEMORY_USED=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
log_info "Memory usage: ${MEMORY_USED}%"

# Disk usage
DISK_USED=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
log_info "Disk usage: ${DISK_USED}%"

if [ "$DISK_USED" -gt 80 ]; then
    log_warn "Disk usage is above 80%"
fi

################################################################################
# Log files check
################################################################################
log_step "Checking log files..."

LOG_FILES=(
    "/var/log/balaur/backend/error.log"
    "/var/log/balaur/backend/access.log"
    "/var/log/nginx/balaur-error.log"
    "/var/log/nginx/balaur-access.log"
)

for logfile in "${LOG_FILES[@]}"; do
    if [ -f "$logfile" ]; then
        log_success "Log file exists: $logfile"
    else
        log_info "Log file will be created: $logfile"
    fi
done