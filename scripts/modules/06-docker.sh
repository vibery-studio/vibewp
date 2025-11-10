#!/usr/bin/env bash
################################################################################
# Module: Docker Installation
# Purpose: Install Docker Engine and Docker Compose v2
################################################################################

setup_docker() {
    log "Setting up Docker..."

    local ssh_cmd="ssh -i $SSH_KEY -p $SSH_PORT $DEPLOYER_USER@$VPS_IP"

    # Remove old Docker versions
    log "Removing old Docker versions if present..."
    $ssh_cmd "sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true" 2>&1 | tee -a "$LOG_FILE"

    # Update package index
    log "Updating package index..."
    $ssh_cmd "sudo apt-get update" 2>&1 | tee -a "$LOG_FILE"

    # Install prerequisites
    log "Installing prerequisites..."
    $ssh_cmd "sudo apt-get install -y ca-certificates curl gnupg lsb-release" 2>&1 | tee -a "$LOG_FILE"

    # Add Docker GPG key
    log "Adding Docker GPG key..."
    $ssh_cmd "sudo install -m 0755 -d /etc/apt/keyrings" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "sudo chmod a+r /etc/apt/keyrings/docker.gpg" 2>&1 | tee -a "$LOG_FILE"

    # Add Docker repository
    log "Adding Docker repository..."
    $ssh_cmd 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null' 2>&1 | tee -a "$LOG_FILE"

    # Update package index again
    log "Updating package index with Docker repo..."
    $ssh_cmd "sudo apt-get update" 2>&1 | tee -a "$LOG_FILE"

    # Install Docker Engine and Docker Compose plugin
    log "Installing Docker Engine and Docker Compose..."
    $ssh_cmd "sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin" 2>&1 | tee -a "$LOG_FILE"

    # Start and enable Docker service
    log "Starting Docker service..."
    $ssh_cmd "sudo systemctl enable docker" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "sudo systemctl start docker" 2>&1 | tee -a "$LOG_FILE"

    # Verify Docker is running
    log "Verifying Docker service..."
    if $ssh_cmd "sudo systemctl is-active docker" | grep -q "active"; then
        log_success "Docker service is active"
    else
        log_error "Docker service failed to start"
        $ssh_cmd "sudo systemctl status docker" 2>&1 | tee -a "$LOG_FILE"
        return 1
    fi

    # Add deployer to docker group
    log "Adding $DEPLOYER_USER to docker group..."
    $ssh_cmd "sudo usermod -aG docker $DEPLOYER_USER" 2>&1 | tee -a "$LOG_FILE"

    # Test Docker installation
    log "Testing Docker installation..."
    if $ssh_cmd "sudo docker run --rm hello-world" 2>&1 | tee -a "$LOG_FILE" | grep -q "Hello from Docker"; then
        log_success "Docker installation verified"
    else
        log_error "Docker test failed"
        return 1
    fi

    # Test Docker Compose
    log "Testing Docker Compose..."
    $ssh_cmd "docker compose version" 2>&1 | tee -a "$LOG_FILE"

    # Display Docker info
    log "Docker information:"
    $ssh_cmd "sudo docker --version" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "docker compose version" 2>&1 | tee -a "$LOG_FILE"

    log_success "Docker setup completed"
    log_warning "Note: $DEPLOYER_USER needs to log out and back in for docker group to take effect"
    return 0
}
