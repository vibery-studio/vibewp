#!/bin/bash
set -e

# VibeWP Installer - One-line installation script
# Usage: curl -fsSL https://raw.githubusercontent.com/vibery-studio/vibewp/main/install.sh | bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[VibeWP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check if running on Ubuntu
if [[ ! -f /etc/os-release ]] || ! grep -q "Ubuntu" /etc/os-release; then
    error "This installer only supports Ubuntu 22.04 and 24.04"
fi

# Check Ubuntu version
VERSION=$(grep VERSION_ID /etc/os-release | cut -d'"' -f2)
if [[ "$VERSION" != "22.04" && "$VERSION" != "24.04" ]]; then
    error "Ubuntu $VERSION is not supported. Only 22.04 and 24.04 are supported."
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

# Initialize config directory
mkdir -p ~/.vibewp
chmod 700 ~/.vibewp

# Verify installation
if command -v vibewp &> /dev/null; then
    VERSION=$(vibewp --version 2>&1 | grep -oP 'v\d+\.\d+\.\d+' || echo "unknown")
    log "✓ VibeWP $VERSION installed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Initialize configuration: vibewp config init"
    echo "  2. Edit VPS settings: vibewp config show"
    echo "  3. Create your first site: vibewp site create"
    echo ""
    echo "For help: vibewp --help"
else
    error "Installation failed. Please check the logs above."
fi
