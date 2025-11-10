#!/usr/bin/env bash
################################################################################
# Module: SSH Hardening
# Purpose: Secure SSH daemon configuration
################################################################################

harden_ssh() {
    log "Hardening SSH configuration..."

    local ssh_cmd="ssh -i $SSH_KEY -p $SSH_PORT root@$VPS_IP"
    local template_path="${SCRIPT_DIR}/templates/sshd_config.template"

    # Backup original sshd_config
    log "Backing up original sshd_config..."
    $ssh_cmd "cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d-%H%M%S)" 2>&1 | tee -a "$LOG_FILE"
    log_success "Backup created"

    # Check if template exists
    if [[ ! -f "$template_path" ]]; then
        log_error "SSH config template not found: $template_path"
        return 1
    fi

    # Apply SSH configuration template
    log "Applying hardened SSH configuration (Port: $NEW_SSH_PORT)..."

    # Replace port placeholder in template and upload
    sed "s/{{SSH_PORT}}/$NEW_SSH_PORT/g" "$template_path" | $ssh_cmd "cat > /etc/ssh/sshd_config" 2>&1 | tee -a "$LOG_FILE"

    # Verify configuration syntax
    log "Validating SSH configuration..."
    if ! $ssh_cmd "sshd -t" 2>&1 | tee -a "$LOG_FILE"; then
        log_error "SSH configuration validation failed"
        log "Restoring backup..."
        $ssh_cmd "cp /etc/ssh/sshd_config.backup.* /etc/ssh/sshd_config" 2>&1 | tee -a "$LOG_FILE"
        return 1
    fi
    log_success "SSH configuration valid"

    # Warn user about SSH port change
    log_warning "========================================="
    log_warning "IMPORTANT: SSH port will change to $NEW_SSH_PORT"
    log_warning "Keep this terminal open until verified!"
    log_warning "========================================="
    read -p "Press Enter to restart SSH daemon..."

    # Restart SSH service
    log "Restarting SSH service..."
    $ssh_cmd "systemctl restart sshd" 2>&1 | tee -a "$LOG_FILE"

    # Wait for SSH to restart
    sleep 3

    # Test connection on new port with deployer user
    log "Testing SSH connection on new port $NEW_SSH_PORT..."
    local test_count=0
    local max_attempts=5

    while [[ $test_count -lt $max_attempts ]]; do
        if ssh -i "$SSH_KEY" -p "$NEW_SSH_PORT" -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=no "$DEPLOYER_USER@$VPS_IP" "echo 'New port OK'" &> /dev/null; then
            log_success "SSH accessible on port $NEW_SSH_PORT"
            # Update SSH_PORT for subsequent modules
            export SSH_PORT="$NEW_SSH_PORT"
            break
        fi
        test_count=$((test_count + 1))
        log_warning "Attempt $test_count/$max_attempts failed, retrying..."
        sleep 2
    done

    if [[ $test_count -eq $max_attempts ]]; then
        log_error "Cannot connect to SSH on new port $NEW_SSH_PORT"
        log_error "You may need to manually restore: ssh -p 22 root@$VPS_IP 'cp /etc/ssh/sshd_config.backup.* /etc/ssh/sshd_config && systemctl restart sshd'"
        return 1
    fi

    # Verify root login disabled
    log "Verifying root login is disabled..."
    if ssh -i "$SSH_KEY" -p "$NEW_SSH_PORT" -o BatchMode=yes root@"$VPS_IP" "echo 'Root still accessible'" &> /dev/null; then
        log_warning "Root login still accessible (may require reboot)"
    else
        log_success "Root login disabled"
    fi

    log_success "SSH hardening completed"
    return 0
}
