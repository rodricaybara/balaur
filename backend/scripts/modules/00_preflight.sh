#!/bin/bash
################################################################################
# Module 00: Pre-flight Checks
# Verifica que el sistema cumple con los requisitos mínimos
################################################################################

set -euo pipefail

# Source utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"
source "$SCRIPT_DIR/modules/utils/logger.sh"
source "$SCRIPT_DIR/modules/utils/validators.sh"

log_section "Pre-flight System Checks"

################################################################################
# Check if running as root
################################################################################
log_step "Checking root privileges..."
if ! check_root; then
    log_error "This script must be run as root or with sudo"
    exit 1
fi
log_success "Running as root"

################################################################################
# Check OS version
################################################################################
if ! check_os_version; then
    log_error "Unsupported OS. Ubuntu 22.04 or newer required."
    exit 1
fi

################################################################################
# Check system resources
################################################################################
log_step "Checking system resources..."

# Memory
if ! check_memory 8; then
    log_warn "System has less than 8GB RAM. Installation may be slow."
    if ! confirm_continue "Continue anyway?"; then
        exit 1
    fi
fi

# CPU
if ! check_cpu_cores 4; then
    log_warn "System has less than 4 CPU cores. Performance may be degraded."
fi

# Disk space
if ! check_disk_space "/" 50; then
    log_error "Insufficient disk space. At least 50GB required."
    exit 1
fi

################################################################################
# Check network connectivity
################################################################################
log_step "Checking network..."

if ! check_internet; then
    log_error "No internet connectivity. Cannot proceed with installation."
    exit 1
fi

if ! check_dns; then
    log_error "DNS resolution failed. Check /etc/resolv.conf"
    exit 1
fi

################################################################################
# Check required ports
################################################################################
log_step "Checking port availability..."

declare -A REQUIRED_PORTS=(
    [80]="HTTP (nginx)"
    [443]="HTTPS (nginx)"
    [8000]="FastAPI Backend"
    [21]="FTP Control"
    [5432]="PostgreSQL"
)

for port in "${!REQUIRED_PORTS[@]}"; do
    if ! check_port_available "$port"; then
        log_error "Port $port (${REQUIRED_PORTS[$port]}) is already in use"
        log_info "Check with: sudo lsof -i :$port"
        
        if ! confirm_continue "Continue anyway? (may cause conflicts)"; then
            exit 1
        fi
    fi
done

################################################################################
# Check for conflicting services
################################################################################
log_step "Checking for conflicting services..."

CONFLICTING_SERVICES=(
    "apache2"
    "httpd"
)

for service in "${CONFLICTING_SERVICES[@]}"; do
    if check_service_exists "$service"; then
        if systemctl is-active --quiet "$service"; then
            log_warn "Conflicting service $service is running"
            
            if prompt_yes_no "Stop and disable $service?"; then
                systemctl stop "$service"
                systemctl disable "$service"
                log_success "Service $service stopped and disabled"
            else
                log_warn "Service $service will conflict with nginx"
            fi
        fi
    fi
done

################################################################################
# Check if already installed
################################################################################
log_step "Checking for previous installation..."

if [ -d "/opt/balaur" ]; then
    log_warn "Previous installation detected at /opt/balaur"
    
    if [ -f "/opt/balaur/backend/.env" ]; then
        log_warn "Existing .env file found"
    fi
    
    if check_service_exists "balaur-backend"; then
        log_warn "balaur-backend service already exists"
        
        if systemctl is-active --quiet balaur-backend; then
            log_warn "Service is currently running"
            
            if prompt_yes_no "Stop service before continuing?"; then
                systemctl stop balaur-backend
                log_success "Service stopped"
            fi
        fi
    fi
    
    if ! confirm_continue "Continue with existing installation? (will backup and overwrite)"; then
        exit 1
    fi
    
    # Backup existing installation
    BACKUP_DIR="/opt/balaur.backup.$(date +%Y%m%d-%H%M%S)"
    log_step "Creating backup at $BACKUP_DIR..."
    cp -r /opt/balaur "$BACKUP_DIR"
    log_success "Backup created"
fi

################################################################################
# Test package manager
################################################################################
log_step "Testing package manager..."

if ! apt-get update &>/dev/null; then
    log_error "apt-get update failed. Check /etc/apt/sources.list"
    exit 1
fi
log_success "Package manager working"

################################################################################
# Check available package versions
################################################################################
log_step "Checking required packages availability..."

REQUIRED_PACKAGES=(
    "python3"
    "python3-venv"
    "python3-pip"
    "postgresql-15"
    "nginx"
    "git"
    "proftpd"
)

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! apt-cache show "$package" &>/dev/null; then
        log_warn "Package $package not found in repositories"
        
        # Special handling for PostgreSQL 15
        if [[ $package == postgresql-* ]]; then
            log_info "PostgreSQL repository may need to be added"
            log_info "Will attempt to add it during installation"
        fi
    fi
done

################################################################################
# Git repository access test (if URL provided)
################################################################################
if [ -n "${GIT_REPO_URL:-}" ]; then
    log_step "Testing git repository access..."
    
    if test_git_access "$GIT_REPO_URL"; then
        log_success "Git repository is accessible"
    else
        log_warn "Cannot access git repository"
        log_info "You may need to configure SSH keys or access tokens"
        
        if ! confirm_continue "Continue anyway?"; then
            exit 1
        fi
    fi
fi

################################################################################
# LDAP connectivity test (if configured)
################################################################################
if [ -n "${LDAP_SERVER:-}" ]; then
    test_ldap_connectivity "$LDAP_SERVER" || {
        log_warn "LDAP server not reachable. This will be tested again later."
    }
fi

################################################################################
# Summary
################################################################################
echo ""
log_section "Pre-flight Check Summary"

print_summary "System Information" \
    "OS: $(lsb_release -d | cut -f2)" \
    "Kernel: $(uname -r)" \
    "CPU Cores: $(nproc)" \
    "Memory: $(free -h | awk '/^Mem:/ {print $2}')" \
    "Disk Available: $(df -h / | awk 'NR==2 {print $4}')"

echo ""
log_success "All pre-flight checks passed!"
echo ""

# Wait before proceeding
press_any_key "Ready to begin installation. Press any key to continue..."