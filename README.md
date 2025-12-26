# VibeWP - VPS WordPress Manager

**Version**: 1.7.0 | CLI tool for managing WordPress sites on VPS with automatic HTTPS, Docker isolation, and security auditing.

## Quick Start

### Prerequisites
- Fresh Ubuntu VPS (22.04 or 24.04 LTS)
- Docker 20.10+ installed and running
- Root or sudo access
- Domain DNS pointed to VPS IP

### One-Line Install
```bash
curl -fsSL https://raw.githubusercontent.com/vibery-studio/vibewp/main/install.sh | sudo bash
```

### Create First Site
```bash
vibewp site create
```

Fully automated! Generates secure credentials, installs WordPress, sets up HTTPS.

## Core Features

- **One-command site creation** (<5 minutes with auto-HTTPS)
- **Multi-site management** (unlimited sites per VPS)
- **Three engines** (FrankenWP, WordPress Official, OpenLiteSpeed)
- **Automatic HTTPS** (Let's Encrypt via Caddy)
- **Security auditing** (system + WordPress + CVE scanning)
- **SFTP access** (chroot jails, wp-content only)
- **Backups** (local + S3-compatible remote)
- **Recovery tools** (fix permissions, reinstall core, malware cleanup)
- **Interactive UI** (beautiful CLI with arrow-key menus)

## Essential Commands

### Site Management
```bash
vibewp site create                    # Create WordPress site
vibewp site list                      # List all sites
vibewp site start|stop|restart <name> # Control sites
vibewp site delete <name>             # Remove site
vibewp site fix-permissions <name>    # Fix permission issues
vibewp site reinstall-core <name>     # Recover from hack
vibewp site migrate <name>            # Migrate to new FrankenPHP image
vibewp site migrate-all               # Batch migrate all FrankenWP sites
```

### Domain Management
```bash
vibewp domain add <site> <domain>     # Add domain
vibewp domain remove <site> <domain>  # Remove domain
vibewp domain list <site>             # List domains
vibewp domain ssl-status <site>       # Check SSL certs
```

### Security & Backups
```bash
vibewp security audit-server          # Full security audit
vibewp security scan                  # Quick scan
vibewp backup create <site>           # Local backup
vibewp backup create <site> --remote  # Local + S3 upload
vibewp backup restore <site> <backup> # Restore backup
```

### Additional Operations
```bash
vibewp sftp add-key <site> <pub-key>  # Grant SFTP access
vibewp malware scan|cleanup <site>    # Malware operations
vibewp firewall list|open|close <port># Firewall management
vibewp php set-limits <site>          # PHP configuration
vibewp system status|doctor           # System monitoring
vibewp update check|install           # Self-update
vibewp menu                            # Interactive menu
```

## Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 core | 2 cores |
| RAM | 1GB | 2GB+ |
| Disk | 10GB base | 20GB+ |
| Sites | 1-2 | 3-5 |

## Architecture

```
Internet (80/443)
    ↓
Caddy Reverse Proxy (auto-HTTPS)
    ├── FrankenWP Sites (shinsenter/frankenphp + MariaDB)
    ├── WordPress Sites (wordpress:latest + MariaDB)
    └── OpenLiteSpeed Sites (OLS + Redis + MariaDB)
```

Each site runs in isolated Docker network with separate database, filesystem, and network access.

## Configuration

Config auto-generated at `~/.vibewp/sites.yaml` during installation.

```bash
vibewp config show          # View current config
vibewp config edit          # Edit config file
```

Optional settings:
- `wpscan_api_token` - For vulnerability scanning (free at wpscan.com)

## Troubleshooting

### Command Not Found
```bash
which vibewp
curl -fsSL https://raw.githubusercontent.com/vibery-studio/vibewp/main/install.sh | sudo bash
```

### Site Won't Start
```bash
vibewp site logs <site-name>
docker ps -a | grep <site-name>
vibewp doctor check
```

### SSL Certificate Issues
```bash
vibewp domain ssl-status <site-name>
dig +short yourdomain.com  # Verify DNS points to VPS
```

## Security Features

- SSH key-only authentication (no passwords)
- Custom SSH port with safe change mechanism
- UFW firewall with fail2ban protection
- Automatic security updates
- 32-character database passwords
- Per-site network isolation
- SFTP chroot jails (wp-content access only)
- Server + WordPress security auditing
- WPScan vulnerability scanning (optional, free API)

## What Gets Installed

- **VibeWP CLI** (Python package with all dependencies)
- **Caddy reverse proxy** (Docker container)
- **Docker networks** (isolated per site)
- **Configuration files** (~/.vibewp/)

**Prerequisites** (must be pre-installed):
- Docker Engine 20.10+
- Python 3.10+

**Optional** (auto-installed when needed):
- rclone (for S3 backups)
- lynis (for hardening audit)

## Usage Examples

### Create FrankenWP Site
```bash
vibewp site create \
  --site-name myblog \
  --domain blog.example.com \
  --wp-type frankenwp \
  --admin-email admin@example.com
```

### Add Multi-Domain
```bash
vibewp domain add myblog www.blog.example.com
vibewp domain add myblog cdn.blog.example.com
```

### Setup SFTP Access
```bash
vibewp sftp add-key mysite ~/.ssh/id_rsa.pub --id john
# Client connects: sftp sftp_mysite_john@your-server.com
# Can only access wp-content (no shell access)
```

### Remote Backups to S3
```bash
# Interactive setup (AWS S3 / R2 / B2)
vibewp backup configure-remote

# Create backup and upload to S3
vibewp backup create mysite --remote

# List remote backups
vibewp backup list-remote --site mysite
```

### Full Security Audit
```bash
# Basic audit
vibewp security audit-server

# With WPScan API (requires token)
vibewp security set-wpscan-token YOUR_TOKEN
vibewp security audit-server

# Save HTML report
vibewp security audit-server --format html --output ~/audit.html
```

### Change SSH Port Safely
```bash
vibewp ssh change-port 2222
# Automatic rollback if connection fails
```

## Self-Update

VibeWP updates itself automatically:

```bash
vibewp update check              # Check for new version
vibewp update install [--yes]    # Install latest
vibewp update cleanup --keep 3   # Cleanup old backups
vibewp update info               # Show install details
vibewp --version                 # Show version
```

Automatic backup + rollback on failure.

## Interactive Menu

Launch full menu UI:
```bash
vibewp menu
```

Navigate with arrow keys, select with Enter. Complete management interface for all operations.

## Documentation

- **Full docs**: See `./docs/` directory
- **API reference**: `./docs/codebase-summary.md`
- **Architecture**: `./docs/system-architecture.md`
- **Code standards**: `./docs/code-standards.md`
- **Security audit guide**: `./docs/security-audit-guide.md`
- **SFTP guide**: `./docs/sftp-access-guide.md`

## Roadmap

### Completed ✅
- [x] Site CRUD operations
- [x] Multi-domain support
- [x] FrankenWP + OpenLiteSpeed
- [x] Automatic HTTPS
- [x] Security auditing
- [x] WPScan integration
- [x] SFTP management
- [x] Local + remote backups
- [x] Self-update system
- [x] Malware scanning
- [x] Interactive menus

### Planned 🚧
- [ ] VPS hardening automation
- [ ] Scheduled backups
- [ ] Multi-VPS management
- [ ] Site cloning
- [ ] Monitoring dashboard

## Contributing

Contributions welcome! Please:
1. Fork repository
2. Create feature branch
3. Test on Ubuntu 22.04 or 24.04
4. Submit pull request

## Support

- **Issues**: https://github.com/vibery-studio/vibewp/issues
- **Docs**: https://github.com/vibery-studio/vibewp/wiki
- **Discord**: Coming soon

## License

MIT License - See LICENSE file

---

**Built with ❤️ by Vibery Studio**
