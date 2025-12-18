#!/bin/bash
################################################################################
# Input Validators
# Funciones para validar inputs del usuario
################################################################################

################################################################################
# Network validation
################################################################################

validate_hostname_or_ip() {
    local input=$1
    
    # Check if it's a valid IP
    if [[ $input =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        local IFS='.'
        local -a ip=($input)
        [[ ${ip[0]} -le 255 && ${ip[1]} -le 255 && ${ip[2]} -le 255 && ${ip[3]} -le 255 ]]
        return $?
    fi
    
    # Check if it's a valid hostname/FQDN
    if [[ $input =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$ ]]; then
        return 0
    fi
    
    return 1
}

validate_email() {
    local email=$1
    local regex="^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    
    [[ $email =~ $regex ]]
}

validate_port() {
    local port=$1
    
    if [[ $port =~ ^[0-9]+$ ]] && [ $port -ge 1 ] && [ $port -le 65535 ]; then
        return 0
    fi
    return 1
}

validate_url() {
    local url=$1
    local regex="^(https?|ftp)://[a-zA-Z0-9.-]+(:[0-9]+)?(/.*)?$"
    
    [[ $url =~ $regex ]]
}

################################################################################
# LDAP validation
################################################################################

validate_ldap_url() {
    local url=$1
    local regex="^ldaps?://[a-zA-Z0-9.-]+(:[0-9]+)?$"
    
    [[ $url =~ $regex ]]
}

validate_dn() {
    local dn=$1
    # Basic DN validation: should contain at least one =
    # Example: cn=user,ou=Users,dc=example,dc=com
    
    if [[ $dn =~ ^[a-zA-Z]+=.+ ]]; then
        return 0
    fi
    return 1
}

validate_ldap_filter() {
    local filter=$1
    # Basic LDAP filter validation: should start with ( and end with )
    # Example: (sAMAccountName={username})
    
    if [[ $filter =~ ^\(.+\)$ ]]; then
        return 0
    fi
    return 1
}

test_ldap_connectivity() {
    local server=$1
    local port=${2:-389}
    
    # Extract hostname and port from URL if provided
    if [[ $server =~ ldaps?://([^:]+):?([0-9]+)? ]]; then
        local host="${BASH_REMATCH[1]}"
        local extracted_port="${BASH_REMATCH[2]}"
        port=${extracted_port:-$port}
        
        # Use 636 for ldaps if no port specified
        if [[ $server =~ ^ldaps:// ]] && [ -z "$extracted_port" ]; then
            port=636
        fi
    else
        local host=$server
    fi
    
    log_step "Testing connectivity to $host:$port..."
    
    if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$host/$port" 2>/dev/null; then
        log_success "LDAP server $host:$port is reachable"
        return 0
    else
        log_error "Cannot reach LDAP server $host:$port"
        return 1
    fi
}

################################################################################
# Database validation
################################################################################

validate_db_name() {
    local name=$1
    # Database name: alphanumeric and underscore only
    local regex="^[a-z][a-z0-9_]*$"
    
    [[ $name =~ $regex ]]
}

test_postgres_connection() {
    local user=$1
    local db=$2
    local password=$3
    
    log_step "Testing PostgreSQL connection..."
    
    if PGPASSWORD="$password" psql -U "$user" -d "$db" -c "SELECT 1" &>/dev/null; then
        log_success "PostgreSQL connection successful"
        return 0
    else
        log_error "PostgreSQL connection failed"
        return 1
    fi
}

################################################################################
# File system validation
################################################################################

validate_path() {
    local path=$1
    # Valid Unix path
    local regex="^/([a-zA-Z0-9_.-]+/?)*$"
    
    [[ $path =~ $regex ]]
}

check_disk_space() {
    local path=$1
    local required_gb=$2
    
    log_step "Checking disk space for $path..."
    
    local available_kb=$(df -k "$path" | awk 'NR==2 {print $4}')
    local available_gb=$((available_kb / 1024 / 1024))
    
    if [ $available_gb -ge $required_gb ]; then
        log_success "Sufficient disk space: ${available_gb}GB available (required: ${required_gb}GB)"
        return 0
    else
        log_error "Insufficient disk space: ${available_gb}GB available (required: ${required_gb}GB)"
        return 1
    fi
}

check_file_exists() {
    local file=$1
    
    if [ -f "$file" ]; then
        return 0
    fi
    return 1
}

check_directory_exists() {
    local dir=$1
    
    if [ -d "$dir" ]; then
        return 0
    fi
    return 1
}

check_writable() {
    local path=$1
    
    if [ -w "$path" ]; then
        return 0
    fi
    return 1
}

################################################################################
# System validation
################################################################################

check_os_version() {
    log_step "Checking OS version..."
    
    if [ -f /etc/os-release ]; then
        source /etc/os-release
        
        if [ "$ID" != "ubuntu" ]; then
            log_error "This script requires Ubuntu (detected: $ID)"
            return 1
        fi
        
        local version=$(echo "$VERSION_ID" | cut -d. -f1)
        if [ "$version" -lt 22 ]; then
            log_error "This script requires Ubuntu 22.04 or newer (detected: $VERSION_ID)"
            return 1
        fi
        
        log_success "OS version OK: Ubuntu $VERSION_ID"
        return 0
    else
        log_error "Cannot detect OS version"
        return 1
    fi
}

check_root() {
    if [ "$EUID" -eq 0 ]; then
        return 0
    fi
    return 1
}

check_memory() {
    local required_gb=$1
    
    log_step "Checking system memory..."
    
    local total_mem_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local total_mem_gb=$((total_mem_kb / 1024 / 1024))
    
    if [ $total_mem_gb -ge $required_gb ]; then
        log_success "Sufficient memory: ${total_mem_gb}GB (required: ${required_gb}GB)"
        return 0
    else
        log_error "Insufficient memory: ${total_mem_gb}GB (required: ${required_gb}GB)"
        return 1
    fi
}

check_cpu_cores() {
    local required_cores=$1
    
    log_step "Checking CPU cores..."
    
    local cores=$(nproc)
    
    if [ $cores -ge $required_cores ]; then
        log_success "Sufficient CPU cores: $cores (required: $required_cores)"
        return 0
    else
        log_warn "CPU cores below recommended: $cores (recommended: $required_cores)"
        return 0  # Warning only, not critical
    fi
}

check_internet() {
    log_step "Checking internet connectivity..."
    
    if ping -c 1 -W 2 8.8.8.8 &>/dev/null; then
        log_success "Internet connectivity OK"
        return 0
    else
        log_error "No internet connectivity"
        return 1
    fi
}

check_dns() {
    log_step "Checking DNS resolution..."
    
    if host github.com &>/dev/null; then
        log_success "DNS resolution OK"
        return 0
    else
        log_error "DNS resolution failed"
        return 1
    fi
}

################################################################################
# Service validation
################################################################################

check_port_available() {
    local port=$1
    
    # Usar ss (disponible por defecto en Ubuntu)
    if ss -tuln 2>/dev/null | grep -q ":${port} "; then
        log_error "Port $port is already in use"
        return 1
    else
        log_success "Port $port is available"
        return 0
    fi
}

check_service_exists() {
    local service=$1
    
    if systemctl list-unit-files | grep -q "^${service}.service"; then
        return 0
    fi
    return 1
}

################################################################################
# Package validation
################################################################################

check_package_installed() {
    local package=$1
    
    if dpkg -l | grep -q "^ii  $package "; then
        return 0
    fi
    return 1
}

check_command_exists() {
    local command=$1
    
    if command -v "$command" &>/dev/null; then
        return 0
    fi
    return 1
}

################################################################################
# Git validation
################################################################################

validate_git_url() {
    local url=$1
    local regex="^(https?|git)://[a-zA-Z0-9.-]+/.*\.git$|^git@[a-zA-Z0-9.-]+:.*\.git$"
    
    # Allow URLs without .git extension too
    if [[ $url =~ ^(https?|git)://[a-zA-Z0-9.-]+/.+ ]] || [[ $url =~ ^git@[a-zA-Z0-9.-]+:.+ ]]; then
        return 0
    fi
    return 1
}

test_git_access() {
    local repo_url=$1
    
    log_step "Testing git repository access..."
    
    if git ls-remote "$repo_url" HEAD &>/dev/null; then
        log_success "Git repository is accessible"
        return 0
    else
        log_error "Cannot access git repository"
        return 1
    fi
}

################################################################################
# Password validation
################################################################################

validate_password_strength() {
    local password=$1
    local min_length=${2:-12}
    
    # Check minimum length
    if [ ${#password} -lt $min_length ]; then
        return 1
    fi
    
    # Check for at least one uppercase
    if ! [[ $password =~ [A-Z] ]]; then
        return 1
    fi
    
    # Check for at least one lowercase
    if ! [[ $password =~ [a-z] ]]; then
        return 1
    fi
    
    # Check for at least one digit
    if ! [[ $password =~ [0-9] ]]; then
        return 1
    fi
    
    # Check for at least one special character
    if ! [[ $password =~ [^a-zA-Z0-9] ]]; then
        return 1
    fi
    
    return 0
}

################################################################################
# Configuration file validation
################################################################################

validate_env_file() {
    local env_file=$1
    
    log_step "Validating .env file..."
    
    local required_vars=(
        "DATABASE_URL"
        "SECRET_KEY"
        "LDAP_SERVER"
        "LDAP_BIND_DN"
        "LDAP_SEARCH_BASE"
    )
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" "$env_file"; then
            log_error "Missing required variable in .env: $var"
            return 1
        fi
    done
    
    log_success ".env file is valid"
    return 0
}