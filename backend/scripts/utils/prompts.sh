#!/bin/bash
################################################################################
# Interactive Prompts
# Funciones para interactuar con el usuario
################################################################################

################################################################################
# Basic prompts
################################################################################

prompt_input() {
    local prompt_text=$1
    local default_value=$2
    local value
    
    if [ -n "$default_value" ]; then
        read -p "$(echo -e ${CYAN}${SYMBOL_ARROW}${NC}) $prompt_text [$default_value]: " value
        value=${value:-$default_value}
    else
        read -p "$(echo -e ${CYAN}${SYMBOL_ARROW}${NC}) $prompt_text: " value
    fi
    
    echo "$value"
}

prompt_password() {
    local prompt_text=$1
    local value
    
    # Use stderr for the newline so it is printed to the terminal even when
    # the function output is captured via command substitution
    read -s -p "$(echo -e ${CYAN}${SYMBOL_ARROW}${NC}) $prompt_text: " value
    printf '\n' >&2
    echo "$value"
}

prompt_yes_no() {
    local prompt_text=$1
    local default="${2:-n}"
    local response
    
    if [ "$default" = "y" ]; then
        read -p "$(echo -e ${CYAN}${SYMBOL_ARROW}${NC}) $prompt_text (Y/n): " response
    else
        read -p "$(echo -e ${CYAN}${SYMBOL_ARROW}${NC}) $prompt_text (y/N): " response
    fi
    
    response=${response:-$default}
    
    [[ "$response" =~ ^[Yy]$ ]]
}

prompt_choice() {
    local prompt_text=$1
    shift
    local options=("$@")
    local choice
    
    echo ""
    echo -e "${CYAN}$prompt_text${NC}"
    echo ""
    
    for i in "${!options[@]}"; do
        echo "  $((i+1))) ${options[$i]}"
    done
    
    echo ""
    while true; do
        read -p "$(echo -e ${CYAN}${SYMBOL_ARROW}${NC}) Choose [1-${#options[@]}]: " choice
        
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
            echo "${options[$((choice-1))]}"
            return 0
        else
            echo -e "${RED}Invalid choice. Please select 1-${#options[@]}${NC}"
        fi
    done
}

################################################################################
# Validated prompts
################################################################################

prompt_hostname_or_ip() {
    local prompt_text=$1
    local default_value=$2
    local value
    
    while true; do
        value=$(prompt_input "$prompt_text" "$default_value")
        
        if validate_hostname_or_ip "$value"; then
            echo "$value"
            return 0
        else
            echo -e "${RED}Invalid hostname or IP address. Please try again.${NC}"
        fi
    done
}

prompt_email() {
    local prompt_text=$1
    local default_value=$2
    local value
    
    while true; do
        value=$(prompt_input "$prompt_text" "$default_value")
        
        if validate_email "$value"; then
            echo "$value"
            return 0
        else
            echo -e "${RED}Invalid email address. Please try again.${NC}"
        fi
    done
}

prompt_port() {
    local prompt_text=$1
    local default_value=$2
    local value
    
    while true; do
        value=$(prompt_input "$prompt_text" "$default_value")
        
        if validate_port "$value"; then
            echo "$value"
            return 0
        else
            echo -e "${RED}Invalid port number (1-65535). Please try again.${NC}"
        fi
    done
}

prompt_ldap_url() {
    local prompt_text=$1
    local default_value=$2
    local value
    
    while true; do
        value=$(prompt_input "$prompt_text" "$default_value")
        
        if validate_ldap_url "$value"; then
            echo "$value"
            return 0
        else
            echo -e "${RED}Invalid LDAP URL format (e.g., ldaps://server:636). Please try again.${NC}"
        fi
    done
}

