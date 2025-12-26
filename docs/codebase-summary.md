# VibeWP Codebase Summary

**Version**: 1.6.2 | **Last Updated**: 2025-12-25

## Overview

VibeWP is a production-ready CLI tool for managing WordPress sites on VPS with automatic HTTPS, Docker isolation, security auditing, and advanced operations.

## Project Statistics

- **Total Files**: 98
- **Total Tokens**: 172,682 (7.5 MB source)
- **Language**: Python 3.10+
- **CLI Framework**: Typer 0.12+
- **Package Manager**: pip / script install
- **Config Format**: YAML (sites.yaml)

## Directory Structure

```
wpserver/
├── cli/                        # Main CLI package (50+ files)
│   ├── commands/               # 16 command modules
│   │   ├── __init__.py         # Typer app registration
│   │   ├── site.py             # Create/list/delete sites (3,682 lines)
│   │   ├── domain.py           # Domain management
│   │   ├── backup.py           # Local + remote backups
│   │   ├── security.py         # Audits + hardening
│   │   ├── malware.py          # Malware scanning
│   │   ├── sftp.py             # SFTP access management
│   │   ├── firewall.py         # UFW port management
│   │   ├── ssh_cmd.py          # SSH port management
│   │   ├── php.py              # PHP limit configuration
│   │   ├── proxy.py            # Caddy reload/status
│   │   ├── system.py           # Monitoring + doctor
│   │   ├── update.py           # Self-update system
│   │   ├── config.py           # Configuration init/show
│   │   ├── doctor.py           # System diagnostics
│   │   └── test_backup.py      # Backup testing
│   ├── utils/                  # 30+ utility modules
│   │   ├── config.py           # YAML config manager
│   │   ├── docker.py           # Docker orchestration
│   │   ├── caddy.py            # Reverse proxy config
│   │   ├── wordpress.py        # WP-CLI wrapper
│   │   ├── database.py         # MariaDB operations
│   │   ├── ssh.py              # SSH client (Paramiko)
│   │   ├── backup.py           # Local backup logic
│   │   ├── remote_backup.py    # S3 backup uploads
│   │   ├── sftp.py             # Chroot jail setup
│   │   ├── firewall.py         # UFW wrapper
│   │   ├── security.py         # Security utilities
│   │   ├── server_audit.py     # Audit orchestration
│   │   ├── system_auditor.py   # System-level audits
│   │   ├── wordpress_auditor.py # WordPress audits
│   │   ├── vulnerability_scanner.py # WPScan API
│   │   ├── report_generator.py  # Multi-format reports
│   │   ├── credentials.py       # Secure password gen
│   │   ├── validators.py        # Domain/email/IP/port
│   │   ├── dns.py              # DNS validation
│   │   ├── health.py           # Container health
│   │   ├── permissions.py      # File permission fixes
│   │   ├── template.py         # Jinja2 rendering
│   │   ├── version.py          # Semantic versioning
│   │   ├── update.py           # Update logic
│   │   ├── github.py           # GitHub API client
│   │   ├── lynis_integration.py # Lynis wrapper
│   │   ├── audit_report.py     # Report utilities
│   │   └── __init__.py
│   ├── ui/                     # UI components
│   │   ├── console.py          # Rich formatting
│   │   ├── menu.py             # Questionary menus
│   │   └── __init__.py
│   ├── main.py                 # CLI entry point
│   └── __init__.py             # Package init
├── templates/                  # Docker + config templates
│   ├── frankenwp/             # FrankenWP stack
│   │   └── docker-compose.yml.j2
│   ├── ols/                   # OpenLiteSpeed stack
│   │   └── docker-compose.yml.j2
│   ├── caddy/                 # Caddy config
│   │   └── Caddyfile.j2
│   └── *.j2                   # Config templates
├── scripts/                    # VPS setup scripts (8 bash modules)
│   ├── init.sh                # Initial setup
│   ├── docker-setup.sh        # Docker pre-requisites
│   └── *.sh
├── tests/                      # Test suite (100+ methods)
│   ├── unit/
│   ├── integration/
│   ├── conftest.py
│   └── test_*.py
├── docs/                       # Documentation
│   ├── project-overview-pdr.md # PDR + requirements
│   ├── code-standards.md       # Code conventions
│   ├── system-architecture.md  # Architecture diagram
│   ├── codebase-summary.md    # This file
│   ├── security-audit-guide.md # Security audit details
│   ├── sftp-access-guide.md   # SFTP setup guide
│   └── *.md
├── changelogs/                 # Version history
│   ├── README.md              # Changelog index
│   └── 251112-remote-backups.md
├── material/                   # Assets
│   └── vibewp-menu-screenshot.jpeg
├── config/                     # Reserved for config templates
├── README.md                   # User documentation
├── CLAUDE.md                   # Development guidance
├── setup.py                    # Package installation
├── pyproject.toml             # Project metadata
├── pytest.ini                 # Test configuration
├── .gitignore
├── .pre-commit-config.yaml
├── LICENSE
└── repomix-output.xml         # Codebase snapshot
```

