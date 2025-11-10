#!/usr/bin/env bash
################################################################################
# Module: Fail2Ban Configuration
# Purpose: Install and configure intrusion prevention system
################################################################################

setup_fail2ban() {
    log "Setting up fail2ban..."

    local ssh_cmd="ssh -i $SSH_KEY -p $SSH_PORT $DEPLOYER_USER@$VPS_IP"
    local template_path="${SCRIPT_DIR}/templates/jail.local.template"

    # Install fail2ban
    log "Installing fail2ban..."
    $ssh_cmd "sudo apt-get update && sudo apt-get install -y fail2ban" 2>&1 | tee -a "$LOG_FILE"

    # Check if template exists
    if [[ ! -f "$template_path" ]]; then
        log_error "Fail2ban template not found: $template_path"
        return 1
    fi

    # Apply jail.local configuration
    log "Applying fail2ban configuration (SSH port: $SSH_PORT)..."

    # Replace SSH_PORT placeholder and upload
    sed "s/{{SSH_PORT}}/$SSH_PORT/g" "$template_path" | $ssh_cmd "sudo tee /etc/fail2ban/jail.local" > /dev/null 2>&1

    # Start and enable fail2ban
    log "Starting fail2ban service..."
    $ssh_cmd "sudo systemctl enable fail2ban" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "sudo systemctl restart fail2ban" 2>&1 | tee -a "$LOG_FILE"

    # Wait for service to start
    sleep 3

    # Verify fail2ban is running
    log "Verifying fail2ban status..."
    if $ssh_cmd "sudo systemctl is-active fail2ban" | grep -q "active"; then
        log_success "Fail2ban service is active"
    else
        log_error "Fail2ban service failed to start"
        $ssh_cmd "sudo systemctl status fail2ban" 2>&1 | tee -a "$LOG_FILE"
        return 1
    fi

    # Check sshd jail status
    log "Checking sshd jail status..."
    $ssh_cmd "sudo fail2ban-client status sshd" 2>&1 | tee -a "$LOG_FILE"

    # Display fail2ban status
    log "Fail2ban status:"
    $ssh_cmd "sudo fail2ban-client status" 2>&1 | tee -a "$LOG_FILE"

    log_success "Fail2ban setup completed"
    return 0
}
