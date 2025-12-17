#!/bin/bash
################################################################################
# Balaur SMS - Automated Installation Script
# Version: 1.0.0
# Description: Interactive installer for Balaur SMS on Ubuntu 22.04+
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/balaur-install-$(date +%Y%m%d-%H%M%S).log"
CONFIG_FILE="/tmp/balaur-install.conf"
RESUME_FILE="/opt/balaur/.install_progress"
CURRENT_STEP=0

# Source utility functions
source "$SCRIPT_DIR/modules/utils/logger.sh"
source "$SCRIPT_DIR/modules/utils/validators.sh"
source "$SCRIPT_DIR/modules/utils/prompts.sh"

################################################################################
# Trap errors and cleanup
################################################################################
trap 'error_handler $? $LINENO' ERR
trap 'cleanup' EXIT

error_handler() {
    local exit_code=$1
    local line_number=$2
    log_error "Installation failed at line $line_number with exit code $exit_code"
    log_error "Current step: $CURRENT_STEP"
    log_info "Check log file: $LOG_FILE"
    
    read -p "Do you want to save progress for resume? (y/n): " SAVE_PROGRESS
    if [[ "$SAVE_PROGRESS" =~ ^[Yy]$ ]]; then
        echo "$CURRENT_STEP" > "$RESUME_FILE"
        log_info "Progress saved. Run script again to resume from step $CURRENT_STEP"
    fi
    
    exit $exit_code
}

cleanup() {
    # Clean up temporary files
    rm -f /tmp/balaur-*.tmp 2>/dev/null || true
}

################################################################################
# Print banner
################################################################################
print_banner() {
    clear
    echo -e "${BLUE}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║    ██████╗  █████╗ ██╗      █████╗ ██╗   ██╗██████╗              ║
║    ██╔══██╗██╔══██╗██║     ██╔══██╗██║   ██║██╔══██╗             ║
║    ██████╔╝███████║██║     ███████║██║   ██║██████╔╝             ║
║    ██╔══██╗██╔══██║██║     ██╔══██║██║   ██║██╔══██╗             ║
║    ██████╔╝██║  ██║███████╗██║  ██║╚██████╔╝██║  ██║             ║
║    ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝             ║
║                                                                  ║
║              Software Management System - SMS                    ║
║                   Automated Installer v1.0                       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    echo ""
}

################################################################################
# Check if resume is available
################################################################################
check_resume() {
    if [ -f "$RESUME_FILE" ]; then
        local resume_step=$(cat "$RESUME_FILE")
        echo ""
        log_warn "Previous installation found. Last completed step: $resume_step"
        if prompt_yes_no "Do you want to resume from step $resume_step?"; then
            CURRENT_STEP=$resume_step
            log_info "Resuming from step $resume_step"
            return 0
        else
            rm -f "$RESUME_FILE"
            log_info "Starting fresh installation"
            return 1
        fi
    fi
    return 1
}

################################################################################
# Save progress
################################################################################
save_progress() {
    local step=$1
    echo "$step" > "$RESUME_FILE"
    CURRENT_STEP=$step
}

