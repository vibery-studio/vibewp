#!/usr/bin/env bash
################################################################################
# Module: System Hardening
# Purpose: Apply kernel and system-level security hardening
################################################################################

harden_system() {
    log "Applying system hardening..."

    local ssh_cmd="ssh -i $SSH_KEY -p $SSH_PORT $DEPLOYER_USER@$VPS_IP"
    local template_path="${SCRIPT_DIR}/templates/sysctl.conf.template"

    # Install unattended-upgrades
    log "Installing automatic security updates..."
    $ssh_cmd "sudo apt-get install -y unattended-upgrades apt-listchanges" 2>&1 | tee -a "$LOG_FILE"

    # Configure unattended-upgrades
    log "Configuring automatic security updates..."
    $ssh_cmd "sudo dpkg-reconfigure -plow unattended-upgrades" 2>&1 | tee -a "$LOG_FILE"

    # Enable automatic updates
    $ssh_cmd "echo 'APT::Periodic::Update-Package-Lists \"1\";
APT::Periodic::Download-Upgradeable-Packages \"1\";
APT::Periodic::AutocleanInterval \"7\";
APT::Periodic::Unattended-Upgrade \"1\";' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades" > /dev/null 2>&1

    log_success "Automatic security updates enabled"

    # Apply sysctl hardening
    if [[ -f "$template_path" ]]; then
        log "Applying kernel hardening via sysctl..."

        # Backup existing sysctl.conf
        $ssh_cmd "sudo cp /etc/sysctl.conf /etc/sysctl.conf.backup.$(date +%Y%m%d-%H%M%S)" 2>&1 | tee -a "$LOG_FILE"

        # Upload sysctl template
        cat "$template_path" | $ssh_cmd "sudo tee /etc/sysctl.d/99-custom-hardening.conf" > /dev/null 2>&1

        # Apply sysctl settings
        $ssh_cmd "sudo sysctl -p /etc/sysctl.d/99-custom-hardening.conf" 2>&1 | tee -a "$LOG_FILE"

        log_success "Kernel hardening applied"
    else
        log_warning "Sysctl template not found: $template_path"
    fi

    # Disable unused services
    log "Disabling unused services..."
    local services_to_disable=("telnet" "rsh" "rlogin")
    for service in "${services_to_disable[@]}"; do
        $ssh_cmd "sudo systemctl disable $service 2>/dev/null || true" 2>&1 | tee -a "$LOG_FILE"
    done

    # Configure log rotation
    log "Configuring log rotation..."
    $ssh_cmd "echo '/var/log/auth.log
{
    rotate 90
    daily
    missingok
    notifempty
    compress
    delaycompress
    postrotate
        /usr/lib/rsyslog/rsyslog-rotate
    endscript
}' | sudo tee /etc/logrotate.d/auth-logs" > /dev/null 2>&1

    # Set up basic system monitoring
    log "Installing monitoring tools..."
    $ssh_cmd "sudo apt-get install -y htop iotop nethogs" 2>&1 | tee -a "$LOG_FILE"

    # Configure timezone (optional, to UTC)
    log "Setting timezone to UTC..."
    $ssh_cmd "sudo timedatectl set-timezone UTC" 2>&1 | tee -a "$LOG_FILE"

    # Enable and configure NTP
    log "Configuring time synchronization..."
    $ssh_cmd "sudo systemctl enable systemd-timesyncd" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "sudo systemctl start systemd-timesyncd" 2>&1 | tee -a "$LOG_FILE"

    # Clean up unnecessary packages
    log "Cleaning up unnecessary packages..."
    $ssh_cmd "sudo apt-get autoremove -y" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "sudo apt-get autoclean -y" 2>&1 | tee -a "$LOG_FILE"

    # Display system information
    log "System information:"
    $ssh_cmd "uname -a" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "free -h" 2>&1 | tee -a "$LOG_FILE"
    $ssh_cmd "df -h /" 2>&1 | tee -a "$LOG_FILE"

    log_success "System hardening completed"
    return 0
}
