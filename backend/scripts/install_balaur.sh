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
# Preferred and fallback resume locations. We'll pick the first writable one at startup.
DEFAULT_RESUME_DIR="/opt/balaur"
FALLBACK_RESUME_DIR="/var/lib/balaur"
RESUME_DIR="$DEFAULT_RESUME_DIR"
RESUME_FILE="$RESUME_DIR/.install_progress"
CURRENT_STEP=0

# Source utility functions
source "$SCRIPT_DIR/utils/logger.sh"
source "$SCRIPT_DIR/utils/validators.sh"
source "$SCRIPT_DIR/utils/prompts.sh"

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
        save_progress "$CURRENT_STEP"
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
# Prepare and save progress utilities
################################################################################
prepare_resume_file() {
    # Try preferred dir, then fallback dirs, then /tmp
    for dir in "$RESUME_DIR" "$FALLBACK_RESUME_DIR" "/run/balaur" "/var/lib/balaur" "/tmp"; do
        mkdir -p "$dir" 2>/dev/null || true
        touch "$dir/.install_progress" 2>/dev/null || true
        # check writability
        if [ -w "$dir" ] || [ -w "$dir/.install_progress" ]; then
            RESUME_DIR="$dir"
            RESUME_FILE="$RESUME_DIR/.install_progress"
            chmod 0666 "$RESUME_FILE" 2>/dev/null || true
            return 0
        fi
    done
    # No writable location found
    log_warn "No writable location available for resume progress; progress will not be saved"
    RESUME_FILE=""
    return 1
}