prompt_dn() {
    local prompt_text=$1
    local default_value=$2
    local value
    
    while true; do
        value=$(prompt_input "$prompt_text" "$default_value")
        
        if validate_dn "$value"; then
            echo "$value"
            return 0
        else
            echo -e "${RED}Invalid DN format (e.g., cn=user,dc=example,dc=com). Please try again.${NC}"
        fi
    done
}

prompt_db_name() {
    local prompt_text=$1
    local default_value=$2
    local value
    
    while true; do
        value=$(prompt_input "$prompt_text" "$default_value")
        
        if validate_db_name "$value"; then
            echo "$value"
            return 0
        else
            echo -e "${RED}Invalid database name (lowercase letters, numbers, underscores only). Please try again.${NC}"
        fi
    done
}

prompt_path() {
    local prompt_text=$1
    local default_value=$2
    local value
    
    while true; do
        value=$(prompt_input "$prompt_text" "$default_value")
        
        if validate_path "$value"; then
            echo "$value"
            return 0
        else
            echo -e "${RED}Invalid path format. Please try again.${NC}"
        fi
    done
}

################################################################################
# Password prompts
################################################################################

prompt_strong_password() {
    local prompt_text=$1
    local min_length=${2:-12}
    local password
    local password_confirm
    
    while true; do
        password=$(prompt_password "$prompt_text")
        
        if ! validate_password_strength "$password" "$min_length"; then
            echo -e "${RED}Password does not meet requirements:${NC}"
            echo "  • Minimum $min_length characters"
            echo "  • At least one uppercase letter"
            echo "  • At least one lowercase letter"
            echo "  • At least one digit"
            echo "  • At least one special character"
            continue
        fi
        
        password_confirm=$(prompt_password "Confirm password")
        
        if [ "$password" = "$password_confirm" ]; then
            echo "$password"
            return 0
        else
            echo -e "${RED}Passwords do not match. Please try again.${NC}"
        fi
    done
}

################################################################################
# Advanced prompts
################################################################################

prompt_multiline() {
    local prompt_text=$1
    local end_marker="${2:-EOF}"
    
    echo -e "${CYAN}${SYMBOL_ARROW}${NC} $prompt_text"
    echo -e "${YELLOW}(Type '$end_marker' on a new line to finish)${NC}"
    
    local input=""
    local line
    
    while IFS= read -r line; do
        if [ "$line" = "$end_marker" ]; then
            break
        fi
        input+="$line"$'\n'
    done
    
    echo "$input"
}

prompt_file_path() {
    local prompt_text=$1
    local must_exist=${2:-false}
    local value
    
    while true; do
        value=$(prompt_input "$prompt_text")
        
        if [ "$must_exist" = true ] && [ ! -f "$value" ]; then
            echo -e "${RED}File does not exist: $value${NC}"
            continue
        fi
        
        echo "$value"
        return 0
    done
}

prompt_directory_path() {
    local prompt_text=$1
    local must_exist=${2:-false}
    local value
    
    while true; do
        value=$(prompt_input "$prompt_text")
        
        if [ "$must_exist" = true ] && [ ! -d "$value" ]; then
            echo -e "${RED}Directory does not exist: $value${NC}"
            
            if prompt_yes_no "Create directory?"; then
                mkdir -p "$value"
                echo "$value"
                return 0
            fi
            continue
        fi
        
        echo "$value"
        return 0
    done
}

################################################################################
# Confirmation dialogs
################################################################################

confirm_continue() {
    local message="${1:-Do you want to continue?}"
    
    echo ""
    if ! prompt_yes_no "$message"; then
        log_warn "Operation cancelled by user"
        return 1
    fi
    return 0
}

confirm_destructive() {
    local action=$1
    
    echo ""
    log_warn "⚠️  DESTRUCTIVE ACTION: $action"
    echo ""
    
    if ! prompt_yes_no "Are you absolutely sure?"; then
        log_info "Action cancelled"
        return 1
    fi
    
    # Double confirmation for destructive actions
    if ! prompt_yes_no "Type 'yes' to confirm" "n"; then
        log_info "Action cancelled"
        return 1
    fi
    
    return 0
}

