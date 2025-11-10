# VibeWP Codebase Summary

**Version**: 1.0.0 | **Last Updated**: 2025-11-10

## Overview

VibeWP is a complete CLI tool for managing WordPress sites on VPS with automatic HTTPS, Docker isolation, and self-update capabilities.

## Architecture

```
vibewp/
├── core/              # Core functionality
│   ├── manager.py     # Main VPS/site operations
│   ├── docker.py      # Docker container management
│   └── updater.py     # Self-update system
├── commands/          # CLI command handlers
│   ├── site.py        # Site create/delete/list
│   ├── domain.py      # Domain management
│   ├── vps.py         # VPS operations
│   ├── backup.py      # Backup operations
│   ├── security.py    # Security commands + audit-server
│   ├── update.py      # Update commands
│   └── cli.py         # Main CLI entry
├── models/            # Data structures
├── utils/             # Helper utilities
│   ├── system_auditor.py        # System-level security audits
│   ├── wordpress_auditor.py     # WordPress-specific audits
│   ├── vulnerability_scanner.py # WPScan API integration
│   ├── report_generator.py      # Multi-format report generation
│   ├── server_audit.py          # Audit orchestration
│   └── config.py                # Config with WPScan token support
├── config/            # Configuration management
└── templates/         # Docker & config templates
```

## Key Components

### Self-Update System (NEW)
- **Location**: `cli/core/updater.py`
- **Features**:
  - GitHub API integration for version checking
  - Install method detection (pip/script/editable)
  - Automatic backup & rollback on failure
  - Config preservation during updates
  - Semantic versioning support

### Update Commands
- **Location**: `cli/commands/update.py`
- **Commands**:
  - `vibewp update check` - Check for updates
  - `vibewp update install` - Install latest version
  - `vibewp update cleanup` - Cleanup old backups
  - `vibewp update info` - Show install information
  - `vibewp --version` - Show version & install method

### Security Audit System
- **Location**: `cli/commands/security.py`, `cli/utils/server_audit.py`
- **Components**:
  - **SystemAuditor** (`cli/utils/system_auditor.py`): SSH, firewall, fail2ban, ports, services, users, updates, logs, filesystem permissions
  - **WordPressAuditor** (`cli/utils/wordpress_auditor.py`): Core version, plugins, themes, users, wp-config.php, file permissions
  - **VulnerabilityScanner** (`cli/utils/vulnerability_scanner.py`): WPScan API integration for CVE database matching
  - **ReportGenerator** (`cli/utils/report_generator.py`): Console, JSON, HTML, PDF report formats
  - **ServerAuditManager** (`cli/utils/server_audit.py`): Orchestrates all audits, calculates security score
- **Commands**:
  - `vibewp security audit-server` - Full server audit
  - `vibewp security set-wpscan-token` - Configure WPScan API
  - `vibewp security clear-wpscan-token` - Remove API token
  - `vibewp security scan` - Basic security scan
  - `vibewp security check-updates` - System updates
  - `vibewp security install-updates` - Install updates
- **Features**:
  - System-level security checks (9 categories)
  - WordPress-specific audits per site
  - Vulnerability scanning via WPScan API
  - Optional Lynis integration
  - Multi-format reports (console/JSON/HTML/PDF)
  - Overall security score (0-100)
  - Severity-based findings (critical/high/medium/low)
  - Auto-fix suggestions where applicable

### Core Manager
- **Location**: `cli/core/manager.py`
- **Responsibilities**:
  - Site CRUD operations
  - Domain management
  - Configuration state tracking

### Docker Management
- **Location**: `cli/core/docker.py`
- **Responsibilities**:
  - Container lifecycle management
  - Network isolation setup
  - Caddy reverse proxy orchestration

## Configuration

Config stored in `~/.vibewp/sites.yaml`:
```yaml
vps:
  host: "YOUR_VPS_IP"
  port: 22
  user: "root"
  key_path: "~/.ssh/id_rsa"
  install_method: "pip"            # pip, script, or editable
  wpscan_api_token: "YOUR_TOKEN"   # Optional, for vulnerability scanning

sites:
  myblog:
    domain: "blog.example.com"
    type: "frankenwp"
    status: "running"
    created: "2025-11-10T16:00:00Z"
```

## Installation Methods

VibeWP supports 3 installation methods, all with self-update capability:

1. **pip** - System-wide package installation
2. **script** - Standalone script installation (via install.sh)
3. **editable** - Development mode installation

The update system automatically detects the installation method and applies updates appropriately.

## Features

- One-line installation
- Multi-site WordPress management
- Dual engine support (FrankenWP/OpenLiteSpeed)
- Automatic HTTPS via Caddy
- Security-first design
- Self-update capability with backup/rollback
- Comprehensive security auditing (system + WordPress + vulnerabilities)
- Interactive CLI with menus
- Multi-format audit reports (console/JSON/HTML/PDF)
- Comprehensive logging

## Security Features

- SSH key-only authentication
- Custom SSH port with safe change mechanism
- UFW firewall integration
- fail2ban protection
- Automatic security updates
- 32-character database passwords
- Network isolation per site
- Automatic HTTPS (Let's Encrypt)
- Comprehensive security auditing:
  - System-level: SSH, firewall, fail2ban, ports, services, users, updates, logs, filesystem
  - WordPress: Core, plugins, themes, users, wp-config.php, file permissions
  - Vulnerability scanning: WPScan API integration for CVE database
  - Optional Lynis system hardening audit
  - Severity-based findings (critical/high/medium/low)
  - Security score calculation (0-100)
  - Auto-fix suggestions
  - Multi-format reports

## Development

- **Language**: Python 3.10+
- **Test Framework**: pytest
- **CLI Framework**: Click
- **Container**: Docker & Docker Compose v2
- **Config Format**: YAML

## Testing

Tests located in `tests/` directory:
- Unit tests for core functionality
- Integration tests for CLI commands
- E2E tests for update workflow

Run tests:
```bash
pytest tests/
pytest tests/ --cov=cli  # With coverage
```

## Entry Points

- **CLI**: `vibewp` command (installed via pip/setup.py)
- **Script**: `/usr/local/bin/vibewp` (via install.sh)
- **Version**: `vibewp --version`