save_progress() {
    local step=$1
    if [ -z "${RESUME_FILE:-}" ]; then
        log_warn "Resume file not configured; skipping save of progress"
        CURRENT_STEP=$step
        return 0
    fi

    mkdir -p "$(dirname "$RESUME_FILE")" 2>/dev/null || true

    if printf "%s\n" "$step" > "$RESUME_FILE" 2>/dev/null; then
        CURRENT_STEP=$step
        return 0
    fi

    if printf "%s\n" "$step" | tee "$RESUME_FILE" > /dev/null 2>/dev/null; then
        CURRENT_STEP=$step
        return 0
    fi

    chmod 0666 "$RESUME_FILE" 2>/dev/null || true
    if printf "%s\n" "$step" > "$RESUME_FILE" 2>/dev/null; then
        CURRENT_STEP=$step
        return 0
    fi

    log_error "Could not write to $RESUME_FILE; progress will not be saved"
    CURRENT_STEP=$step
    return 0
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
    LDAP_SERVER=$(prompt_ldap_url "LDAP server URL" "ldaps://dc.example.com:636")

    # Derive port and SSL usage from URL (do not prompt for port)
    if [[ $LDAP_SERVER =~ ^ldaps?://[^:]+:([0-9]+)$ ]]; then
        LDAP_PORT="${BASH_REMATCH[1]}"
    else
        if [[ $LDAP_SERVER =~ ^ldaps:// ]]; then
            LDAP_PORT=636
        else
            LDAP_PORT=389
        fi
    fi

    if [[ $LDAP_SERVER =~ ^ldaps:// ]]; then
        LDAP_USE_SSL="true"
    else
        LDAP_USE_SSL="false"
    fi

    LDAP_BIND_DN=$(prompt_dn "LDAP Bind DN" "cn=balaur-service,ou=Service Accounts,dc=example,dc=com")
    validate_dn "$LDAP_BIND_DN" || {
        log_error "Invalid DN format"
        exit 1
    }

    LDAP_BIND_PASSWORD=$(prompt_password "LDAP Bind Password (leave blank for anonymous bind)")
    # Remove any accidental newlines/carriage returns from password (prevents config corruption)
    LDAP_BIND_PASSWORD=$(printf '%s' "$LDAP_BIND_PASSWORD" | tr -d '\r\n')

    LDAP_BASE_DN=$(prompt_dn "LDAP Base DN" "dc=example,dc=com")
    validate_dn "$LDAP_BASE_DN" || {
        log_error "Invalid base DN format"
        exit 1
    }

    LDAP_USER_SEARCH_BASE=$(prompt_dn "LDAP User Search Base" "ou=Users,dc=example,dc=com")
    validate_dn "$LDAP_USER_SEARCH_BASE" || {
        log_error "Invalid user search base format"
        exit 1
    }

    # User search filter - validated
    while true; do
        LDAP_USER_SEARCH_FILTER=$(prompt_input "LDAP User Search Filter" "(sAMAccountName={username})")
        if validate_ldap_filter "$LDAP_USER_SEARCH_FILTER"; then
            break
        fi
        echo -e "${RED}Invalid LDAP filter. Please try again.${NC}"
    done

    LDAP_USER_OBJECT_CLASS=$(prompt_input "LDAP User Object Class" "person")

    LDAP_USE_TLS=$(prompt_yes_no "Use STARTTLS for LDAP?" "n" && echo "true" || echo "false")

    LDAP_GROUP_ADMIN=$(prompt_dn "LDAP Group (admin) DN" "cn=balaur-admins,ou=Groups,dc=example,dc=com")
    LDAP_GROUP_MANAGER=$(prompt_dn "LDAP Group (manager) DN" "cn=balaur-managers,ou=Groups,dc=example,dc=com")
    LDAP_GROUP_USER=$(prompt_dn "LDAP Group (user) DN" "cn=balaur-users,ou=Groups,dc=example,dc=com")

    # Keep old variable name for compatibility
    LDAP_SEARCH_BASE="$LDAP_BASE_DN"

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
LDAP_PORT="$LDAP_PORT"
LDAP_USE_SSL="$LDAP_USE_SSL"
LDAP_USE_TLS="$LDAP_USE_TLS"
LDAP_BIND_DN="$LDAP_BIND_DN"
LDAP_BIND_PASSWORD="$LDAP_BIND_PASSWORD"
LDAP_BASE_DN="$LDAP_BASE_DN"
LDAP_SEARCH_BASE="$LDAP_SEARCH_BASE"
LDAP_USER_SEARCH_BASE="$LDAP_USER_SEARCH_BASE"
LDAP_USER_SEARCH_FILTER="$LDAP_USER_SEARCH_FILTER"
LDAP_USER_OBJECT_CLASS="$LDAP_USER_OBJECT_CLASS"
LDAP_GROUP_ADMIN="$LDAP_GROUP_ADMIN"
LDAP_GROUP_MANAGER="$LDAP_GROUP_MANAGER"
LDAP_GROUP_USER="$LDAP_GROUP_USER"
DB_NAME="$DB_NAME"
DB_USER="$DB_USER"
INSTALL_SAMPLE_DATA="$INSTALL_SAMPLE_DATA"
CORS_ORIGINS="$CORS_ORIGINS"
EOF
    
    # Show summary
    echo ""
    log_section "Configuration Summary"
    echo ""
    echo "Server:                 $SERVER_NAME"
    echo "Admin Email:            $ADMIN_EMAIL"
    echo "Git Repo:               $GIT_REPO_URL ($GIT_BRANCH)"
    echo "LDAP Server:            $LDAP_SERVER"
    echo "LDAP Port:              $LDAP_PORT"
    echo "LDAP SSL:               $LDAP_USE_SSL"
    echo "LDAP STARTTLS:          $LDAP_USE_TLS"
    echo "LDAP Base DN:           $LDAP_BASE_DN"
    echo "LDAP User Search Base:  $LDAP_USER_SEARCH_BASE"
    echo "LDAP User Filter:       $LDAP_USER_SEARCH_FILTER"
    echo "LDAP Groups:            admin=$LDAP_GROUP_ADMIN, manager=$LDAP_GROUP_MANAGER, user=$LDAP_GROUP_USER"
    echo "Database Name:          $DB_NAME"
    echo "Database User:          $DB_USER"
    echo "Sample Data:            $INSTALL_SAMPLE_DATA"
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
    
    # Prepare resume file location (create dirs or fallback)
    prepare_resume_file
    
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
    export LDAP_SERVER LDAP_PORT LDAP_BIND_DN LDAP_BIND_PASSWORD LDAP_BASE_DN LDAP_SEARCH_BASE LDAP_USER_SEARCH_BASE LDAP_USER_SEARCH_FILTER LDAP_USER_OBJECT_CLASS LDAP_USE_SSL LDAP_USE_TLS LDAP_GROUP_ADMIN LDAP_GROUP_MANAGER LDAP_GROUP_USER
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