#!/usr/bin/env bash
################################################################################
# VPS Setup - Main Orchestrator
# Purpose: Automated VPS security hardening and Docker environment setup
# Usage: ./vps-setup.sh --ip <VPS_IP> [--port <SSH_PORT>] [--ssh-key <KEY_PATH>]
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/setup.log"
VPS_IP=""
SSH_PORT="22"
SSH_KEY=""
DEPLOYER_USER="deployer"
NEW_SSH_PORT="2222"

# Helper functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗${NC} $*" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠${NC} $*" | tee -a "$LOG_FILE"
}

usage() {
    cat << EOF
Usage: $0 --ip <VPS_IP> [OPTIONS]

Required:
  --ip <VPS_IP>           VPS IP address

Optional:
  --port <SSH_PORT>       Current SSH port (default: 22)
  --ssh-key <KEY_PATH>    Path to SSH private key
  --new-port <PORT>       New SSH port after hardening (default: 2222)
  --help                  Show this help message

Example:
  $0 --ip 157.90.159.172 --port 22 --new-port 2222
EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ip)
            VPS_IP="$2"
            shift 2
            ;;
        --port)
            SSH_PORT="$2"
            shift 2
            ;;
        --ssh-key)
            SSH_KEY="$2"
            shift 2
            ;;
        --new-port)
            NEW_SSH_PORT="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate required arguments
if [[ -z "$VPS_IP" ]]; then
    log_error "VPS IP is required"
    usage
fi

# Export variables for modules
export VPS_IP SSH_PORT SSH_KEY DEPLOYER_USER NEW_SSH_PORT LOG_FILE
export SCRIPT_DIR

# Source module functions
source_modules() {
    log "Loading modules..."
    local modules=(
        "00-preflight.sh"
        "01-ssh-keys.sh"
        "02-user-setup.sh"
        "03-ssh-harden.sh"
        "04-firewall.sh"
        "05-fail2ban.sh"
        "06-docker.sh"
        "07-system-harden.sh"
    )

    for module in "${modules[@]}"; do
        local module_path="${SCRIPT_DIR}/modules/${module}"
        if [[ -f "$module_path" ]]; then
            # shellcheck source=/dev/null
            source "$module_path"
        else
            log_error "Module not found: $module_path"
            exit 1
        fi
    done
    log_success "All modules loaded"
}

# Main execution
main() {
    log "========================================="
    log "VPS Setup - Phase 01: Initial Setup"
    log "========================================="
    log "Target VPS: $VPS_IP"
    log "Current SSH Port: $SSH_PORT"
    log "New SSH Port: $NEW_SSH_PORT"
    log "Deployer User: $DEPLOYER_USER"
    log "========================================="

    # Initialize log file
    echo "VPS Setup Log - $(date)" > "$LOG_FILE"

    # Load all modules
    source_modules

    # Execute modules in sequence
    log "\n[Phase 1/8] Running preflight checks..."
    run_preflight_checks || { log_error "Preflight checks failed"; exit 1; }

    log "\n[Phase 2/8] Setting up SSH keys..."
    setup_ssh_keys || { log_error "SSH key setup failed"; exit 1; }

    log "\n[Phase 3/8] Creating deployer user..."
    setup_user || { log_error "User setup failed"; exit 1; }

    log "\n[Phase 4/8] Hardening SSH configuration..."
    harden_ssh || { log_error "SSH hardening failed"; exit 1; }

    log "\n[Phase 5/8] Configuring firewall..."
    setup_firewall || { log_error "Firewall setup failed"; exit 1; }

    log "\n[Phase 6/8] Installing fail2ban..."
    setup_fail2ban || { log_error "Fail2ban setup failed"; exit 1; }

    log "\n[Phase 7/8] Installing Docker..."
    setup_docker || { log_error "Docker setup failed"; exit 1; }

    log "\n[Phase 8/8] Applying system hardening..."
    harden_system || { log_error "System hardening failed"; exit 1; }

    # Success summary
    log "\n========================================="
    log_success "VPS setup completed successfully!"
    log "========================================="
    log "\nConnection details:"
    log "  SSH: ssh -p $NEW_SSH_PORT $DEPLOYER_USER@$VPS_IP"
    if [[ -n "$SSH_KEY" ]]; then
        log "  Key: $SSH_KEY"
    fi
    log "\nNext steps:"
    log "  1. Test SSH connection with new settings"
    log "  2. Verify Docker: ssh -p $NEW_SSH_PORT $DEPLOYER_USER@$VPS_IP 'docker run hello-world'"
    log "  3. Check firewall: ssh -p $NEW_SSH_PORT $DEPLOYER_USER@$VPS_IP 'sudo ufw status'"
    log "  4. Review fail2ban: ssh -p $NEW_SSH_PORT $DEPLOYER_USER@$VPS_IP 'sudo fail2ban-client status sshd'"
    log "\nFull log: $LOG_FILE"
    log "========================================="
}

# Run main function
main "$@"
