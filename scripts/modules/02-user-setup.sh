#!/usr/bin/env bash
################################################################################
# Module: User Setup
# Purpose: Create deployer user with appropriate permissions
################################################################################

setup_user() {
    log "Setting up deployer user..."

    local ssh_cmd="ssh -i $SSH_KEY -p $SSH_PORT root@$VPS_IP"

    # Check if user already exists
    if $ssh_cmd "id $DEPLOYER_USER" &> /dev/null; then
        log_warning "User $DEPLOYER_USER already exists, skipping creation"
    else
        log "Creating user: $DEPLOYER_USER"

        # Generate random password
        local password
        password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

        # Create user with home directory
        $ssh_cmd "useradd -m -s /bin/bash $DEPLOYER_USER" 2>&1 | tee -a "$LOG_FILE"

        # Set password
        $ssh_cmd "echo '$DEPLOYER_USER:$password' | chpasswd" 2>&1 | tee -a "$LOG_FILE"

        log_success "User $DEPLOYER_USER created"
        log "Generated password: $password (save this securely)"
    fi

    # Add user to sudo group
    log "Adding $DEPLOYER_USER to sudo group..."
    $ssh_cmd "usermod -aG sudo $DEPLOYER_USER" 2>&1 | tee -a "$LOG_FILE"

    # Configure passwordless sudo for docker commands
    log "Configuring sudo permissions..."
    $ssh_cmd "echo '$DEPLOYER_USER ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose, /usr/sbin/ufw' | tee /etc/sudoers.d/$DEPLOYER_USER" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "chmod 0440 /etc/sudoers.d/$DEPLOYER_USER" 2>&1 | tee -a "$LOG_FILE"

    # Setup SSH directory for deployer
    log "Configuring SSH access for $DEPLOYER_USER..."
    $ssh_cmd "mkdir -p /home/$DEPLOYER_USER/.ssh" 2>&1 | tee -a "$LOG_FILE"

    # Copy authorized_keys from root
    $ssh_cmd "cp /root/.ssh/authorized_keys /home/$DEPLOYER_USER/.ssh/authorized_keys" 2>&1 | tee -a "$LOG_FILE"

    # Set proper permissions
    $ssh_cmd "chown -R $DEPLOYER_USER:$DEPLOYER_USER /home/$DEPLOYER_USER/.ssh" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "chmod 700 /home/$DEPLOYER_USER/.ssh" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "chmod 600 /home/$DEPLOYER_USER/.ssh/authorized_keys" 2>&1 | tee -a "$LOG_FILE"

    # Test deployer SSH access
    log "Testing SSH access for $DEPLOYER_USER..."
    if ssh -i "$SSH_KEY" -p "$SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=no "$DEPLOYER_USER@$VPS_IP" "echo 'Access verified'" 2>&1 | tee -a "$LOG_FILE"; then
        log_success "SSH access verified for $DEPLOYER_USER"
    else
        log_error "SSH access test failed for $DEPLOYER_USER"
        return 1
    fi

    log_success "User setup completed"
    return 0
}
