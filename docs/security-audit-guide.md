# Security Audit Guide

**Version**: 1.0.0 | **Last Updated**: 2025-11-10

## Overview

VibeWP provides comprehensive server security auditing covering:
- System-level security (SSH, firewall, fail2ban, ports, services)
- WordPress installations (core, plugins, themes, file permissions)
- Vulnerability scanning via WPScan API
- Lynis system hardening audit (optional)

## Command Usage

### Basic Audit
```bash
# Console output with security score
vibewp security audit-server
```

### Export Reports
```bash
# HTML report
vibewp security audit-server --format html --output ~/audit-report.html

# JSON report (machine-readable)
vibewp security audit-server --format json --output ~/audit.json

# PDF report (requires HTML conversion)
vibewp security audit-server --format pdf --output ~/audit.pdf
```

### Advanced Options
```bash
# Skip WordPress audits
vibewp security audit-server --skip-wordpress

# Skip Lynis integration
vibewp security audit-server --skip-lynis

# Verbose output with progress
vibewp security audit-server --verbose

# Override config with inline token
vibewp security audit-server --wp-api-token YOUR_TOKEN
```

## Understanding Findings

### Severity Levels

**Critical** - Immediate action required
- SSH Protocol 1 enabled
- Firewall disabled
- Public-facing databases (MySQL, Redis, etc.)

**High** - Action required within 24-48h
- Root login enabled
- Password authentication enabled
- Security updates available
- Outdated WordPress core

**Medium** - Action required within 1 week
- Default SSH port (22)
- Missing fail2ban
- Many pending updates
- File permission issues

**Low** - Consider fixing
- Informational findings
- Best practice recommendations

### Finding Categories

#### System Security
- **SSH**: Configuration, authentication methods, protocol
- **Firewall**: UFW status, rules, default policies
- **fail2ban**: Status, jails, banned IPs
- **Ports**: Open ports, listening services
- **Services**: Running services, unnecessary daemons
- **Users**: Account permissions, sudo access
- **Updates**: Security patches, system updates
- **Logs**: Failed logins, suspicious activity
- **Filesystem**: Sensitive file permissions

#### WordPress Security
- **Core**: Version, updates, known vulnerabilities
- **Plugins**: Active/inactive, updates, vulnerabilities
- **Themes**: Active themes, updates, vulnerabilities
- **Users**: Admin accounts, weak passwords
- **File Permissions**: wp-config.php, uploads directory
- **wp-config.php**: Security keys, debug mode, database exposure

#### Vulnerabilities
- CVE database matches
- Known exploit availability
- Affected versions
- Patch availability

## Remediation Steps

### Common Critical Findings

#### Firewall Disabled
```bash
# Enable UFW
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### Root Login Enabled
```bash
# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

#### Password Authentication Enabled
```bash
# Disable password auth (ensure SSH keys configured first!)
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### Common High Findings

#### Security Updates Available
```bash
# Install security updates only
vibewp security install-updates --security-only

# Or install all updates
vibewp security install-updates
```

#### Outdated WordPress Core
```bash
# SSH into VPS
vibewp site ssh <site-name>

# Update WordPress via WP-CLI
wp core update --allow-root
wp core update-db --allow-root
```

#### Vulnerable Plugins
```bash
# List plugin updates
vibewp site ssh <site-name>
wp plugin list --allow-root

# Update specific plugin
wp plugin update <plugin-name> --allow-root

# Update all plugins
wp plugin update --all --allow-root
```

### Common Medium Findings

#### Default SSH Port
```bash
# Change SSH port (automatic rollback on failure)
vibewp ssh change-port 2222
```

#### Install fail2ban
```bash
sudo apt-get update
sudo apt-get install fail2ban -y