################################################################################
# Interactive configuration wizard
################################################################################
run_wizard() {
    log_section "Configuration Wizard"
    
    echo ""
    echo "Please provide the following information for the installation:"
    echo ""
    
    # Server information
    log_info "Server Configuration"
    SERVER_NAME=$(prompt_input "Server FQDN or IP address" "$(hostname -I | awk '{print $1}')")
    validate_hostname_or_ip "$SERVER_NAME" || {
        log_error "Invalid server name or IP"
        exit 1
    }
    
    ADMIN_EMAIL=$(prompt_input "Administrator email" "admin@$(hostname -d 2>/dev/null || echo 'example.com')")
    validate_email "$ADMIN_EMAIL" || {
        log_error "Invalid email address"
        exit 1
    }
    
    # Git repository
    echo ""
    log_info "Repository Configuration"
    GIT_REPO_URL=$(prompt_input "Git repository URL" "https://github.com/rodricaybara/balaur.git")
    GIT_BRANCH=$(prompt_input "Git branch" "main")
    
    # Active Directory / LDAP
    echo ""
    log_info "Active Directory / LDAP Configuration"
    LDAP_SERVER=$(prompt_input "LDAP server URL" "ldaps://dc.example.com:636")
    validate_ldap_url "$LDAP_SERVER" || {
        log_error "Invalid LDAP URL format"
        exit 1
    }
    
    LDAP_BIND_DN=$(prompt_input "LDAP Bind DN" "cn=balaur-service,ou=Service Accounts,dc=example,dc=com")
    validate_dn "$LDAP_BIND_DN" || {
        log_error "Invalid DN format"
        exit 1
    }
    
    LDAP_SEARCH_BASE=$(prompt_input "LDAP Search Base" "dc=example,dc=com")
    validate_dn "$LDAP_SEARCH_BASE" || {
        log_error "Invalid search base format"
        exit 1
    }
    
    LDAP_SEARCH_FILTER=$(prompt_input "LDAP Search Filter" "(sAMAccountName={username})")
    
    LDAP_USE_TLS=$(prompt_yes_no "Use TLS for LDAP?" "y" && echo "true" || echo "false")
    
    # Database
    echo ""
    log_info "Database Configuration"
    DB_NAME=$(prompt_input "Database name" "balaur_sms")
    validate_db_name "$DB_NAME" || {
        log_error "Invalid database name (use only a-z, 0-9, _)"
        exit 1
    }
    
    DB_USER=$(prompt_input "Database user" "balaur")
    validate_db_name "$DB_USER" || {
        log_error "Invalid database user (use only a-z, 0-9, _)"
        exit 1
    }
    
    # Installation options
    echo ""
    log_info "Installation Options"
    INSTALL_SAMPLE_DATA=$(prompt_yes_no "Install sample data (users, software, licenses)?" "n" && echo "yes" || echo "no")
    
    # CORS origins
    CORS_ORIGINS="[\"http://localhost:3000\",\"https://localhost:3000\",\"http://${SERVER_NAME}\",\"https://${SERVER_NAME}\"]"
    
    # Save configuration
    cat > "$CONFIG_FILE" << EOF
SERVER_NAME="$SERVER_NAME"
ADMIN_EMAIL="$ADMIN_EMAIL"
GIT_REPO_URL="$GIT_REPO_URL"
GIT_BRANCH="$GIT_BRANCH"
LDAP_SERVER="$LDAP_SERVER"
LDAP_BIND_DN="$LDAP_BIND_DN"
LDAP_SEARCH_BASE="$LDAP_SEARCH_BASE"
LDAP_SEARCH_FILTER="$LDAP_SEARCH_FILTER"
LDAP_USE_TLS="$LDAP_USE_TLS"
DB_NAME="$DB_NAME"
DB_USER="$DB_USER"
INSTALL_SAMPLE_DATA="$INSTALL_SAMPLE_DATA"
CORS_ORIGINS="$CORS_ORIGINS"
EOF
    
    # Show summary
    echo ""
    log_section "Configuration Summary"
    echo ""
    echo "Server:          $SERVER_NAME"
    echo "Admin Email:     $ADMIN_EMAIL"
    echo "Git Repo:        $GIT_REPO_URL ($GIT_BRANCH)"
    echo "LDAP Server:     $LDAP_SERVER"
    echo "LDAP Bind DN:    $LDAP_BIND_DN"
    echo "LDAP Search Base: $LDAP_SEARCH_BASE"
    echo "Database Name:   $DB_NAME"
    echo "Database User:   $DB_USER"
    echo "Sample Data:     $INSTALL_SAMPLE_DATA"
    echo ""
    
    if ! prompt_yes_no "Is this configuration correct?"; then
        log_error "Installation cancelled by user"
        exit 0
    fi
}

