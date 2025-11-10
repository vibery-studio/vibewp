#!/usr/bin/env bash
################################################################################
# Module: Preflight Checks
# Purpose: Validate prerequisites and connectivity before setup
################################################################################

run_preflight_checks() {
    log "Running preflight checks..."

    # Check local dependencies
    local required_commands=("ssh" "ssh-keygen" "ssh-copy-id")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Required command not found: $cmd"
            return 1
        fi
    done
    log_success "Local dependencies verified"

    # Test SSH connectivity
    log "Testing SSH connectivity to $VPS_IP:$SSH_PORT..."
    local ssh_cmd="ssh -p $SSH_PORT"
    [[ -n "$SSH_KEY" ]] && ssh_cmd="$ssh_cmd -i $SSH_KEY"

    if ! timeout 10 $ssh_cmd -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no root@"$VPS_IP" "echo 'SSH OK'" &> /dev/null; then
        log_warning "SSH key authentication failed, trying with password..."
        if ! timeout 10 ssh -p "$SSH_PORT" -o ConnectTimeout=5 root@"$VPS_IP" "echo 'SSH OK'" 2>&1 | grep -q "password"; then
            log_error "Cannot connect to VPS. Check IP, port, and credentials."
            return 1
        fi
    fi
    log_success "SSH connectivity verified"

    # Check OS compatibility
    log "Checking OS compatibility..."
    local ssh_cmd="ssh -p $SSH_PORT"
    [[ -n "$SSH_KEY" ]] && ssh_cmd="$ssh_cmd -i $SSH_KEY"

    local os_info
    os_info=$($ssh_cmd root@"$VPS_IP" "cat /etc/os-release" 2>/dev/null)

    if ! echo "$os_info" | grep -qE "Ubuntu (22\.04|24\.04)"; then
        log_error "Unsupported OS. Only Ubuntu 22.04 and 24.04 are supported."
        log_error "Detected OS:"
        echo "$os_info" | grep "PRETTY_NAME" | tee -a "$LOG_FILE"
        return 1
    fi
    log_success "OS compatibility verified (Ubuntu 22.04/24.04)"

    # Check available disk space
    log "Checking disk space..."
    local ssh_cmd="ssh -p $SSH_PORT"
    [[ -n "$SSH_KEY" ]] && ssh_cmd="$ssh_cmd -i $SSH_KEY"

    local available_gb
    available_gb=$($ssh_cmd root@"$VPS_IP" "df -BG / | tail -1 | awk '{print \$4}'" | tr -d 'G')

    if [[ "$available_gb" -lt 20 ]]; then
        log_warning "Low disk space: ${available_gb}GB available (recommended: 20GB+)"
    else
        log_success "Disk space sufficient: ${available_gb}GB available"
    fi

    # Check if VPS is reachable on HTTP/HTTPS ports
    log "Checking network ports..."
    if nc -z -w5 "$VPS_IP" 80 2>/dev/null; then
        log_success "Port 80 (HTTP) is open"
    else
        log_warning "Port 80 (HTTP) appears closed or filtered"
    fi

    if nc -z -w5 "$VPS_IP" 443 2>/dev/null; then
        log_success "Port 443 (HTTPS) is open"
    else
        log_warning "Port 443 (HTTPS) appears closed or filtered"
    fi

    log_success "Preflight checks completed"
    return 0
}
