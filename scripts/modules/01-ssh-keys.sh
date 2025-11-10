#!/usr/bin/env bash
################################################################################
# Module: SSH Key Management
# Purpose: Generate and deploy SSH keys for secure authentication
################################################################################

setup_ssh_keys() {
    log "Setting up SSH keys..."

    local key_path="${SSH_KEY:-$HOME/.ssh/vps_manager_ed25519}"
    local key_pub="${key_path}.pub"

    # Generate key if not exists
    if [[ ! -f "$key_path" ]]; then
        log "Generating ed25519 SSH key pair..."
        ssh-keygen -t ed25519 -f "$key_path" -N "" -C "vps-manager-$(date +%Y%m%d)" 2>&1 | tee -a "$LOG_FILE"

        if [[ ! -f "$key_path" ]]; then
            log_error "Failed to generate SSH key"
            return 1
        fi
        log_success "SSH key pair generated: $key_path"
    else
        log_success "SSH key already exists: $key_path"
    fi

    # Update SSH_KEY variable if it was auto-generated
    if [[ -z "$SSH_KEY" ]]; then
        export SSH_KEY="$key_path"
    fi

    # Copy public key to VPS
    log "Deploying public key to VPS..."

    if [[ -f "$key_pub" ]]; then
        # Try automated ssh-copy-id first
        if ssh-copy-id -i "$key_pub" -p "$SSH_PORT" root@"$VPS_IP" 2>&1 | tee -a "$LOG_FILE"; then
            log_success "Public key deployed successfully"
        else
            log_warning "Automated key deployment failed"
            log "Public key content:"
            cat "$key_pub" | tee -a "$LOG_FILE"
            log "\nPlease manually add this key to root@$VPS_IP:~/.ssh/authorized_keys"
            read -p "Press Enter after adding the key manually..."
        fi
    else
        log_error "Public key not found: $key_pub"
        return 1
    fi

    # Test key authentication
    log "Testing SSH key authentication..."
    if ssh -i "$SSH_KEY" -p "$SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=no root@"$VPS_IP" "echo 'Key auth successful'" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "SSH key authentication verified"
    else
        log_error "SSH key authentication failed"
        return 1
    fi

    log_success "SSH key setup completed"
    return 0
}