## Key Components

### 1. CLI Entry Point
- **File**: `cli/main.py`
- **Purpose**: Typer app initialization, command registration
- **Export**: `app: typer.Typer` (installed as `vibewp` command)

### 2. Site Management
- **Command**: `cli/commands/site.py`
- **Utils**: `cli/utils/docker.py`, `cli/utils/wordpress.py`
- **Functions**:
  - `create_site()` - Deploy containers, init WordPress
  - `list_sites()` - Show all sites
  - `start_site()` / `stop_site()` / `restart_site()`
  - `delete_site()` - Remove site + backups
  - `fix_permissions()` - Restore file permissions
  - `reinstall_core()` - Recover from hack

### 3. Domain Management
- **Command**: `cli/commands/domain.py`
- **Utils**: `cli/utils/caddy.py`, `cli/utils/dns.py`
- **Functions**:
  - `add_domain()` - Add to Caddy config + cert
  - `remove_domain()` - Clean Caddy config
  - `set_primary_domain()` - Update site config
  - `list_domains()` - Show per-site domains
  - `check_ssl_status()` - Certificate verification

### 4. Backup System
- **Commands**: `cli/commands/backup.py`
- **Utils**: `cli/utils/backup.py`, `cli/utils/remote_backup.py`
- **Features**:
  - Local backups (tar + mysqldump)
  - S3-compatible remote backups (rclone)
  - Providers: AWS S3, Cloudflare R2, Backblaze B2
  - Automatic retention policies
  - Restore from local/remote

### 5. Security Audit System
- **Command**: `cli/commands/security.py`
- **Core Utils**:
  - `cli/utils/server_audit.py` - Orchestration engine
  - `cli/utils/system_auditor.py` - 9 system categories
  - `cli/utils/wordpress_auditor.py` - Site-level checks
  - `cli/utils/vulnerability_scanner.py` - WPScan API
  - `cli/utils/report_generator.py` - Multi-format reports
- **Features**:
  - System-level audit (SSH, firewall, fail2ban, updates, logs, filesystem)
  - WordPress-level audit (core, plugins, themes, users)
  - Vulnerability scanning via WPScan API
  - Optional Lynis integration
  - Reports: Console, JSON, HTML, PDF
  - Security score (0-100)
  - Severity classification (critical/high/medium/low)

### 6. SFTP Access Management
- **Command**: `cli/commands/sftp.py`
- **Utils**: `cli/utils/sftp.py`
- **Features**:
  - SSH key-based chroot jails
  - Restrict to wp-content only
  - Dynamic sshd_config management
  - ACL-based write permissions
  - No shell access (SFTP only)
  - User format: `sftp_sitename_identifier`

### 7. Malware Detection
- **Command**: `cli/commands/malware.py`
- **Functions**:
  - `scan_malware()` - Non-destructive detection
  - `cleanup_malware()` - Remove suspicious items
  - Flags: `--plugins`, `--files`, `--auto`, `--backup`

### 8. Self-Update System
- **Command**: `cli/commands/update.py`
- **Utils**: `cli/utils/update.py`, `cli/utils/github.py`, `cli/utils/version.py`
- **Features**:
  - GitHub API version checking
  - Install method detection (pip/script/editable)
  - Automatic backup before update
  - Rollback on failure
  - Config preservation
  - Semantic versioning

