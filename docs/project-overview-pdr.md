# VibeWP - Project Overview & PDR

**Version**: 1.6.2 | **Last Updated**: 2025-12-25

## Project Vision

VibeWP is a production-ready CLI tool for managing multiple WordPress sites on a single VPS with zero friction. Automates HTTPS, Docker isolation, security hardening, and advanced operations via elegant interactive menus.

## Core Mission

Enable developers/agencies to:
- Deploy WordPress in <5 minutes with automatic HTTPS
- Manage multi-site infrastructure from CLI
- Enforce security best practices without manual configuration
- Monitor, audit, and secure WordPress at scale

## Functional Requirements

### 1. Site Management
- Create WordPress site (FrankenWP or OpenLiteSpeed)
- List/info/start/stop/restart/delete sites
- Fix permissions + reinstall core (recovery)
- Auto-generates secure credentials (32-char DB passwords)
- Non-interactive flags for automation

### 2. Domain Management
- Add/remove unlimited domains per site
- Set primary domain
- List domains with SSL status
- Automatic HTTPS via Let's Encrypt
- DNS validation integration

### 3. Container Orchestration
- Docker Compose v2 for site isolation
- FrankenWP stack: FrankenPHP + MariaDB 11
- OpenLiteSpeed stack: OLS + Redis + MariaDB 11
- Caddy reverse proxy for auto-HTTPS + HTTP/2/3
- Per-site Docker networks

### 4. Security
- SSH hardening (key-only auth, custom port)
- UFW firewall with port management
- fail2ban integration
- Server security audit (system + WordPress)
- WPScan API integration for CVE scanning
- Lynis optional hardening audit
- Security score calculation (0-100)
- Multi-format reports (console/JSON/HTML/PDF)

### 5. SFTP Access Management
- SSH key-based chroot jails
- Site-specific restrictions (wp-content only)
- ACL-based write permissions
- No shell access (SFTP only)
- Dynamic sshd_config management

### 6. Backup & Recovery
- Local backups (full site + database)
- Remote S3-compatible backups (rclone)
- Providers: AWS S3, Cloudflare R2, Backblaze B2
- Backup/restore operations
- Retention policies

### 7. Malware Detection
- Malware scanning (non-destructive)
- Suspicious file detection
- Plugin/theme vulnerability checks
- Auto-cleanup with plugin/file removal
- Backup before cleanup

### 8. System Operations
- Resource monitoring (CPU/RAM/Disk)
- System diagnostics (doctor command)
- PHP limit configuration
- Proxy reload/status
- SSH port safe change with rollback

### 9. Self-Update System
- Version checking via GitHub API
- 3 installation methods: pip/script/editable
- Automatic backup before update
- Rollback on failure
- Config preservation

### 10. Interactive CLI
- Typer framework with Rich formatting
- Questionary menus with arrow keys
- Beautiful console output
- Progress indicators
- Full menu navigation

## Non-Functional Requirements

### Performance
- <5 min site deployment target
- <1s CLI response for read operations
- Parallel backup uploads to S3
- Docker layer caching optimization

### Reliability
- Atomic file operations (no partial writes)
- Automatic rollback on failures
- SSH connection retry logic
- Error messages with actionable remedies

### Security
- Secrets in config only (never CLI args)
- Secure password generation (secrets module)
- YAML config with 0o600 permissions
- No sensitive data in logs
- Paramiko for SSH (no shell execution)
- Jinja2 template injection safe

### Maintainability
- 100% type hints (Pydantic models)
- Clear separation: commands/utils/core
- Comprehensive docstrings
- Test coverage for critical paths
- YAML config over environment variables

### Usability
- One-line installation
- Interactive prompts for defaults
- Clear error messages
- Help text for all commands
- Documented examples

## Technical Constraints

### System Requirements
- **OS**: Ubuntu 22.04 or 24.04 LTS
- **RAM**: 2GB minimum (1 site), 4GB+ for 3+ sites
- **CPU**: 2 cores minimum
- **Disk**: 10GB base + per-site allocation
- **Docker**: 20.10+, Docker Compose v2
- **Python**: 3.10+

