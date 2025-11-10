# VibeWP Docker Templates

Docker Compose templates for WordPress deployments with automatic HTTPS via Caddy reverse proxy.

## Directory Structure

```
vibewp/templates/
├── README.md                      # This file
├── DOCKER_ARCHITECTURE.md         # Network topology & architecture docs
├── TEMPLATE_VARIABLES.md          # Complete variable reference
├── caddy/
│   ├── docker-compose.yml         # Caddy reverse proxy (static)
│   └── Caddyfile.j2              # Caddy config template (optional)
├── frankenwp/
│   ├── docker-compose.yml.j2     # FrankenWP + MariaDB template
│   └── .env.template             # Environment variables example
└── ols/
    ├── docker-compose.yml.j2     # OpenLiteSpeed + MariaDB + Redis template
    └── .env.template             # Environment variables example
```

## Quick Start

### 1. Deploy Caddy Proxy

```bash
# Create proxy network
docker network create proxy

# Deploy Caddy
cd /opt/vps-wp-manager/caddy
cp -r /path/to/vibewp/templates/caddy/* .
docker compose up -d

# Verify
docker logs caddy_proxy
```

### 2. Deploy FrankenWP Site

```bash
# Prepare site directory
mkdir -p /opt/vps-wp-manager/sites/mysite
cd /opt/vps-wp-manager/sites/mysite

# Render template
python3 <<EOF
from jinja2 import Template

template = Template(open('/path/to/vibewp/templates/frankenwp/docker-compose.yml.j2').read())
output = template.render(
    site_name='mysite',
    domain='example.com',
    db_name='wp_mysite',
    db_user='wp_user',
    db_password='SecurePassword123!'
)

with open('docker-compose.yml', 'w') as f:
    f.write(output)
EOF

# Deploy
docker compose up -d

# Verify
docker ps | grep mysite
curl -I https://example.com
```

### 3. Deploy OLS Site

```bash
# Prepare site directory
mkdir -p /opt/vps-wp-manager/sites/mysite
cd /opt/vps-wp-manager/sites/mysite

# Render template
python3 <<EOF
from jinja2 import Template

template = Template(open('/path/to/vibewp/templates/ols/docker-compose.yml.j2').read())
output = template.render(
    site_name='mysite',
    domain='example.com',
    db_name='wp_mysite',
    db_user='wp_user',
    db_password='SecurePassword123!',
    lsws_admin_pass='AdminPassword123!'
)

with open('docker-compose.yml', 'w') as f:
    f.write(output)
EOF

# Deploy
docker compose up -d

# Verify
docker ps | grep mysite
curl -I https://example.com
```

## Templates

### Caddy Reverse Proxy

**File**: `caddy/docker-compose.yml`
**Type**: Static (no variables)
**Purpose**: Central reverse proxy for all sites

**Features**:
- Auto HTTPS via Let's Encrypt/ZeroSSL
- Docker container auto-discovery
- SSL certificate management
- HTTP to HTTPS redirect

**Network**: Creates `proxy` network (external)

**Ports**:
- 80: HTTP
- 443: HTTPS
- 2019: Admin API (internal)

### FrankenWP

**File**: `frankenwp/docker-compose.yml.j2`
**Type**: Jinja2 template
**Purpose**: High-performance WordPress with FrankenPHP

**Components**:
- FrankenPHP (Go-based PHP runtime)
- MariaDB 10.11
- Built-in Caddy web server

**Required Variables**:
- `site_name` - Unique identifier
- `domain` - Primary domain
- `db_name` - Database name
- `db_user` - Database username
- `db_password` - Database password

**Optional Variables**:
- `num_workers` - FrankenPHP workers (default: 2)
- `www_redirect` - Redirect www to non-www (default: false)

**Performance**:
- Worker mode for concurrency
- Built-in OPcache
- Optimized for high traffic

### OpenLiteSpeed

**File**: `ols/docker-compose.yml.j2`
**Type**: Jinja2 template
**Purpose**: Enterprise WordPress with LiteSpeed Cache

**Components**:
- OpenLiteSpeed web server
- MariaDB 10.11
- Redis (object caching)
- phpMyAdmin (database management)