### 9. Configuration Management
- **Class**: `ConfigManager` (cli/utils/config.py)
- **File**: `~/.vibewp/sites.yaml`
- **Features**:
  - YAML load/save with atomic writes
  - Secure file permissions (0o600)
  - Schema validation
  - WPScan token support
  - Install method tracking

### 10. UI & Display
- **Console**: `cli/ui/console.py` - Rich formatting
- **Menu**: `cli/ui/menu.py` - Questionary interactive menus
- **Features**:
  - Colored output with Rich
  - Arrow-key navigation
  - Progress indicators
  - Beautiful error messages

## Code Metrics

### Top 5 Files by Size
1. `cli/commands/site.py` (6,427 tokens, 31,682 chars)
2. `cli/utils/system_auditor.py` (4,796 tokens, 22,847 chars)
3. `cli/utils/report_generator.py` (4,653 tokens, 19,813 chars)
4. `cli/utils/backup.py` (4,387 tokens, 20,234 chars)
5. `cli/utils/server_audit.py` (3,900+ tokens)

### Quality Metrics
- **Type Hints**: 100% coverage (Pydantic models)
- **Docstrings**: Google style (Args, Returns, Raises)
- **Test Coverage**: 100+ test methods
- **Linting**: Black formatting enforced
- **Security**: 0 critical issues (repomix verified)

## Installation Methods

### 1. pip (Recommended)
```bash
pip install vibewp
vibewp --version
```

### 2. Script (One-line)
```bash
curl -fsSL https://raw.githubusercontent.com/vibery-studio/vibewp/main/install.sh | sudo bash
```

### 3. Editable (Development)
```bash
pip install -e .
vibewp --version
```

All methods support self-update via:
```bash
vibewp update install [--pre] [--yes]
```

## Technology Stack

### Core
- **Python**: 3.10+
- **CLI Framework**: Typer 0.12+
- **Console Output**: Rich 13.7+
- **Interactive Menus**: Questionary 2.0+
- **Type Validation**: Pydantic 2.9+
- **Config Format**: PyYAML 6.0+

### Infrastructure
- **Containerization**: Docker + Docker Compose v2
- **WordPress Engines**: FrankenWP (FrankenPHP) or OpenLiteSpeed
- **Database**: MariaDB 11
- **Reverse Proxy**: Caddy v2 (auto-HTTPS)
- **Caching**: Redis (OpenLiteSpeed optional)
- **OS**: Ubuntu 22.04 or 24.04 LTS

### Libraries
- **SSH**: Paramiko 3.0+ (key-based auth)
- **Templating**: Jinja2 3.1+ (Docker Compose)
- **HTTP**: requests (WPScan API, GitHub API)
- **Backup**: rclone (S3-compatible uploads)
- **Security**: lynis (optional hardening audit)

## Configuration

### YAML Schema
```yaml
vps:
  host: "192.0.2.1"
  port: 22
  user: "root"
  key_path: "~/.ssh/id_rsa"
  install_method: "pip"
  wpscan_api_token: "optional"

sites:
  sitename:
    domain: "example.com"
    type: "frankenwp"  # or "ols"
    status: "running"  # or "stopped"
    created: "2025-12-25T10:00:00Z"
    domains:
      - "www.example.com"
```

### Storage
- **Config**: `~/.vibewp/sites.yaml` (0o600 permissions)
- **Logs**: `~/.vibewp/vibewp.log`
- **Backups**: `~/.vibewp/backups/sitename/`
- **Remote**: S3-compatible (rclone config)

## Development

### Project Setup
```bash
git clone https://github.com/vibery-studio/vibewp.git
cd wpserver
pip install -e .
pip install pytest pytest-cov
```

### Running Tests
```bash
pytest tests/
pytest tests/ --cov=cli
pytest tests/ -v
```

### Code Style
```bash
black cli/ tests/
isort cli/ tests/
flake8 cli/ tests/
```

### Pre-commit Hooks
```bash
pre-commit install
pre-commit run --all-files
```

## Entry Points

- **CLI Command**: `vibewp` (installed globally)
- **Version**: `vibewp --version`
- **Help**: `vibewp --help`
- **Menu**: `vibewp menu`

## Feature Completeness

