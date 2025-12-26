#!/bin/bash
set -e

# VibeWP Installer - One-line installation script
# Usage: curl -fsSL https://raw.githubusercontent.com/vibery-studio/vibewp/main/install.sh | sudo bash
#
# Copyright (c) 2024-2025 Vibery Production Studio
# https://vibery.app
# Licensed under MIT License

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[VibeWP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Display banner
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    VibeWP Installer                          ║"
echo "║           VPS WordPress Manager with Auto-HTTPS              ║"
echo "║                                                              ║"
echo "║              https://github.com/vibery-studio/vibewp         ║"
echo "║              Made by Vibery Production Studio                ║"
echo "║                    https://vibery.app                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run with sudo or as root.\n       Usage: curl -fsSL https://... | sudo bash"
fi

# Display warnings
echo -e "${YELLOW}${BOLD}⚠️  IMPORTANT WARNINGS:${NC}"
echo ""
echo -e "${YELLOW}  1. FRESH SERVER RECOMMENDED${NC}"
echo "     This installer is designed for fresh Ubuntu servers."
echo "     Running on existing servers may cause conflicts."
echo ""
echo -e "${YELLOW}  2. DATA RESPONSIBILITY${NC}"
echo "     You are responsible for your own data and backups."
echo "     We are not liable for any data loss or server issues."
echo ""
echo -e "${YELLOW}  3. PRODUCTION USE${NC}"
echo "     Test on a non-production server first."
echo "     Review the code at: https://github.com/vibery-studio/vibewp"
echo ""
echo -e "${YELLOW}  4. PORTS REQUIRED${NC}"
echo "     Ports 80 and 443 must be available for Caddy proxy."
echo ""

# Confirmation prompt (skip if -y flag or piped input)
if [[ -t 0 ]]; then
    read -p "Do you understand and accept these terms? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Installation cancelled."
        exit 0
    fi
else
    warn "Running in non-interactive mode. Proceeding with installation..."
    sleep 2
fi

echo ""

# Check if running on Ubuntu
if [[ ! -f /etc/os-release ]] || ! grep -q "Ubuntu" /etc/os-release; then
    error "This installer only supports Ubuntu 22.04, 24.04, and 25.04"
fi

# Check Ubuntu version
VERSION=$(grep VERSION_ID /etc/os-release | cut -d'"' -f2)
if [[ "$VERSION" != "22.04" && "$VERSION" != "24.04" && "$VERSION" != "25.04" ]]; then
    error "Ubuntu $VERSION is not supported. Only 22.04, 24.04, and 25.04 are supported."
fi

log "Installing VibeWP on Ubuntu $VERSION..."

# Install dependencies
log "Installing dependencies..."
apt-get update -qq
apt-get install -y -qq git python3 python3-pip python3-venv curl

# Clone repository
INSTALL_DIR="/opt/vibewp"
if [[ -d "$INSTALL_DIR/.git" ]]; then
    log "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull -q
elif [[ -d "$INSTALL_DIR" ]]; then
    log "Removing incomplete installation..."
    rm -rf "$INSTALL_DIR"
    log "Cloning VibeWP repository..."
    git clone -q https://github.com/vibery-studio/vibewp.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
else
    log "Cloning VibeWP repository..."
    git clone -q https://github.com/vibery-studio/vibewp.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create virtual environment
log "Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python package
log "Installing VibeWP CLI..."
pip install -q --upgrade pip
pip install -q -e .

# Create symlink for global access
log "Creating global command..."
ln -sf "$INSTALL_DIR/venv/bin/vibewp" /usr/local/bin/vibewp
chmod +x /usr/local/bin/vibewp

# Setup SSH key for localhost access (needed for Docker management)
log "Configuring SSH for localhost access..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

if [[ ! -f ~/.ssh/id_rsa ]]; then
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "" -C "vibewp-localhost" -q
    cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
    log "✓ SSH key generated and authorized"
else
    # Ensure key is authorized
    if ! grep -q "$(cat ~/.ssh/id_rsa.pub)" ~/.ssh/authorized_keys 2>/dev/null; then
        cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
    fi
    log "✓ SSH key already configured"
fi

# Test localhost SSH (add to known_hosts)
ssh-keyscan -H localhost >> ~/.ssh/known_hosts 2>/dev/null || true

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com | sh

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    # Add current user to docker group (if not root)
    if [[ $EUID -ne 0 && -n "$SUDO_USER" ]]; then
        usermod -aG docker "$SUDO_USER"
        log "Added $SUDO_USER to docker group (logout required for non-sudo docker)"
    fi

    # Wait for Docker to be ready
    sleep 3

    if command -v docker &> /dev/null; then
        log "✓ Docker installed successfully"
    else
        error "Docker installation failed"
    fi
else
    log "✓ Docker is installed"
fi

# Create proxy network if it doesn't exist
if ! docker network ls | grep -q "proxy"; then
    log "Creating proxy network..."
    docker network create proxy >/dev/null 2>&1 || true
    log "✓ Proxy network created"
else
    log "✓ Proxy network already exists"
fi

# Deploy Caddy proxy if not running
if ! docker ps | grep -q caddy_proxy; then
    log "Deploying Caddy reverse proxy..."
    cd "$INSTALL_DIR"
    docker compose -f templates/caddy/docker-compose.yml up -d >/dev/null 2>&1 || warn "Failed to deploy Caddy (will retry later)"
else
    log "✓ Caddy proxy already running"
fi

# Initialize config directory
mkdir -p ~/.vibewp
chmod 700 ~/.vibewp

# Create initial config if it doesn't exist
if [[ ! -f ~/.vibewp/sites.yaml ]]; then
    log "Creating initial configuration..."
    cat > ~/.vibewp/sites.yaml << 'CONFIGEOF'
vps:
  host: localhost
  port: 22
  user: root
  key_path: ~/.ssh/id_rsa
wordpress:
  default_admin_email: admin@example.com
  default_timezone: UTC
  default_locale: en_US
docker:
  base_path: /opt/vibewp
  network_name: proxy
sites: []
CONFIGEOF
    chmod 600 ~/.vibewp/sites.yaml
    log "✓ Configuration initialized"
else
    log "✓ Configuration already exists"
fi

# Verify installation
if command -v vibewp &> /dev/null; then
    VERSION=$(vibewp --version 2>&1 | grep -oP 'v\d+\.\d+\.\d+' || echo "unknown")
    log "✓ VibeWP $VERSION installed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Test SSH connection: vibewp test-ssh"
    echo "  2. View configuration: vibewp config show"
    echo "  3. Create your first site: vibewp site create"
    echo ""
    echo "For help: vibewp --help"
else
    error "Installation failed. Please check the logs above."
fi
