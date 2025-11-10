#!/usr/bin/env bash
################################################################################
# Module: Firewall Configuration
# Purpose: Setup UFW firewall with security rules
################################################################################

setup_firewall() {
    log "Configuring UFW firewall..."

    local ssh_cmd="ssh -i $SSH_KEY -p $SSH_PORT $DEPLOYER_USER@$VPS_IP"

    # Install UFW if not present
    log "Installing UFW..."
    $ssh_cmd "sudo apt-get update && sudo apt-get install -y ufw" 2>&1 | tee -a "$LOG_FILE"

    # Reset UFW to default state (idempotent)
    log "Resetting UFW to defaults..."
    $ssh_cmd "sudo ufw --force reset" 2>&1 | tee -a "$LOG_FILE"

    # Set default policies
    log "Setting default policies (deny incoming, allow outgoing)..."
    $ssh_cmd "sudo ufw default deny incoming" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "sudo ufw default allow outgoing" 2>&1 | tee -a "$LOG_FILE"

    # Allow SSH on custom port with rate limiting
    log "Allowing SSH on port $SSH_PORT with rate limiting..."
    $ssh_cmd "sudo ufw allow $SSH_PORT/tcp" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "sudo ufw limit $SSH_PORT/tcp comment 'SSH with rate limiting'" 2>&1 | tee -a "$LOG_FILE"

    # Allow HTTP
    log "Allowing HTTP (port 80)..."
    $ssh_cmd "sudo ufw allow 80/tcp comment 'HTTP'" 2>&1 | tee -a "$LOG_FILE"

    # Allow HTTPS
    log "Allowing HTTPS (port 443)..."
    $ssh_cmd "sudo ufw allow 443/tcp comment 'HTTPS'" 2>&1 | tee -a "$LOG_FILE"

    # Enable UFW
    log_warning "Enabling UFW firewall..."
    $ssh_cmd "sudo ufw --force enable" 2>&1 | tee -a "$LOG_FILE"

    # Wait for UFW to stabilize
    sleep 2

    # Verify SSH still works
    log "Verifying SSH connectivity after firewall activation..."
    if ssh -i "$SSH_KEY" -p "$SSH_PORT" -o ConnectTimeout=5 -o BatchMode=yes "$DEPLOYER_USER@$VPS_IP" "echo 'SSH OK'" &> /dev/null; then
        log_success "SSH connectivity verified after firewall setup"
    else
        log_error "SSH connectivity lost after firewall setup!"
        log_error "This should not happen. Check VPS console access."
        return 1
    fi

    # Display firewall status
    log "Firewall status:"
    $ssh_cmd "sudo ufw status numbered" 2>&1 | tee -a "$LOG_FILE"

    log_success "Firewall setup completed"
    return 0
}
