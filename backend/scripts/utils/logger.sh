#!/bin/bash
################################################################################
# Logger Utilities
# Funciones para logging con colores y formato
################################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Symbols
SYMBOL_SUCCESS="✅"
SYMBOL_ERROR="❌"
SYMBOL_WARNING="⚠️"
SYMBOL_INFO="ℹ️"
SYMBOL_ARROW="➜"

################################################################################
# Log functions
################################################################################

log_raw() {
    local message="$*"
    echo "$message" | tee -a "$LOG_FILE"
}

log_info() {
    local message="$*"
    echo -e "${BLUE}${SYMBOL_INFO}  [INFO]${NC} $message" | tee -a "$LOG_FILE"
}

log_success() {
    local message="$*"
    echo -e "${GREEN}${SYMBOL_SUCCESS} [OK]${NC}   $message" | tee -a "$LOG_FILE"
}

log_error() {
    local message="$*"
    echo -e "${RED}${SYMBOL_ERROR} [ERROR]${NC} $message" | tee -a "$LOG_FILE" >&2
}

log_warn() {
    local message="$*"
    echo -e "${YELLOW}${SYMBOL_WARNING}  [WARN]${NC} $message" | tee -a "$LOG_FILE"
}

log_step() {
    local message="$*"
    echo -e "${CYAN}${SYMBOL_ARROW}  $message${NC}" | tee -a "$LOG_FILE"
}

log_section() {
    local title="$*"
    local line="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "" | tee -a "$LOG_FILE"
    echo -e "${MAGENTA}$line${NC}" | tee -a "$LOG_FILE"
    echo -e "${WHITE}  $title${NC}" | tee -a "$LOG_FILE"
    echo -e "${MAGENTA}$line${NC}" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
}

log_command() {
    local cmd="$*"
    log_step "Executing: $cmd"
    if eval "$cmd" >> "$LOG_FILE" 2>&1; then
        log_success "Command succeeded"
        return 0
    else
        log_error "Command failed: $cmd"
        return 1
    fi
}

log_command_output() {
    local cmd="$*"
    log_step "Executing: $cmd"
    if eval "$cmd" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "Command succeeded"
        return 0
    else
        log_error "Command failed: $cmd"
        return 1
    fi
}

################################################################################
# Progress bar
################################################################################

show_progress() {
    local current=$1
    local total=$2
    local message=$3
    local width=50
    local percentage=$((current * 100 / total))
    local filled=$((width * current / total))
    local empty=$((width - filled))
    
    printf "\r${CYAN}["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "]${NC} %3d%% - %s" "$percentage" "$message"
    
    if [ $current -eq $total ]; then
        echo ""
    fi
}

################################################################################
# Spinner
################################################################################

spinner() {
    local pid=$1
    local message=$2
    local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0
    
    while kill -0 $pid 2>/dev/null; do
        i=$(( (i+1) % 10 ))
        printf "\r${CYAN}${spin:$i:1}${NC} $message"
        sleep 0.1
    done
    
    printf "\r${GREEN}${SYMBOL_SUCCESS}${NC} $message\n"
}

################################################################################
# Box drawing
################################################################################

draw_box() {
    local text="$*"
    local length=${#text}
    local border_length=$((length + 4))
    
    echo ""
    echo -e "${BLUE}╔$(printf '═%.0s' $(seq 1 $border_length))╗${NC}"
    echo -e "${BLUE}║${NC}  $text  ${BLUE}║${NC}"
    echo -e "${BLUE}╚$(printf '═%.0s' $(seq 1 $border_length))╝${NC}"
    echo ""
}

################################################################################
# Confirmation prompts with logging
################################################################################

confirm_action() {
    local message="$1"
    local default="${2:-n}"
    
    log_warn "$message"
    read -p "Continue? (y/n) [$default]: " response
    response=${response:-$default}
    
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log_info "User confirmed: $message"
        return 0
    else
        log_info "User cancelled: $message"
        return 1
    fi
}

################################################################################
# Time tracking
################################################################################

start_timer() {
    START_TIME=$(date +%s)
}

stop_timer() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))
    
    log_info "Elapsed time: ${minutes}m ${seconds}s"
}

################################################################################
# Service status check
################################################################################

check_service() {
    local service_name=$1
    
    if systemctl is-active --quiet "$service_name"; then
        log_success "$service_name is running"
        return 0
    else
        log_error "$service_name is not running"
        return 1
    fi
}

check_service_enabled() {
    local service_name=$1
    
    if systemctl is-enabled --quiet "$service_name"; then
        log_success "$service_name is enabled"
        return 0
    else
        log_warn "$service_name is not enabled"
        return 1
    fi
}

################################################################################
# File operations with logging
################################################################################

safe_backup() {
    local file=$1
    local backup="${file}.backup.$(date +%Y%m%d-%H%M%S)"
    
    if [ -f "$file" ]; then
        log_step "Backing up $file to $backup"
        cp "$file" "$backup"
        log_success "Backup created"
    fi
}

safe_create_dir() {
    local dir=$1
    local owner="${2:-root:root}"
    local perms="${3:-755}"
    
    if [ ! -d "$dir" ]; then
        log_step "Creating directory: $dir"
        mkdir -p "$dir"
        chown "$owner" "$dir"
        chmod "$perms" "$dir"
        log_success "Directory created"
    else
        log_info "Directory already exists: $dir"
    fi
}

safe_write_file() {
    local file=$1
    local content=$2
    local owner="${3:-root:root}"
    local perms="${4:-644}"
    
    log_step "Writing file: $file"
    safe_backup "$file"
    echo "$content" > "$file"
    chown "$owner" "$file"
    chmod "$perms" "$file"
    log_success "File written"
}

################################################################################
# Wait for condition
################################################################################

wait_for_service() {
    local service=$1
    local max_wait=${2:-30}
    local count=0
    
    log_step "Waiting for $service to be ready..."
    
    while [ $count -lt $max_wait ]; do
        if systemctl is-active --quiet "$service"; then
            log_success "$service is ready"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        printf "."
    done
    
    echo ""
    log_error "$service failed to start within ${max_wait}s"
    return 1
}

wait_for_port() {
    local port=$1
    local max_wait=${2:-30}
    local count=0
    
    log_step "Waiting for port $port to be ready..."
    
    while [ $count -lt $max_wait ]; do
        if nc -z localhost "$port" 2>/dev/null; then
            log_success "Port $port is ready"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        printf "."
    done
    
    echo ""
    log_error "Port $port not ready within ${max_wait}s"
    return 1
}

################################################################################
# Summary functions
################################################################################

print_summary() {
    local title="$1"
    shift
    local items=("$@")
    
    log_section "$title"
    for item in "${items[@]}"; do
        echo "  • $item"
    done
    echo ""
}