################################################################################
# Progress indication
################################################################################

press_any_key() {
    local message="${1:-Press any key to continue...}"
    
    echo ""
    read -n 1 -s -r -p "$(echo -e ${CYAN}${SYMBOL_ARROW}${NC}) $message"
    echo ""
}

wait_for_user() {
    local message=$1
    local seconds=${2:-5}
    
    echo ""
    echo -e "${YELLOW}$message${NC}"
    echo -e "${YELLOW}Waiting ${seconds} seconds...${NC}"
    
    for i in $(seq $seconds -1 1); do
        echo -ne "\r${YELLOW}$i seconds remaining...${NC}"
        sleep 1
    done
    echo -ne "\r${GREEN}Continuing...          ${NC}\n"
    echo ""
}

################################################################################
# Information display
################################################################################

show_info_box() {
    local title=$1
    shift
    local lines=("$@")
    
    local max_length=0
    for line in "${lines[@]}"; do
        if [ ${#line} -gt $max_length ]; then
            max_length=${#line}
        fi
    done
    
    local width=$((max_length + 4))
    
    echo ""
    echo -e "${BLUE}╔$(printf '═%.0s' $(seq 1 $width))╗${NC}"
    echo -e "${BLUE}║${NC} ${WHITE}${title}${NC}$(printf ' %.0s' $(seq 1 $((width - ${#title} - 1))))${BLUE}║${NC}"
    echo -e "${BLUE}╠$(printf '═%.0s' $(seq 1 $width))╣${NC}"
    
    for line in "${lines[@]}"; do
        echo -e "${BLUE}║${NC} ${line}$(printf ' %.0s' $(seq 1 $((width - ${#line} - 1))))${BLUE}║${NC}"
    done
    
    echo -e "${BLUE}╚$(printf '═%.0s' $(seq 1 $width))╝${NC}"
    echo ""
}

show_warning_box() {
    local title=$1
    shift
    local lines=("$@")
    
    echo ""
    echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║${NC} ${RED}⚠️  WARNING: ${title}${NC}$(printf ' %.0s' $(seq 1 $((45 - ${#title}))))${YELLOW}║${NC}"
    echo -e "${YELLOW}╠═══════════════════════════════════════════════════════════╣${NC}"
    
    for line in "${lines[@]}"; do
        echo -e "${YELLOW}║${NC} ${line}$(printf ' %.0s' $(seq 1 $((58 - ${#line}))))${YELLOW}║${NC}"
    done
    
    echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

################################################################################
# Menu system
################################################################################

show_menu() {
    local title=$1
    shift
    local options=("$@")
    
    while true; do
        clear
        log_section "$title"
        
        for i in "${!options[@]}"; do
            echo "  $((i+1))) ${options[$i]}"
        done
        echo ""
        echo "  0) Exit"
        echo ""
        
        read -p "$(echo -e ${CYAN}${SYMBOL_ARROW}${NC}) Select option: " choice
        
        if [ "$choice" = "0" ]; then
            return 255
        elif [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#options[@]}" ]; then
            return $((choice - 1))
        else
            echo -e "${RED}Invalid choice${NC}"
            sleep 1
        fi
    done
}

################################################################################
# Comparison display
################################################################################

show_comparison() {
    local title=$1
    local option1_title=$2
    local option1_desc=$3
    local option2_title=$4
    local option2_desc=$5
    
    echo ""
    log_section "$title"
    
    echo -e "${GREEN}Option 1: $option1_title${NC}"
    echo "$option1_desc"
    echo ""
    
    echo -e "${YELLOW}Option 2: $option2_title${NC}"
    echo "$option2_desc"
    echo ""
    
    if prompt_yes_no "Choose Option 1?"; then
        return 0
    else
        return 1
    fi
}