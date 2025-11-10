# SFTP Access Management Guide

## Overview

VibeWP provides secure SFTP access with **site-specific restrictions** using chroot jails. Users can only access their assigned site's `wp-content` directory via SFTP - no shell access, no other directories, no other sites.

## Architecture

### Security Model

```
User connects via SFTP
    ↓
SSH authenticates with key
    ↓
Match User directive triggers
    ↓
ChrootDirectory activated: /opt/vibewp/sftp/sftp_mysite_john/
    ↓
ForceCommand internal-sftp (no shell)
    ↓
User sees: /wp-content → symlink to site's Docker volume
    ↓
ACLs grant www-data group write access
```

### Directory Structure

```
/opt/vibewp/sftp/
├── sftp_mysite_john/           # Chroot base (root:root, 755)
│   ├── sftp_mysite_john/       # User home (user:sftpusers, 700)
│   │   └── .ssh/
│   │       └── authorized_keys # SSH public key
│   └── wp-content → /var/lib/docker/volumes/mysite_wp_data/_data/wp-content
└── sftp_mysite_deploy/
    ├── sftp_mysite_deploy/
    └── wp-content → ...
```

### sshd_config Integration

Each user gets a Match block:

```sshd_config
# SFTP chroot for sftp_mysite_john
Match User sftp_mysite_john
    ChrootDirectory /opt/vibewp/sftp/sftp_mysite_john
    ForceCommand internal-sftp
    AllowTcpForwarding no
    X11Forwarding no
```

## Commands

### Add SFTP Access

Grant SFTP access to a specific site:

```bash
vibewp sftp add-key <site-name> <public-key-file> [--id <identifier>]
```

**Arguments:**
- `site-name`: WordPress site name (e.g., `mysite`)
- `public-key-file`: Path to SSH public key (e.g., `~/.ssh/id_rsa.pub`)
- `--id`: Short identifier for this key (default: `user`)

**Examples:**

```bash
# Grant access to developer John
vibewp sftp add-key mysite ~/.ssh/john_id_rsa.pub --id john

# Grant access to deployment system
vibewp sftp add-key mystore /tmp/deploy_key.pub --id deploy

# Default identifier
vibewp sftp add-key myblog ~/.ssh/id_rsa.pub
```

**Output:**

```
✓ SFTP access created successfully!

Connection Details:
  Username: sftp_mysite_john
  Host: 46.62.225.162
  Port: 22
  Accessible Path: /wp-content

Connect with:
  sftp sftp_mysite_john@46.62.225.162
```

### Remove SFTP Access

Revoke SFTP access:

```bash
vibewp sftp remove-key <site-name> <identifier>
```

**Examples:**

```bash
# Remove John's access
vibewp sftp remove-key mysite john

# Confirmation prompt
Remove SFTP user 'sftp_mysite_john'? [y/N]: y
✓ SFTP access removed successfully!
```

### List SFTP Users

View all SFTP users or filter by site:

```bash
vibewp sftp list [site-name]
```

**Examples:**

```bash
# List all SFTP users
vibewp sftp list

# List users for specific site
vibewp sftp list mysite
```

**Output:**

```
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Username           ┃ Site    ┃ Identifier ┃ UID ┃ Home                ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ sftp_mysite_john   │ mysite  │ john       │ 1002│ /sftp_mysite_john   │
│ sftp_mysite_deploy │ mysite  │ deploy     │ 1003│ /sftp_mysite_deploy │
│ sftp_mystore_jane  │ mystore │ jane       │ 1004│ /sftp_mystore_jane  │
└────────────────────┴─────────┴────────────┴─────┴─────────────────────┘
```

### Test SFTP Configuration

Verify SFTP user is properly configured:

```bash
vibewp sftp test <site-name> <identifier>
```

**Examples:**

```bash
vibewp sftp test mysite john
```

**Output:**

```
Testing SFTP configuration for 'sftp_mysite_john'...

Configuration Checks:
  ✓ User Exists
  ✓ Chroot Dir Exists
  ✓ Authorized Keys Exists
  ✓ Sshd Config Match

✓ All checks passed! SFTP access is properly configured.
```

### Show Information

Display SFTP usage guide:

```bash
vibewp sftp info
```

## Client Usage

### Connect via SFTP

After access is granted, users connect with:

```bash
sftp sftp_<site>_<identifier>@<server-ip>
```

**Example:**

```bash
$ sftp sftp_mysite_john@46.62.225.162

Connected to 46.62.225.162.
sftp> ls
wp-content

sftp> cd wp-content
sftp> ls
plugins  themes  uploads

sftp> cd themes
sftp> put my-theme.zip
Uploading my-theme.zip to /wp-content/themes/my-theme.zip
my-theme.zip                            100%  2048KB   1.5MB/s   00:01

sftp> exit
```

### Directory Restrictions

Users **can** access:
- `/wp-content/`
- `/wp-content/plugins/`
- `/wp-content/themes/`
- `/wp-content/uploads/`
- All subdirectories within wp-content