### Commands (16+)
- ✅ Site: create, list, info, start, stop, restart, delete, fix-permissions, reinstall-core
- ✅ Domain: add, remove, set-primary, list, ssl-status
- ✅ Backup: create, restore, list, configure-remote, list-remote
- ✅ Security: scan, audit-server, set-wpscan-token, clear-wpscan-token, harden-vps, harden-wp
- ✅ Malware: scan, cleanup
- ✅ SFTP: add-key, remove-key, list, test, info
- ✅ Firewall: list, open, close
- ✅ SSH: change-port
- ✅ PHP: set-limits, show-limits
- ✅ Proxy: reload, status
- ✅ System: status, doctor
- ✅ Update: check, install, cleanup, info
- ✅ Config: init, show, path
- ✅ Menu: interactive

### Infrastructure
- ✅ Docker Compose orchestration
- ✅ FrankenWP stack (FrankenPHP + MariaDB)
- ✅ OpenLiteSpeed stack (OLS + Redis + MariaDB)
- ✅ Caddy reverse proxy (auto-HTTPS)
- ✅ Per-site network isolation

### Security
- ✅ SSH hardening (key-only, custom port)
- ✅ UFW firewall integration
- ✅ fail2ban protection
- ✅ Server security auditing
- ✅ WordPress auditing
- ✅ WPScan vulnerability scanning
- ✅ SFTP chroot jails
- ✅ Security scoring (0-100)
- ✅ Multi-format reports

### Backup & Recovery
- ✅ Local backups (tar + mysqldump)
- ✅ Remote S3 backups (rclone)
- ✅ Backup restore
- ✅ Retention policies

### Operations
- ✅ Site recovery (fix-permissions, reinstall-core)
- ✅ Malware scanning + cleanup
- ✅ System monitoring
- ✅ Self-update system

## Roadmap

### Completed ✅
- [x] Site CRUD operations
- [x] Multi-domain support
- [x] FrankenWP + OpenLiteSpeed stacks
- [x] Automatic HTTPS (Let's Encrypt)
- [x] Security auditing system
- [x] WPScan vulnerability integration
- [x] SFTP access management
- [x] Local + remote backups
- [x] Self-update system
- [x] Malware scanning + cleanup
- [x] Interactive CLI menus
- [x] System diagnostics (doctor)
- [x] PHP configuration
- [x] Firewall management
- [x] SSH port management

### In Progress 🚧
- [ ] VPS security hardening automation
- [ ] WordPress hardening automation
- [ ] Scheduled backup automation
- [ ] Monitoring dashboard

### Planned 📋
- [ ] Multi-VPS management
- [ ] Site cloning
- [ ] Email notifications
- [ ] CDN integration
- [ ] API server mode
- [ ] Web UI dashboard

## Documentation

- **README.md** - User quick start + commands
- **project-overview-pdr.md** - PDR + requirements
- **code-standards.md** - Code conventions
- **system-architecture.md** - Architecture overview
- **codebase-summary.md** - This file
- **security-audit-guide.md** - Security audit details
- **sftp-access-guide.md** - SFTP setup guide

## Testing

### Test Structure
```
tests/
├── unit/
│   ├── test_validators.py
│   ├── test_config.py
│   └── test_credentials.py
├── integration/
│   ├── test_site_creation.py
│   └── test_backup_restore.py
└── conftest.py
```

### Coverage
- Unit: 100+ test methods
- Integration: E2E workflows
- Mocked: Docker, SSH, external APIs

## Security Assessment

### Code Review
- ✅ 100% type hints (Pydantic)
- ✅ No shell injection vulnerabilities
- ✅ Secure password generation (secrets module)
- ✅ Atomic file operations (no partial writes)
- ✅ Proper permission handling (0o600, 0o700)
- ✅ No hardcoded secrets
- ✅ Repomix security check: No suspicious files

### Dependencies
- ✅ All pinned versions in setup.py
- ✅ No high-severity vulnerabilities
- ✅ Regular updates via dependabot

## Related Documentation

- **Project Overview**: `project-overview-pdr.md` (PDR, requirements, roadmap)
- **Code Standards**: `code-standards.md` (conventions, style, best practices)
- **System Architecture**: `system-architecture.md` (architecture diagram, data flows)
- **Security Guide**: `security-audit-guide.md` (audit system details)
- **SFTP Guide**: `sftp-access-guide.md` (chroot setup, user management)
