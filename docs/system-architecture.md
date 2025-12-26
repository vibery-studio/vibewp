# VibeWP - System Architecture

**Version**: 1.6.2 | **Last Updated**: 2025-12-25

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Local Machine / VPS                        │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           Internet (HTTPS via Let's Encrypt)             │  │
│  └────────────────────────────┬─────────────────────────────┘  │
│                               │                                 │
│  ┌────────────────────────────▼─────────────────────────────┐  │
│  │    Caddy Reverse Proxy (Port 80/443)                    │  │
│  │  - Auto HTTPS (Let's Encrypt)                           │  │
│  │  - HTTP/2, HTTP/3 support                               │  │
│  │  - Domain routing to isolated networks                  │  │
│  │  - Container: caddy:latest (Docker network: caddy)      │  │
│  └─────┬──────┬──────┬────────────────────────────────────┘  │
│        │      │      │                                         │
│  ┌─────▼─┐ ┌──▼──┐ ┌─▼────┐                                  │
│  │ Site1 │ │Site2│ │Site3 │  (More sites...)               │
│  └─────┬─┘ └──┬──┘ └─┬────┘                                  │
│        │      │      │                                         │
│  ┌─────▼──────▼──────▼────────────────────────────────────┐  │
│  │      Docker Networks (per-site isolation)              │  │
│  │                                                        │  │
│  │  vibewp_site1          vibewp_site2   vibewp_site3   │  │
│  │  ┌──────────────┐      ┌──────────┐   ┌──────────┐   │  │
│  │  │ FrankenWP    │      │OpenLS    │   │FrankenWP │   │  │
│  │  │+MariaDB 11   │      │+Redis    │   │+MariaDB  │   │  │
│  │  │Container:    │      │+MariaDB  │   │Container:│   │  │
│  │  │frankenwp:    │      │11        │   │frankenwp:│   │  │
│  │  │latest        │      │OpenLS:   │   │latest    │   │  │
│  │  │+            │      │latest    │   │+         │   │  │
│  │  │db_site1      │      │mariadb:  │   │db_site3  │   │  │
│  │  │MariaDB11     │      │11        │   │MariaDB11 │   │  │
│  │  │              │      │+         │   │          │   │  │
│  │  │Volumes:      │      │redis:    │   │Volumes:  │   │  │
│  │  │-wp_content   │      │latest    │   │-wp_content  │  │
│  │  │-db_data      │      │+         │   │-db_data  │   │  │
│  │  │-certs        │      │redis_data│   │-certs    │   │  │
│  │  │              │      │+         │   │          │   │  │
│  │  │Ports:        │      │db_data   │   │Ports:    │   │  │
│  │  │8080 (WP)     │      │          │   │8080 (WP) │   │  │
│  │  │3306 (MySQL)  │      │Ports:    │   │3306 (DB) │   │  │
│  │  │              │      │8080/9000 │   │          │   │  │
│  │  │              │      │3306 (DB) │   │          │   │  │
│  │  └──────────────┘      │6379 (R)  │   └──────────┘   │  │
│  │                        └──────────┘                   │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐  │
│  │           Host System Configuration                   │  │
│  │  - UFW Firewall (ports 22, 80, 443)                   │  │
│  │  - fail2ban (SSH brute-force, jails)                  │  │
│  │  - Docker daemon                                      │  │
│  │  - SSH server (hardened)                              │  │
│  │  - Config: ~/.vibewp/sites.yaml                       │  │
│  │  - Logs: ~/.vibewp/vibewp.log                         │  │
│  │  - Backups: ~/.vibewp/backups/ (local)                │  │
│  │  - Backups: S3-compatible (rclone)                    │  │
│  │  - SFTP: chroot jails in /opt/vibewp/sftp/           │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      External Services                          │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Let's Encrypt    │  │ GitHub API   │  │ WPScan API       │ │
│  │ (HTTPS Certs)    │  │ (Update Chk) │  │ (CVE Scanning)   │ │
│  │ caddy-managed    │  │ Auto-update  │  │ Optional, free   │ │
│  └──────────────────┘  └──────────────┘  └──────────────────┘ │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ S3-Compatible Storage (Optional)                         │ │
│  │ - AWS S3 / Cloudflare R2 / Backblaze B2                │ │
│  │ - Remote backup uploads via rclone                     │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Layered Architecture

### Layer 1: CLI Interface
```
typer.Typer(help="...")
├── Commands (16 modules)
│   ├── site.create / list / info / start / stop / restart / delete
│   ├── domain.add / remove / list / set-primary / ssl-status
│   ├── backup.create / restore / list / configure-remote
│   ├── security.scan / audit-server / harden-vps / harden-wp
│   ├── sftp.add-key / remove-key / list / test / info
│   ├── malware.scan / cleanup
│   ├── firewall.list / open / close
│   ├── ssh.change-port
│   ├── php.set-limits / show-limits
│   ├── proxy.reload / status
│   ├── system.status / doctor
│   ├── update.check / install / cleanup
│   ├── config.init / show / path
│   └── menu (interactive)
└── Handlers
    └── Typer routing → Command functions
```

### Layer 2: Command Processing
```
Commands (site.py, domain.py, ...)
├── Input validation
├── Config loading
├── Error handling + recovery
└── Output formatting (Rich console, Questionary menus)
```

### Layer 3: Business Logic
```
Utils (30+ modules)
├── Configuration
│   ├── config.py (YAML load/save)
│   ├── credentials.py (secure password generation)
│   └── validators.py (domain, email, IP, port)
├── Infrastructure
│   ├── docker.py (container management)
│   ├── caddy.py (reverse proxy config)
│   ├── ssh.py (SSH connections)
│   └── database.py (MariaDB operations)
├── Security
│   ├── server_audit.py (orchestration)
│   ├── system_auditor.py (SSH, firewall, updates, etc.)
│   ├── wordpress_auditor.py (core, plugins, themes, users)
│   ├── vulnerability_scanner.py (WPScan API)
│   ├── report_generator.py (multi-format reports)
│   ├── security.py (hardening utilities)
│   └── lynis_integration.py (optional hardening audit)
├── WordPress
│   ├── wordpress.py (WP-CLI wrapper)
│   ├── permissions.py (file permission fixes)
│   └── malware.py (scanning + cleanup)
├── Backup
│   ├── backup.py (local backups)
│   ├── remote_backup.py (S3 uploads)
│   └── health.py (backup validation)
├── SFTP
│   └── sftp.py (chroot jails + sshd_config)
├── Update System
│   ├── update.py (GitHub API, install detection)
│   ├── version.py (semantic versioning)
│   └── github.py (GitHub client)
├── Networking
│   ├── dns.py (DNS validation)
│   ├── firewall.py (UFW wrapper)
│   └── health.py (container health checks)
└── Templates
    ├── template.py (Jinja2 rendering)
    └── /templates/ (Docker Compose, config files)
```

### Layer 4: Infrastructure
```
Docker Compose (per-site)
├── WordPress container (FrankenPHP or OpenLiteSpeed)
├── Database container (MariaDB 11)
├── Optional: Redis (OpenLiteSpeed only)
├── Shared: Caddy reverse proxy
└── Volumes
    ├── wp_content (persistent)
    ├── db_data (persistent)
    ├── certs (Caddy, persistent)
    └── redis_data (OpenLiteSpeed, persistent)
```

## Data Flow

### Site Creation Flow
```
vibewp site create
├── Input (typer.Option)
│   ├── site_name: str
│   ├── domain: str
│   ├── wp_type: "frankenwp" | "ols"
│   └── admin_email: str
├── Validation
│   ├── validate_domain() → DNS resolution
│   ├── validate_email()
│   └── check_site_exists() → ConfigManager
├── Configuration
│   ├── Generate credentials
│   │   ├── DB password (32 chars)
│   │   ├── WP admin password
│   │   └── Store in ~/.vibewp/sites.yaml
│   └── Load templates (Jinja2)
│       ├── docker-compose.yml
│       ├── caddy/site.conf
│       └── wp-config.php
├── Infrastructure
│   ├── Docker network creation (vibewp_sitename)
│   ├── MariaDB container deployment
│   ├── WordPress container deployment
│   └── Caddy config reload
├── WordPress Setup
│   ├── WP-CLI core download
│   ├── Database tables create
│   ├── WP user setup
│   └── Plugin/theme defaults
├── Verification
│   ├── Container health checks
│   └── HTTP endpoint test
└── Output
    └── Display credentials + next steps
```

### Backup Flow
```
vibewp backup create mysite [--remote]
├── Pre-flight
│   ├── Check site exists
│   ├── Verify container running
│   └── Check disk space
├── Local Backup
│   ├── mysqldump (to file)
│   ├── tar wp-content (to file)
│   └── Store: ~/.vibewp/backups/mysite/YYYY-MM-DD-HHMMSS/
├── Remote Upload (if --remote)
│   ├── Initialize rclone (if first time)
│   ├── Upload to S3-compatible storage
│   │   ├── AWS S3 / R2 / B2
│   │   └── Retention policy check
│   └── Cleanup old remote backups
└── Output
    └── Backup path + size + verification
```

### Security Audit Flow
```
vibewp security audit-server [--format json|html|pdf]
├── System Audit (SystemAuditor)
│   ├── SSH configuration check
│   ├── UFW firewall rules
│   ├── fail2ban jails
│   ├── Open ports enumeration
│   ├── System services status
│   ├── User accounts audit
│   ├── System updates check
│   ├── Log file review
│   └── Filesystem permissions
├── WordPress Audit (per-site)
│   ├── WordPress core version
│   ├── Plugin audit (active + inactive)
│   ├── Theme audit
│   ├── User accounts (roles)
│   ├── wp-config.php checks
│   └── File permissions
├── Vulnerability Scanning (optional)
│   ├── WPScan API integration
│   ├── CVE database matching
│   └── Severity classification
├── Report Generation
│   ├── Findings aggregation
│   ├── Security score calculation (0-100)
│   ├── Severity classification (critical/high/medium/low)
│   ├── Remediation suggestions
│   └── Format output (console/JSON/HTML/PDF)
└── Optional Lynis
    └── Additional hardening recommendations
```

## Component Interactions

### Configuration Management
```
ConfigManager (singleton pattern)
├── Load ~/.vibewp/sites.yaml
├── Validate schema
├── Cache in memory
├── Atomic writes (temp file → move)
├── File permissions (0o600)
└── Export to dict for utilities
```

### Docker Management
```
DockerManager
├── Initialize docker.client
├── Create/delete networks (per-site)
├── Deploy containers (via docker-compose)
├── Health checks (container status)
├── Log retrieval
└── Volume management
```

### SSH Access
```
SSHManager (Paramiko)
├── SSH key authentication
├── Command execution (no shell)
├── File transfer (sftp.SFTPClient)
├── Retry logic
└── Connection cleanup
```

### WordPress Operations
```
WordPressManager (WP-CLI wrapper)
├── Core installation
├── Plugin management
├── Theme management
├── User management
├── Option updates
└── Database operations
```

## State Management

### Configuration State
```yaml
~/.vibewp/sites.yaml (single source of truth)

vps:
  host, port, user, key_path, install_method, wpscan_api_token

sites:
  sitename:
    domain: primary_domain
    type: frankenwp | ols
    status: running | stopped
    created: ISO_timestamp
    domains: [list of additional domains]
```

### Runtime State
```
In-memory (discarded after command)
├── Loaded config dict
├── Docker client reference
├── SSH client reference
└── Temporary data structures
```

### Persistent Storage
```
~/.vibewp/
├── sites.yaml (config)
├── vibewp.log (logs)
├── backups/
│   └── sitename/
│       └── YYYY-MM-DD-HHMMSS/
│           ├── database.sql.gz
│           ├── wp-content.tar.gz
│           └── manifest.json
└── update_cache/ (auto-updates, rollback backups)
```

## Deployment Models

### Deployment Sequence (First Run)
```
1. Install VibeWP (pip/script)
2. vibewp config init
   └── Create ~/.vibewp/
   └── Create docker network (caddy)
   └── Deploy Caddy container
3. vibewp site create (repeat for each site)
   └── Create per-site network
   └── Deploy containers
   └── Initialize WordPress
4. vibewp domain add (optional, multi-domain)
5. vibewp sftp add-key (optional, SFTP access)
6. vibewp security audit-server (baseline)
7. vibewp backup configure-remote (optional)
8. vibewp backup create --remote (automated backups)
```

### Multi-Site Architecture
```
Single VPS
├── Caddy (1 container, shared)
│   └── Listens 0.0.0.0:80/443
│   └── Routes to each site network
└── Sites (N networks, N×2-3 containers)
    ├── vibewp_site1 (network)
    │   ├── frankenwp_site1
    │   └── db_site1
    ├── vibewp_site2 (network)
    │   ├── ols_site2
    │   ├── redis_site2
    │   └── db_site2
    └── vibewp_site3 (network)
        └── ...
```

## Security Boundaries

### Network Isolation
```
Each site:
- Separate Docker network (vibewp_sitename)
- No cross-network communication by default
- Cannot access other sites' databases
- Cannot access other sites' file system
```

### File System Isolation
```
SFTP Chroot:
- Users chroot jailed to /opt/vibewp/sftp/username/
- Symlink/bind mount to wp-content only
- No access to wp-admin, wp-includes, config
- No access to other sites
```

### SSH Access Control
```
- Key-based authentication only
- Custom SSH port (via safe-change)
- fail2ban protection (rate limiting)
- No password login
```

### Database Isolation
```
- Per-site database user (site-specific credentials)
- Separate database per site
- No access to other databases
```

## Disaster Recovery

### Backup Strategy
```
Local backups (default):
└── ~/.vibewp/backups/sitename/YYYY-MM-DD-HHMMSS/
    ├── database.sql.gz
    └── wp-content.tar.gz

Remote backups (optional):
└── S3-compatible storage (encrypted optional)
    └── Automatic retention policy
```

### Recovery Options
```
1. Restore from local backup
   vibewp backup restore sitename 2025-12-25-100000

2. Restore from remote backup
   vibewp backup restore-remote sitename 2025-12-25

3. Recovery commands
   vibewp site fix-permissions (fix ownership)
   vibewp site reinstall-core (after hack)
```

### Update Rollback
```
Pre-update backup:
└── ~/.vibewp/update_cache/backup-VERSION/
    └── (VibeWP code, config snapshot)

Rollback:
vibewp update rollback
```

## Scaling Considerations

### Per-VPS Limits
```
Recommended limits (2GB RAM, 2-core CPU):
├── 1-2 sites: Full features
├── 3-5 sites: Performance OK
├── 6-10 sites: Consider 4GB RAM + 4-core CPU
└── 10+ sites: Dedicated database server (separate VPS)
```

### Multi-VPS Management
```
Future feature (planned):
- Central management CLI
- Connect to multiple VPS instances
- Cross-VPS backups
- Distributed security audits
```

## Technology Stack

### Core
```
Python 3.10+
├── Typer 0.12+ (CLI framework)
├── Rich 13.7+ (console formatting)
├── Questionary 2.0+ (interactive menus)
├── Pydantic 2.9+ (type validation)
└── PyYAML 6.0+ (config storage)
```

### Infrastructure
```
Docker + Docker Compose v2
├── FrankenPHP (WordPress engine)
├── OpenLiteSpeed (alternative engine)
├── MariaDB 11 (database)
├── Redis (caching, OLS only)
├── Caddy v2 (reverse proxy)
└── Ubuntu 22.04/24.04 LTS
```

### Security & Operations
```
Paramiko 3.0+ (SSH client)
Jinja2 3.1+ (templates)
requests (HTTP API calls)
rclone (S3 backup upload)
lynis (optional hardening audit)
```

## Performance Considerations

### Docker Optimization
```
├── Layer caching for images
├── Volume mount optimization
├── Network driver selection (bridge)
└── Resource limits per container
```

### PHP Optimization
```
FrankenWP:
├── FrankenPHP worker mode (keep in memory)
├── Early HTTP 103 hints
└── Native Go PHP SAPI

OpenLiteSpeed:
├── LSCache plugin (page caching)
├── Redis object cache
└── JIT compiler (PHP 8.3)
```

### Database Optimization
```
MariaDB 11:
├── InnoDB buffer pool
├── Query caching (selective)
├── Index optimization
└── Backup compression (gzip)
```

## Monitoring & Observability

### Logging
```
~/.vibewp/vibewp.log
├── Command execution (DEBUG)
├── Operations (INFO)
├── Warnings (WARNING)
└── Errors (ERROR)

Docker logs:
vibewp site logs sitename
```

### Health Checks
```
Container health:
├── Docker ps health status
├── HTTP endpoint tests
└── Database connectivity

System health:
vibewp doctor check
├── Docker daemon status
├── Disk space
├── Network connectivity
└── Configuration validation
```

## Related Documentation

- **Project Overview**: `project-overview-pdr.md`
- **Code Standards**: `code-standards.md`
- **Codebase Summary**: `codebase-summary.md`