**Required Variables**:
- `site_name` - Unique identifier
- `domain` - Primary domain
- `db_name` - Database name
- `db_user` - Database username
- `db_password` - Database password
- `lsws_admin_pass` - OLS admin password

**Optional Variables**:
- `lsws_admin_user` - Admin username (default: admin)
- `admin_port` - Admin panel port (default: 7080)
- `redis_maxmemory` - Redis memory limit (default: 256mb)
- `pma_basic_auth` - Enable phpMyAdmin auth (default: false)

**Features**:
- LiteSpeed Cache pre-configured
- Redis object caching
- Admin panel on :7080
- phpMyAdmin on subdomain

## Network Architecture

### Topology

```
Caddy (proxy network)
  │
  ├── Site 1 (site1_default network)
  │   ├── WordPress/OLS
  │   ├── MariaDB
  │   └── Redis (OLS only)
  │
  └── Site 2 (site2_default network)
      ├── WordPress/OLS
      ├── MariaDB
      └── Redis (OLS only)
```

### Isolation

- Each site on separate network
- Only Caddy bridges networks
- No inter-site communication
- Caddy on shared `proxy` network

### Security

- Docker socket read-only (Caddy only)
- Network isolation per site
- HTTPS termination at Caddy
- Backend containers use HTTP
- Strong passwords required (20+ chars)

## Template Rendering

### Using Python

```python
from jinja2 import Template

template = Template(open('template.j2').read())
output = template.render(
    site_name='mysite',
    domain='example.com',
    # ... other variables
)

with open('docker-compose.yml', 'w') as f:
    f.write(output)
```

### Using CLI (Phase 03)

```bash
# After Phase 03 implementation
vibewp create mysite --domain example.com --type frankenwp
vibewp create mysite --domain example.com --type ols
```

## Health Checks

All services include health checks:

- **Caddy**: Admin API availability (30s interval)
- **WordPress/OLS**: HTTP response (30s interval)
- **MariaDB**: Connection + InnoDB init (30s interval)
- **Redis**: PING command (30s interval)

## SSL/TLS

### Automatic HTTPS

Caddy automatically:
1. Detects new containers via labels
2. Requests SSL certificate from Let's Encrypt
3. Configures HTTPS routing
4. Renews certificates (60 days before expiry)

### Staging Mode

For testing, use Let's Encrypt staging:

```yaml
# In Caddyfile.j2
acme_ca https://acme-staging-v02.api.letsencrypt.org/directory
```

### Certificate Storage

Certificates stored in Docker volume `caddy_data`.

**Backup**:
```bash
docker run --rm -v caddy_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/caddy-certs.tar.gz -C /data .
```

## Monitoring

### Container Status

```bash
# All containers
docker ps

# Site-specific
docker compose ps

# Logs
docker logs -f caddy_proxy
docker logs -f mysite_wp
docker logs -f mysite_db
```

### Caddy Metrics

```bash
# Admin API
curl http://localhost:2019/config/

# Metrics endpoint
curl http://localhost:2019/metrics
```

## Backup Strategy

### What to Backup

**Per Site**:
- `{site_name}_wp_content` - WordPress files
- `{site_name}_db_data` - Database

**Global**:
- `caddy_data` - SSL certificates
- `caddy_config` - Caddy config

### Backup Commands

```bash
# Database
docker exec mysite_db mysqldump -u wp_user -p wp_mysite > backup.sql

# WordPress files
docker run --rm -v mysite_wp_content:/data -v $(pwd):/backup \
  alpine tar czf /backup/wp-content.tar.gz -C /data .

# Caddy certificates
docker run --rm -v caddy_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/caddy-certs.tar.gz -C /data .
```

### Restore Commands

```bash
# Database
docker exec -i mysite_db mysql -u wp_user -p wp_mysite < backup.sql

# WordPress files
docker run --rm -v mysite_wp_content:/data -v $(pwd):/backup \
  alpine tar xzf /backup/wp-content.tar.gz -C /data

# Caddy certificates
docker run --rm -v caddy_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/caddy-certs.tar.gz -C /data
```

## Troubleshooting

### Certificate Not Issued