################################################################################
# Main installation process
################################################################################
main() {
    print_banner
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
    
    log_info "Starting Balaur SMS installation"
    log_info "Log file: $LOG_FILE"
    
    # Check for resume
    local resume=false
    check_resume && resume=true
    
    # Load configuration if resuming
    if [ "$resume" = true ] && [ -f "$CONFIG_FILE" ]; then
        log_info "Loading saved configuration..."
        source "$CONFIG_FILE"
    else
        # Run configuration wizard
        run_wizard
    fi
    
    # Export variables for modules
    export SERVER_NAME ADMIN_EMAIL GIT_REPO_URL GIT_BRANCH
    export LDAP_SERVER LDAP_BIND_DN LDAP_SEARCH_BASE LDAP_SEARCH_FILTER LDAP_USE_TLS
    export DB_NAME DB_USER INSTALL_SAMPLE_DATA CORS_ORIGINS
    export LOG_FILE
    
    # Execute installation modules
    execute_step 0 "Pre-flight checks" "$SCRIPT_DIR/modules/00_preflight.sh"
    execute_step 1 "System preparation" "$SCRIPT_DIR/modules/01_system.sh"
    execute_step 2 "PostgreSQL setup" "$SCRIPT_DIR/modules/02_postgresql.sh"
    execute_step 3 "ProFTPD setup" "$SCRIPT_DIR/modules/03_ftp.sh"
    execute_step 4 "Backend installation" "$SCRIPT_DIR/modules/04_backend.sh"
    execute_step 5 "Frontend build" "$SCRIPT_DIR/modules/05_frontend.sh"
    execute_step 6 "Nginx configuration" "$SCRIPT_DIR/modules/06_nginx.sh"
    execute_step 7 "Security hardening" "$SCRIPT_DIR/modules/07_security.sh"
    execute_step 8 "Database initialization" "$SCRIPT_DIR/modules/08_database.sh"
    execute_step 9 "Post-installation checks" "$SCRIPT_DIR/modules/09_postinstall.sh"
    
    # Installation complete
    log_section "Installation Complete!"
    
    echo ""
    log_success "Balaur SMS has been successfully installed!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  🌐 Access URL:     https://$SERVER_NAME"
    echo "  📊 API Docs:       https://$SERVER_NAME/docs"
    echo "  📧 Admin Email:    $ADMIN_EMAIL"
    echo ""
    echo "  Default credentials:"
    echo "    • Admin:   admin / Admin123!"
    echo "    • Manager: manager / Manager123!"
    echo "    • User:    user / User123!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "⚠️  IMPORTANT NEXT STEPS:"
    echo ""
    echo "  1. Test LDAP authentication:"
    echo "     cd /opt/balaur/backend"
    echo "     source venv/bin/activate"
    echo "     python3 scripts/test_ldap.py <username> <password>"
    echo ""
    echo "  2. Change default passwords in production!"
    echo ""
    echo "  3. Review logs:"
    echo "     sudo journalctl -u balaur-backend -f"
    echo "     tail -f /var/log/balaur/backend/error.log"
    echo ""
    echo "  4. View encrypted credentials:"
    echo "     sudo /opt/balaur/backend/scripts/view_secrets.sh"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # Clean up
    rm -f "$CONFIG_FILE"
    rm -f "$RESUME_FILE"
    
    log_info "Installation log saved to: $LOG_FILE"
}

################################################################################
# Execute installation step
################################################################################
execute_step() {
    local step_num=$1
    local step_name=$2
    local step_script=$3
    
    # Skip if already completed
    if [ $CURRENT_STEP -gt $step_num ]; then
        log_info "Step $step_num already completed, skipping..."
        return 0
    fi
    
    log_section "Step $step_num: $step_name"
    
    if [ ! -f "$step_script" ]; then
        log_error "Module script not found: $step_script"
        exit 1
    fi
    
    # Execute module
    bash "$step_script"
    
    # Save progress
    save_progress $((step_num + 1))
    
    log_success "Step $step_num completed: $step_name"
    echo ""
}

################################################################################
# Run main installation
################################################################################
main "$@"