### Dependencies
- **CLI**: Typer 0.12+, Rich 13.7+, Questionary 2.0+
- **Config**: Pydantic 2.9+, PyYAML 6.0+
- **Templating**: Jinja2 3.1+
- **SSH**: Paramiko 3.0+
- **Docker**: Docker SDK, docker-compose CLI
- **Backup**: rclone (auto-installed)
- **Security**: requests (WPScan API), lynis (optional)

### External Services
- GitHub API (update checking)
- WPScan API (optional, free tier 25 req/day)
- Let's Encrypt (Caddy handles)
- S3-compatible storage (backups)

## Acceptance Criteria

### Core Features
- ✅ Create multi-site setup in <5 minutes
- ✅ Automatic HTTPS via Let's Encrypt
- ✅ Site isolation (Docker + network)
- ✅ CLI automation (non-interactive mode)
- ✅ Security audit with severity levels

### Commands
- ✅ 16+ commands fully functional
- ✅ Non-interactive flags for all operations
- ✅ Interactive menus for complex workflows
- ✅ Clear --help for every command

### Configuration
- ✅ YAML config storage at ~/.vibewp/sites.yaml
- ✅ Secure credential generation
- ✅ WPScan token optional support
- ✅ Install method auto-detection

### Error Handling
- ✅ Connection failures with retry
- ✅ Permission errors with clear remedies
- ✅ Docker container failures logged
- ✅ Graceful degradation

### Testing
- ✅ 100+ test methods across CLI
- ✅ Unit tests for utilities
- ✅ Integration tests for commands
- ✅ E2E tests for update workflow

## Architecture Overview

```
VibeWP CLI
├── commands/          (16 command modules)
│   ├── site.py        Site CRUD + recovery
│   ├── domain.py      Multi-domain management
│   ├── backup.py      Local + remote backups
│   ├── security.py    Audits + hardening
│   ├── sftp.py        Chroot access management
│   ├── malware.py     Malware detection
│   ├── firewall.py    UFW + port management
│   ├── ssh_cmd.py     SSH port management
│   ├── php.py         PHP limit configuration
│   ├── proxy.py       Caddy reload
│   ├── system.py      Monitoring + doctor
│   ├── update.py      Self-update system
│   ├── config.py      Configuration
│   ├── doctor.py      System diagnostics
│   └── menu.py        Interactive UI
├── utils/             (30+ utility modules)
│   ├── docker.py      Container orchestration
│   ├── caddy.py       Reverse proxy config
│   ├── wordpress.py   WP-CLI integration
│   ├── database.py    MariaDB management
│   ├── ssh.py         SSH connections
│   ├── server_audit.py         Orchestration
│   ├── system_auditor.py       System checks
│   ├── wordpress_auditor.py    WordPress checks
│   ├── vulnerability_scanner.py WPScan API
│   ├── report_generator.py     Multi-format reports
│   ├── backup.py      Local backup logic
│   ├── remote_backup.py        S3 backup logic
│   ├── sftp.py        Chroot jail setup
│   ├── firewall.py    UFW wrapper
│   ├── security.py    Security utilities
│   ├── config.py      YAML config manager
│   ├── credentials.py Secure password gen
│   ├── validators.py  Domain/email/IP/port
│   ├── dns.py         DNS validation
│   ├── health.py      Container health checks
│   ├── permissions.py File permission fixes
│   ├── template.py    Jinja2 rendering
│   ├── version.py     SemVer handling
│   ├── update.py      Update logic
│   ├── github.py      GitHub API client
│   └── lynis_integration.py   Lynis wrapper
└── ui/                (3 UI modules)
    ├── console.py     Rich formatting
    ├── menu.py        Questionary menus
    └── __init__.py
```

## Configuration Schema

File: `~/.vibewp/sites.yaml`