Users **cannot** access:
- `/` (root)
- `/wp-admin/`
- `/wp-includes/`
- `/opt/vibewp/sites/` (parent directories)
- Other sites' directories
- System directories

### File Operations

All standard SFTP operations work within wp-content:

```bash
sftp> put local-file.php                 # Upload file
sftp> get remote-file.php                # Download file
sftp> mkdir new-directory                # Create directory
sftp> rm old-file.php                    # Delete file
sftp> rename old.php new.php             # Rename file
sftp> ls -la                             # List files
sftp> pwd                                # Print working directory
sftp> cd plugins                         # Change directory
```

**Note:** Shell commands don't work (no `!ls`, no `!cd`, etc.)

## Security Considerations

### Authentication

- **SSH keys only** - No password authentication
- Public key stored in user's `.ssh/authorized_keys`
- Private key must be kept secure by client

### Isolation

- **Chroot jail** - User cannot navigate outside assigned directory
- **No shell access** - `ForceCommand internal-sftp` prevents shell
- **Site-specific** - Each user sees only one site's wp-content
- **No lateral movement** - Cannot access other sites or system files

### Permissions

- Files created by SFTP user have `www-data` group access
- ACLs ensure WordPress can read/write SFTP-uploaded files
- Default permissions: `664` (files), `775` (directories)

### Logging

All SFTP activity is logged in:
- `/var/log/auth.log` - Authentication attempts
- `/var/log/syslog` - SFTP file operations

**Monitor activity:**

```bash
# Watch SFTP logins
tail -f /var/log/auth.log | grep sshd

# Check file operations
tail -f /var/log/syslog | grep sftp-server
```

## Troubleshooting

### Permission Denied After Login

**Symptom:**
```
sftp> ls
Permission denied
```

**Cause:** Chroot directory has wrong ownership

**Fix:**
```bash
# Chroot base must be owned by root
chown root:root /opt/vibewp/sftp/sftp_mysite_john
chmod 755 /opt/vibewp/sftp/sftp_mysite_john
```

### Cannot Upload Files

**Symptom:**
```
sftp> put file.php
Uploading file.php to /wp-content/file.php
remote open("/wp-content/file.php"): Permission denied
```

**Cause:** Missing ACLs on wp-content

**Fix:**
```bash
# Re-apply ACLs
setfacl -R -m u:sftp_mysite_john:rwX /var/lib/docker/volumes/mysite_wp_data/_data/wp-content
setfacl -R -d -m u:sftp_mysite_john:rwX /var/lib/docker/volumes/mysite_wp_data/_data/wp-content
```

### Connection Refused

**Symptom:**
```
ssh: connect to host 46.62.225.162 port 22: Connection refused
```

**Cause:** Firewall blocking port 22

**Fix:**
```bash
# Allow SSH through firewall
vibewp firewall add-rule --port 22 --protocol tcp --comment "SSH/SFTP"
```

### Public Key Not Accepted

**Symptom:**
```
Permission denied (publickey).
```

**Causes:**
1. Wrong private key used
2. authorized_keys has wrong permissions
3. Public key not in authorized_keys

**Fix:**

```bash
# Check authorized_keys permissions
ls -la /opt/vibewp/sftp/sftp_mysite_john/sftp_mysite_john/.ssh/
# Should be: drwx------ .ssh/, -rw------- authorized_keys

# Fix permissions
chmod 700 /opt/vibewp/sftp/sftp_mysite_john/sftp_mysite_john/.ssh
chmod 600 /opt/vibewp/sftp/sftp_mysite_john/sftp_mysite_john/.ssh/authorized_keys
chown -R sftp_mysite_john:sftpusers /opt/vibewp/sftp/sftp_mysite_john/sftp_mysite_john/.ssh
```

### Match User Directive Conflicts

**Symptom:**
```
sshd[1234]: error: Refusing user sftp_mysite_john because account is locked
```

**Cause:** User shell is `/usr/sbin/nologin` but PAM is enforcing it

**Fix:**

```bash
# Edit /etc/pam.d/sshd and comment out:
# account    required     pam_nologin.so

# Or use /bin/false instead
usermod -s /bin/false sftp_mysite_john
```

### Symlink Not Following

**Symptom:**
User sees `wp-content` but cannot access it

**Cause:** ChrootDirectory doesn't allow symlinks outside chroot

**Fix:**

This is a limitation of chroot. Instead of symlinks, use **bind mounts**:

```bash
# Remove symlink
rm /opt/vibewp/sftp/sftp_mysite_john/wp-content

# Create directory and bind mount
mkdir /opt/vibewp/sftp/sftp_mysite_john/wp-content
mount --bind /var/lib/docker/volumes/mysite_wp_data/_data/wp-content \
             /opt/vibewp/sftp/sftp_mysite_john/wp-content

# Make persistent in /etc/fstab
echo "/var/lib/docker/volumes/mysite_wp_data/_data/wp-content /opt/vibewp/sftp/sftp_mysite_john/wp-content none bind 0 0" >> /etc/fstab
```