**Symptoms**: HTTPS not working, Caddy logs show ACME errors

**Causes**:
- DNS not pointing to server
- Firewall blocking ports 80/443
- Rate limit exceeded (50 certs/week)

**Solutions**:
```bash
# Check DNS
dig +short example.com

# Check ports
sudo netstat -tuln | grep -E ':(80|443)'

# Use staging CA for testing
# Edit Caddyfile.j2, uncomment staging line
```

### Site Not Accessible

**Symptoms**: 502 Bad Gateway, site unreachable

**Causes**:
- Container not on proxy network
- Incorrect Caddy labels
- Container unhealthy

**Solutions**:
```bash
# Verify network
docker network inspect proxy | grep mysite_wp

# Check labels
docker inspect mysite_wp | grep -A 10 Labels

# Check health
docker ps | grep mysite
```

### Database Connection Failed

**Symptoms**: WordPress shows "Error establishing database connection"

**Causes**:
- Incorrect credentials
- Database not initialized
- DB container unhealthy

**Solutions**:
```bash
# Check DB health
docker exec mysite_db healthcheck.sh --connect

# Check logs
docker logs mysite_db

# Verify credentials
docker exec mysite_db mysql -u wp_user -p -e "SHOW DATABASES;"
```

### Performance Issues

**Symptoms**: Slow page loads, high CPU/memory

**Causes**:
- Insufficient resources
- Too few workers (FrankenWP)
- Small buffer pool (MariaDB)

**Solutions**:

**FrankenWP**:
```yaml
NUM_WORKERS=4  # Increase workers (1 per CPU core)
MEMORY_LIMIT=512M  # Increase PHP memory
```

**OLS**:
```yaml
INNODB_BUFFER_POOL_SIZE=2G  # Increase buffer pool
REDIS_MAXMEMORY=512mb  # Increase Redis cache
```

## Performance Tuning

### FrankenWP

```yaml
# Optimize for 4 CPU cores, 4GB RAM
NUM_WORKERS=4
MEMORY_LIMIT=512M
MAX_UPLOAD_SIZE=128M
INNODB_BUFFER_POOL_SIZE=1G
```

### OpenLiteSpeed

```yaml
# Optimize for 4 CPU cores, 8GB RAM
MEMORY_LIMIT=1G
MAX_UPLOAD_SIZE=256M
INNODB_BUFFER_POOL_SIZE=4G
REDIS_MAXMEMORY=1gb
MYSQL_MAX_CONNECTIONS=200
```

## Security Best Practices

1. **Strong Passwords**: Min 20 characters, mixed case, numbers, symbols
2. **Network Isolation**: Each site on separate network
3. **Docker Socket**: Read-only mount (Caddy only)
4. **Admin Access**: Bind OLS admin to 127.0.0.1 only
5. **Basic Auth**: Enable for phpMyAdmin
6. **Regular Updates**: Update container images regularly
7. **Backup**: Daily database backups, weekly full backups
8. **Monitoring**: Set up log aggregation and alerts

## Documentation

- **DOCKER_ARCHITECTURE.md** - Complete network topology and architecture
- **TEMPLATE_VARIABLES.md** - All template variables reference
- **.env.template** - Environment variables examples

## Next Steps

**Phase 03**: Python CLI implementation
- Interactive site creation
- Template rendering automation
- Site management (start, stop, remove)
- SSL certificate monitoring
- Backup/restore commands
- Health check monitoring

## Contributing

### Adding New Templates

1. Create template directory: `templates/{name}/`
2. Add `docker-compose.yml.j2` template
3. Add `.env.template` example
4. Document variables in `TEMPLATE_VARIABLES.md`
5. Add usage examples to this README

### Testing Templates

```python
# tests/test_templates.py
from jinja2 import Template

def test_template():
    template = Template(open('template.j2').read())
    output = template.render(site_name='test', domain='test.com', ...)
    assert 'test_wp' in output
```

## Support

**Phase 02 Implementation**: Docker infrastructure only
**Phase 03 Implementation**: CLI automation (upcoming)

For issues, see troubleshooting section or review logs:
```bash
docker logs caddy_proxy
docker logs {site_name}_wp
docker logs {site_name}_db
```
