# VibeWP CLI - Usage Examples

## Site Management Commands

### Create a New WordPress Site

**Interactive Mode** (Recommended):
```bash
vibewp site create
```

This will prompt you for:
- Site name (alphanumeric, underscores)
- Domain name
- WordPress engine (1=FrankenWP, 2=OpenLiteSpeed)
- Admin email
- Site title

**CLI Mode** (All options provided):
```bash
vibewp site create \
  --site-name mysite \
  --domain mysite.example.com \
  --wp-type frankenwp \
  --admin-email admin@example.com \
  --site-title "My WordPress Site"
```

**What Happens**:
1. Validates inputs
2. Generates secure credentials (DB + WP admin)
3. Renders docker-compose template
4. Deploys containers to VPS
5. Waits for database initialization
6. Installs WordPress via WP-CLI
7. Displays admin credentials (SAVE THESE!)

**Estimated Time**: 4-5 minutes

### List All Sites

```bash
vibewp site list
```

**Output**:
```
                    WordPress Sites
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Name     ┃ Domain             ┃ Type      ┃ Status  ┃ Created    ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━┩
│ mysite   │ mysite.example.com │ frankenwp │ running │ 2025-11-10 │
│ shop     │ shop.example.com   │ ols       │ running │ 2025-11-10 │
└──────────┴────────────────────┴───────────┴─────────┴────────────┘
```

### Get Site Details

```bash
vibewp site info mysite
```

**Output**:
```
╭────────────── Site: mysite ──────────────╮
│ Site Information                         │
│                                          │
│ Name: mysite                             │
│ Domain: mysite.example.com               │
│ Type: frankenwp                          │
│ Status: running                          │
│ Created: 2025-11-10T15:30:00.000000      │
│                                          │
│ URLs:                                    │
│   Site: https://mysite.example.com       │
│   Admin: https://mysite.example.com/...  │
╰──────────────────────────────────────────╯
```

### View Container Logs

**All containers**:
```bash
vibewp site logs mysite
```

**Specific service**:
```bash
vibewp site logs mysite --service wp
vibewp site logs mysite --service db
vibewp site logs mysite --service redis  # OLS only
```

**Follow logs (live)**:
```bash
vibewp site logs mysite --follow
```

**Limit output**:
```bash
vibewp site logs mysite --tail 50
```

### Delete a Site

**With confirmation prompt**:
```bash
vibewp site delete mysite
```

**Skip confirmation**:
```bash
vibewp site delete mysite --force
```

**What Gets Deleted**:
- All containers (WordPress, Database, Redis, etc.)
- All Docker volumes (database data, uploads)
- Site directory on VPS
- Registry entry

**⚠️ WARNING**: This is permanent and cannot be undone!

## Configuration Commands

### Initialize Configuration

```bash
vibewp config init
```

Creates `~/.vibewp/sites.yaml` with:
- VPS connection details
- WordPress defaults
- Docker settings
- Empty site registry

### Show Current Configuration

```bash
vibewp config show
```

### Show Configuration File Path

```bash
vibewp config path
```

## Testing Commands

### Test SSH Connection

```bash
vibewp test-ssh
```

Verifies:
- SSH key exists and has correct permissions
- Connection to VPS successful
- Can execute remote commands

### Test Docker Connection

```bash
vibewp test-docker
```

Verifies:
- Docker daemon is running
- Can list containers
- API is accessible

### Test Template System

```bash
vibewp test-templates
```

Lists available templates:
- FrankenWP docker-compose
- OpenLiteSpeed docker-compose
- Caddy configuration

## Interactive Menu

```bash
vibewp menu
```

Launches interactive menu with:
- Create new site
- List sites
- Site management
- Configuration
- System tests

## Complete Workflow Example

### Creating Your First Site

1. **Initialize configuration**:
```bash
vibewp config init
```

2. **Edit configuration** (if needed):
```bash
vim ~/.vibewp/sites.yaml
```

3. **Test VPS connection**:
```bash
vibewp test-ssh
```

4. **Create a site**:
```bash
vibewp site create
```
Follow prompts:
- Site name: `mysite`
- Domain: `mysite.example.com`
- Engine: `1` (FrankenWP)
- Email: `admin@example.com`
- Title: `My Site`

5. **Save credentials** displayed in output

6. **Verify site**:
```bash
vibewp site list
vibewp site info mysite
```

7. **Access your site**:
- Frontend: `https://mysite.example.com`
- Admin: `https://mysite.example.com/wp-admin`

### Creating Multiple Sites (Mixed Deployment)

```bash
# Create FrankenWP site
vibewp site create \
  --site-name blog \
  --domain blog.example.com \
  --wp-type frankenwp \
  --admin-email admin@blog.com

# Create OpenLiteSpeed site
vibewp site create \
  --site-name shop \
  --domain shop.example.com \
  --wp-type ols \
  --admin-email admin@shop.com

# List both sites
vibewp site list
```

**Result**: Two sites running on same VPS with different engines!

## Troubleshooting

### Site creation fails

**View logs**:
```bash
vibewp site logs sitename
```

**Check container status** (via SSH):
```bash
ssh -i ~/.ssh/key user@vps
docker ps -a
docker logs sitename_wp
docker logs sitename_db
```

### Can't access site after creation

1. **Wait 5-10 minutes** for DNS propagation
2. **Check HTTPS certificate** - may take time for Let's Encrypt
3. **Test direct IP access** to verify containers running
4. **Check Caddy proxy** is running

### Database connection errors

```bash
# Check database container health
vibewp site logs sitename --service db

# Restart containers via SSH
ssh -i ~/.ssh/key user@vps
cd /opt/vibewp/sites/sitename
docker compose restart
```

### Delete site and recreate

```bash
vibewp site delete sitename --force
vibewp site create --site-name sitename ...
```

## Advanced Usage

### Custom VPS Configuration

Edit `~/.vibewp/sites.yaml`:
```yaml
vps:
  host: your-vps-ip
  port: 22
  user: root
  key_path: ~/.ssh/your_key

docker:
  base_path: /opt/vibewp
  network_name: proxy

wordpress:
  default_admin_email: admin@example.com
  default_timezone: UTC
  default_locale: en_US
```

### Environment-Specific Domains

**Development**:
```bash
vibewp site create --domain dev.site.com ...
```

**Staging**:
```bash
vibewp site create --domain staging.site.com ...
```

**Production**:
```bash
vibewp site create --domain site.com ...
```

All on the same VPS!

## Best Practices

1. **Save credentials immediately** - they're only shown once
2. **Use descriptive site names** - easier to manage multiple sites
3. **Test on staging first** - create staging.site.com before production
4. **Monitor logs** - `vibewp site logs` shows issues early
5. **Regular backups** - use WP backup plugins or manual dumps
6. **Choose engine wisely**:
   - **FrankenWP**: High performance, modern, lower memory
   - **OLS**: Proven stability, LiteSpeed Cache, more resources

## Quick Reference

| Command | Description |
|---------|-------------|
| `vibewp site create` | Create new WordPress site |
| `vibewp site list` | List all sites |
| `vibewp site info <name>` | Show site details |
| `vibewp site logs <name>` | View container logs |
| `vibewp site delete <name>` | Delete site |
| `vibewp config init` | Initialize configuration |
| `vibewp config show` | Show current config |
| `vibewp test-ssh` | Test VPS connection |
| `vibewp menu` | Interactive menu |

## Support

For issues, check:
- Container logs: `vibewp site logs <name>`
- Docker status: `vibewp test-docker`
- SSH connection: `vibewp test-ssh`
- Phase 04 implementation report