```yaml
vps:
  host: "192.0.2.1"              # VPS IP address
  port: 22                        # SSH port
  user: "root"                    # SSH user
  key_path: "~/.ssh/id_rsa"      # SSH private key
  install_method: "pip"           # pip|script|editable
  wpscan_api_token: "TOKEN"       # Optional, for CVE scanning

sites:
  sitename:
    domain: "example.com"         # Primary domain
    type: "frankenwp"             # frankenwp|ols
    status: "running"             # running|stopped
    created: "2025-12-25T10:00Z"  # ISO timestamp
    domains:                       # Additional domains
      - "www.example.com"
```

## Installation Methods

1. **pip** (recommended)
   - `pip install vibewp`
   - Self-update via pip
   - One-line installer wrapper

2. **script**
   - `curl ... | sudo bash`
   - Downloads from GitHub releases
   - Self-update via script replacement

3. **editable** (dev)
   - `pip install -e .`
   - Local development mode
   - Git-based updates

All methods support automatic self-update via `vibewp update install`.

## Success Metrics

### User Satisfaction
- < 5 min setup time for first site
- < 2 min for additional sites
- < 30 sec for domain additions
- Clear error messages (< 2 min to resolution)

### System Reliability
- 99.5% site uptime (Docker healthy)
- 100% backup success rate
- < 5 sec for CLI command execution
- Zero data loss during updates

### Security Posture
- 90+ security score baseline
- Zero critical findings
- All SSL certs auto-renewed
- Audit reports generated weekly

### Operational Metrics
- 16+ commands fully tested
- 100+ test methods passing
- <2% error rate in production
- <5% code review rejection rate

## Dependencies Graph

```
Python 3.10+
├── Typer 0.12+          (CLI framework)
├── Rich 13.7+           (Console output)
├── Questionary 2.0+     (Interactive menus)
├── Pydantic 2.9+        (Data validation)
├── PyYAML 6.0+          (Config storage)
├── Jinja2 3.1+          (Template rendering)
├── Paramiko 3.0+        (SSH client)
├── requests             (HTTP API calls)
├── Docker SDK           (Container mgmt)
└── docker-compose CLI   (Orchestration)

Optional:
├── rclone               (S3 backups, auto-installed)
└── lynis                (Hardening audit)
```

## Risk Mitigation

### Deployment Failures
- **Risk**: Docker Compose fails during site creation
- **Mitigation**: Pre-flight checks, rollback on error, detailed logs

### SSH Access Loss
- **Risk**: SSH port change breaks connection
- **Mitigation**: Safe change with automatic rollback on connection fail

### Data Loss
- **Risk**: Accidental site deletion
- **Mitigation**: Backup before delete, confirmation prompts, recovery commands

### Security Vulnerabilities
- **Risk**: Unpatched WordPress/plugins
- **Mitigation**: WPScan integration, audit reports, clear remediation

### Update Failures
- **Risk**: Self-update breaks VibeWP
- **Mitigation**: Automatic backup, rollback mechanism, config preservation

## Roadmap

### Completed ✅
- [x] Site CRUD operations
- [x] Multi-domain support
- [x] FrankenWP + OpenLiteSpeed stacks
- [x] Security auditing system
- [x] WPScan vulnerability integration
- [x] SFTP chroot access
- [x] Local + remote backups
- [x] Self-update system
- [x] Malware scanning
- [x] Interactive menus

### In Progress 🚧
- [ ] VPS security hardening automation
- [ ] WordPress hardening automation
- [ ] Multi-VPS management
- [ ] Site cloning
- [ ] Scheduled backup automation
- [ ] Monitoring dashboard
- [ ] Email notifications

### Planned 📋
- [ ] CDN integration
- [ ] API server mode
- [ ] Web UI dashboard
- [ ] Terraform modules
- [ ] Ansible playbooks

## Document Ownership

- **Project Lead**: Vibery Studio
- **Last Updated**: 2025-12-25
- **Review Cycle**: Quarterly
- **Related Docs**: README.md, code-standards.md, system-architecture.md
