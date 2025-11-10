# VibeWP - VPS WordPress Manager

Complete CLI tool for managing WordPress sites on VPS with automatic HTTPS, Docker isolation, and advanced operations.

## ✨ Features

- 🚀 **One-line installation** - Install on fresh Ubuntu VPS in 30 seconds
- 🎯 **< 5 minute deployments** - Create WordPress sites with automatic HTTPS
- 🔄 **Dual engine support** - Choose FrankenWP (speed) or OpenLiteSpeed (stability) per site
- 🔒 **Security-first** - SSH hardening, firewall, fail2ban, automated updates
- 🌐 **Multi-domain** - Add unlimited domains to any site
- 📦 **Complete operations** - Backups, monitoring, security scanning
- 🎨 **Interactive UI** - Beautiful CLI with arrow-key menus

## 🚀 Quick Start

### Prerequisites

1. **Fresh Ubuntu VPS** (22.04 or 24.04 LTS)
2. **Docker installed**:
   ```bash
   curl -fsSL https://get.docker.com | sh
   systemctl start docker && systemctl enable docker
   ```
3. **Domain DNS** pointed to your VPS IP

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/vibery-studio/vibewp/main/install.sh | sudo bash
```

**What this does automatically:**
- ✅ Installs VibeWP CLI
- ✅ Generates SSH keys for localhost access
- ✅ Creates Docker proxy network
- ✅ Deploys Caddy reverse proxy
- ✅ Initializes configuration

### Create Your First Site

```bash
vibewp site create
```

**No additional configuration needed!** Just follow the interactive prompts.

## 📋 Requirements

- **OS**: Ubuntu 22.04 or 24.04 LTS
- **RAM**: 2GB minimum
- **CPU**: 2 cores recommended
- **Docker**: 20.10+ with Docker Compose v2
- **Access**: Root or sudo user
- **Domain**: DNS pointed to your VPS IP

## 🎯 Commands

### Site Management
```bash
vibewp site create              # Create new WordPress site
vibewp site list                # List all sites
vibewp site info <name>         # Site details
vibewp site delete <name>       # Remove site
vibewp site logs <name>         # View logs
```

### Domain Management
```bash
vibewp domain add <site> <domain>       # Add domain
vibewp domain remove <site> <domain>    # Remove domain
vibewp domain set-primary <site>        # Change primary
vibewp domain ssl-status <site>         # SSL certificates
```

### VPS Operations
```bash
vibewp firewall list|open|close         # Firewall control
vibewp ssh change-port <port>           # SSH configuration
vibewp security scan                    # Security audit
vibewp system status                    # Resource usage
vibewp backup create <site>             # Backup site
```

### Interactive Menu
```bash
vibewp menu     # Launch full interactive UI
```

## 🏗️ Architecture

```
Caddy Reverse Proxy (Auto HTTPS)
    ├── FrankenWP Sites (FrankenPHP + MariaDB)
    └── OpenLiteSpeed Sites (OLS + MariaDB + Redis)
```

**Network Isolation**: Each site runs in isolated Docker network, connected via Caddy proxy.

## 🔒 Security Features

- ✅ SSH key-only authentication
- ✅ Custom SSH port with safe change mechanism
- ✅ UFW firewall with fail2ban
- ✅ Automatic security updates
- ✅ 32-character database passwords
- ✅ Network isolation per site
- ✅ Automatic HTTPS (Let's Encrypt)

## 📦 What Gets Installed

- **Python 3.10+** with virtual environment
- **Docker Engine** + Docker Compose v2
- **Caddy** reverse proxy
- **UFW** firewall (optional, via VPS setup)
- **fail2ban** (optional, via VPS setup)

## 🎓 Usage Examples

### Create FrankenWP Site
```bash
vibewp site create \
  --site-name myblog \
  --domain blog.example.com \
  --wp-type frankenwp \
  --admin-email admin@example.com
```

### Create OpenLiteSpeed Site
```bash
vibewp site create \
  --site-name mystore \
  --domain store.example.com \
  --wp-type ols \
  --admin-email admin@example.com
```

### Add Additional Domain
```bash
vibewp domain add myblog www.blog.example.com
```

### Change SSH Port Safely
```bash
vibewp ssh change-port 2222
# Automatic rollback if connection fails
```

## 🔧 Configuration

Config stored in `~/.vibewp/sites.yaml`:

```yaml
vps:
  host: "YOUR_VPS_IP"
  port: 22
  user: "root"
  key_path: "~/.ssh/id_rsa"

sites:
  myblog:
    domain: "blog.example.com"
    type: "frankenwp"
    status: "running"
    created: "2025-11-10T16:00:00Z"
```

## 🐛 Troubleshooting

### Command Not Found
```bash
# Verify installation
which vibewp

# If not found, re-run installer
curl -fsSL https://raw.githubusercontent.com/vibery-studio/vibewp/main/install.sh | sudo bash
```

### Site Won't Start
```bash
# Check container logs
vibewp site logs <site-name>

# Check Docker status
docker ps -a
```

### SSL Certificate Issues
```bash
# Check certificate status
vibewp domain ssl-status <site-name>

# Verify DNS points to VPS
dig +short yourdomain.com
```

## 📊 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 core | 2 cores |
| RAM | 1GB | 2GB+ |
| Disk | 10GB | 20GB+ |
| Sites | 1-2 | 3-5 |

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create feature branch
3. Test on Ubuntu 22.04 or 24.04
4. Submit pull request

## 📄 License

MIT License - See LICENSE file

## 🆘 Support

- **Issues**: https://github.com/vibery-studio/vibewp/issues
- **Docs**: https://github.com/vibery-studio/vibewp/wiki
- **Discord**: Coming soon

## 🎯 Roadmap

- [ ] Multi-VPS management
- [ ] Site cloning
- [ ] Automated backups to S3/R2
- [ ] Monitoring dashboard
- [ ] Email notifications
- [ ] CDN integration

## ⭐ Star History

If VibeWP helps you, please star the repo!

---

**Built with ❤️ by Vibery Studio**