## Advanced Configuration

### Custom Chroot Path

Edit `/etc/ssh/sshd_config` Match block:

```sshd_config
Match User sftp_mysite_john
    ChrootDirectory /custom/path
    ForceCommand internal-sftp
```

Reload SSH:
```bash
systemctl reload sshd
```

### Multiple Sites Per User

Not recommended for security, but possible:

```bash
# Create user manually
useradd -m -d /sftp_multisite -s /usr/sbin/nologin -g sftpusers sftp_multisite

# Bind mount multiple sites
mkdir -p /opt/vibewp/sftp/sftp_multisite/site1
mkdir -p /opt/vibewp/sftp/sftp_multisite/site2

mount --bind /var/lib/docker/volumes/site1_wp_data/_data/wp-content \
             /opt/vibewp/sftp/sftp_multisite/site1

mount --bind /var/lib/docker/volumes/site2_wp_data/_data/wp-content \
             /opt/vibewp/sftp/sftp_multisite/site2
```

### SFTP-only Users (No SSH)

This is already enforced by `ForceCommand internal-sftp`. Users cannot:
- Execute shell commands
- Run bash/sh
- Access system binaries
- Create reverse shells

## Best Practices

### Key Management

1. **Use separate keys per user** - Don't share private keys
2. **Rotate keys regularly** - Remove old keys, add new ones
3. **Use strong keys** - RSA 4096-bit or Ed25519
4. **Protect private keys** - Encrypt with passphrase

### Access Control

1. **Principle of least privilege** - Only grant access when needed
2. **Remove access promptly** - When employee leaves or project ends
3. **Audit regularly** - Review `vibewp sftp list` periodically
4. **Monitor logs** - Watch `/var/log/auth.log` for suspicious activity

### Permissions

1. **Let ACLs handle permissions** - Don't manually chmod files
2. **Check www-data group** - Ensure SFTP user in www-data group
3. **Test after changes** - Use `vibewp sftp test` after modifications

### Backup

1. **Backup authorized_keys** - Store in password manager
2. **Document access** - Keep spreadsheet of who has access where
3. **Include in disaster recovery** - Test SFTP restore procedure

## Integration Examples

### CI/CD Deployment

GitHub Actions workflow for deploying via SFTP:

```yaml
name: Deploy to WordPress

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install SSH key
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SFTP_PRIVATE_KEY }}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key

      - name: Deploy theme via SFTP
        run: |
          sftp -i ~/.ssh/deploy_key \
               -o StrictHostKeyChecking=no \
               sftp_mysite_deploy@${{ secrets.VPS_IP }} <<EOF
          cd /wp-content/themes
          rm -rf my-theme
          mkdir my-theme
          cd my-theme
          put -r *
          quit
          EOF
```

### VS Code Remote Access

**Install Extension:** Remote - SSH

**Add Host:** `.ssh/config`

```
Host mysite-sftp
    HostName 46.62.225.162
    User sftp_mysite_john
    IdentityFile ~/.ssh/id_rsa
    ForceCommand internal-sftp
    RemoteCommand cd /wp-content
```

**Note:** VS Code may not work perfectly since user has no shell. Consider using SFTP extension instead.

### FileZilla Configuration

1. Open **Site Manager**
2. Click **New Site**
3. Configure:
   - Protocol: `SFTP - SSH File Transfer Protocol`
   - Host: `46.62.225.162`
   - Port: `22`
   - Logon Type: `Key file`
   - User: `sftp_mysite_john`
   - Key file: Browse to private key
4. Click **Connect**

Default directory will be `/wp-content`

## FAQ

**Q: Can users install plugins via SFTP?**
A: Yes, they can upload plugin ZIP files to `/wp-content/plugins/` and extract them.

**Q: Can users edit wp-config.php?**
A: No, wp-config.php is outside wp-content. Use `vibewp site ssh <site>` for that.

**Q: What happens if I delete a site?**
A: SFTP users remain. Remove them manually with `vibewp sftp remove-key`.

**Q: Can I use the same public key for multiple sites?**
A: Yes, each site gets a different username, so the same key can be used.

**Q: How many concurrent SFTP connections allowed?**
A: Unlimited by VibeWP. Limited only by server resources and sshd `MaxSessions`.

**Q: Can I change the username format?**
A: Currently hardcoded as `sftp_<site>_<identifier>`. Modify `cli/utils/sftp.py` if needed.

**Q: Do SFTP users count against system user limits?**
A: Yes, they are real Linux users. Check `/etc/login.defs` for `UID_MAX`.

**Q: Can I use SFTP over non-standard SSH port?**
A: Yes, change VPS SSH port with `vibewp ssh change-port <new-port>`.

## See Also

- [Security Best Practices](./security-best-practices.md)
- [WordPress File Permissions](./wordpress-permissions.md)
- [SSH Configuration Guide](./ssh-configuration.md)
- [User Management](./user-management.md)