# Configure SSH jail
sudo tee /etc/fail2ban/jail.local <<EOF
[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF

sudo systemctl restart fail2ban
```

#### File Permission Issues
```bash
# Fix wp-config.php permissions
docker exec <site>-wp chmod 600 /var/www/html/wp-config.php

# Fix uploads directory
docker exec <site>-wp chmod 755 /var/www/html/wp-content/uploads
```

## Best Practices

### Regular Audit Schedule
- **Daily**: Monitor for critical/high findings via cron
- **Weekly**: Full audit with report generation
- **Monthly**: Review and act on medium findings
- **Quarterly**: Comprehensive security review

### Automation
```bash
# Add to crontab
0 2 * * * /usr/local/bin/vibewp security audit-server --format json --output /var/log/vibewp-audit.json

# Alert on critical findings
0 2 * * * /usr/local/bin/vibewp security audit-server --format json | jq '.overall_score' | awk '$1 < 60 { system("mail -s \"Security Score Low\" admin@example.com") }'
```

### Security Hardening Checklist
- [ ] Firewall enabled with minimal open ports
- [ ] SSH key-only authentication
- [ ] Custom SSH port
- [ ] fail2ban active with SSH jail
- [ ] Automatic security updates enabled
- [ ] All WordPress cores up to date
- [ ] No vulnerable plugins/themes
- [ ] Strong admin passwords
- [ ] WP debug mode disabled in production
- [ ] Database credentials secured
- [ ] Regular backups configured

## WPScan API Setup

### Get API Token
1. Visit: https://wpscan.com/api
2. Sign up for free account
3. Verify email
4. Copy API token from dashboard

### Configure Token
```bash
# Set token (stored securely in ~/.vibewp/sites.yaml with 600 perms)
vibewp security set-wpscan-token YOUR_TOKEN_HERE

# Verify configuration
vibewp security audit-server --verbose

# Clear token if needed
vibewp security clear-wpscan-token
```

### API Limits
- **Free Tier**: 25 requests/day
- **Paid Tier**: 500-10,000 requests/day
- Rate limited to 1 request/second

### What Gets Scanned
Per site (counts as multiple requests):
- WordPress core version: 1 request
- Active plugins: 1 request per plugin (limited to 10)
- Active themes: 1 request per theme (limited to 5)

Example: Site with 5 active plugins and 1 theme = 7 API requests

## Lynis Installation

### Ubuntu/Debian
```bash
# Install from repository
sudo apt-get update
sudo apt-get install lynis -y

# Verify installation
lynis show version
```

### Manual Installation
```bash
# Clone repository
cd /usr/local
sudo git clone https://github.com/CISOfy/lynis
sudo chown -R root:root /usr/local/lynis

# Create symlink
sudo ln -s /usr/local/lynis/lynis /usr/local/bin/lynis

# Run audit
sudo lynis audit system
```

### What Lynis Checks
- Kernel hardening
- Boot and services
- Authentication mechanisms
- File and directory permissions
- User accounts
- Logging and monitoring
- Cryptography
- Virtualization
- Security frameworks (AppArmor, SELinux)

## Report Format Examples

### Console Output
```
================================================================================
VIBEWP SECURITY AUDIT REPORT
================================================================================
Generated: 2025-11-10T12:00:00Z
Score: 75/100

SYSTEM SECURITY
--------------------------------------------------------------------------------
SSH: 2 issue(s)
  [MEDIUM] Default SSH port in use
  [HIGH] Password authentication enabled

FIREWALL: 1 issue(s)
  [MEDIUM] Unrestricted access on port 80

WORDPRESS SECURITY
--------------------------------------------------------------------------------
Sites audited: 2

myblog: 3 issue(s)
  [HIGH] WordPress core outdated: 6.3.1 (latest: 6.4.0)
  [MEDIUM] Plugin needs update: contact-form-7
  [LOW] Debug mode enabled
```

### JSON Structure
```json
{
  "timestamp": "2025-11-10T12:00:00Z",
  "overall_score": 75,
  "system": {
    "ssh": {
      "findings": [...]
    },
    "firewall": {...}
  },
  "wordpress": {
    "sites_audited": 2,
    "findings": [...],
    "sites": {
      "myblog": {...}
    }
  },
  "vulnerabilities": {
    "total_vulnerabilities": 3,
    "sites": {...}
  },
  "lynis": {
    "hardening_index": 68,
    "warnings": 2
  }
}
```

## Troubleshooting

### Audit Takes Too Long
- Use `--skip-wordpress` for system-only audit
- Use `--skip-lynis` to skip Lynis integration
- Reduce number of active plugins per site

### WPScan Rate Limit Exceeded
- Free tier limited to 25 requests/day
- Audit fewer sites or upgrade API plan
- Results are cached for 1 hour

### Lynis Not Found
```bash
# Check installation
which lynis

# Install if missing
sudo apt-get install lynis -y

# Or skip Lynis in audit
vibewp security audit-server --skip-lynis
```

### Permission Denied Errors
```bash
# Ensure SSH access works
vibewp system status

# Check sudo permissions on VPS
ssh user@vps 'sudo whoami'

# Verify docker access
ssh user@vps 'docker ps'
```

### Container Not Running
```bash
# Check container status
vibewp site info <site-name>

# Start containers
docker start <site>-wp <site>-db

# View logs
vibewp site logs <site-name>
```

### No Findings for WordPress
- Verify WP-CLI is available in containers
- Check container is running: `docker ps`
- Verify WordPress path matches template type
- Run with `--verbose` to see detailed errors

## Security Score Interpretation

### 80-100: Good
- No critical findings
- Few high-severity issues
- System properly hardened
- Regular maintenance evident

### 60-79: Fair
- Some high-severity findings
- Multiple medium findings
- Action required within days
- Review security practices

### 40-59: Poor
- Critical findings present
- Many high-severity issues
- Immediate action required
- Potential active threats

### 0-39: Critical
- Multiple critical findings
- Immediate intervention needed
- System likely compromised
- Full security review required

## Next Steps

After audit completion:
1. **Prioritize critical findings** - Fix immediately
2. **Address high findings** - Within 24-48h
3. **Plan medium fixes** - Schedule within week
4. **Document changes** - Track remediation progress
5. **Re-run audit** - Verify improvements
6. **Schedule regular audits** - Maintain security posture
