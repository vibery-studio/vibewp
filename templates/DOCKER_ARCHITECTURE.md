# Docker Network Architecture

## Overview

VibeWP uses Docker container orchestration with Caddy reverse proxy for automatic HTTPS and site isolation.

## Network Topology

```
┌─────────────────────────────────────────────┐
│            Host Machine (VPS)               │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │     Docker Network: "proxy"           │  │
│  │                                       │  │
│  │   ┌─────────────────┐                │  │
│  │   │  Caddy Proxy    │                │  │
│  │   │  :80, :443      │                │  │
│  │   └────┬───────┬────┘                │  │
│  └────────┼───────┼─────────────────────┘  │
│           │       │                         │
│  ┌────────▼───────┼─────────────────────┐  │
│  │ Network: site1_default               │  │
│  │   ┌────▼─────────┐  ┌─────────────┐  │  │
│  │   │ FrankenWP    │  │  MariaDB    │  │  │
│  │   │ site1.com    │  │             │  │  │
│  │   └──────────────┘  └─────────────┘  │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  ┌──────────────────┼─────────────────────┐│
│  │ Network: site2_default               │  │
│  │   ┌────▼─────────┐  ┌──────┐ ┌─────┐ │  │
│  │   │     OLS      │  │MariaDB│ │Redis│ │  │
│  │   │  site2.com   │  │       │ │     │ │  │
│  │   └──────────────┘  └───────┘ └─────┘ │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## Components

### 1. Caddy Reverse Proxy

**Image**: `lucaslorentz/caddy-docker-proxy:2.3`

**Purpose**:
- Central reverse proxy for all WordPress sites
- Automatic HTTPS certificate management (Let's Encrypt/ZeroSSL)
- Container auto-discovery via Docker labels
- SSL/TLS termination

**Configuration**:
- Monitors Docker socket for container events
- Auto-generates proxy rules from container labels
- Stores certificates in persistent volumes
- Connected to all site networks via "proxy" network

**Ports**:
- 80: HTTP (auto-redirects to HTTPS)
- 443: HTTPS
- 2019: Admin API (internal)

**Health Check**: Checks Caddy admin API every 30s

### 2. FrankenWP Stack

**Image**: `stephenmiracle/frankenwp:latest`

**Components**:
- FrankenPHP (Go-based PHP runtime)
- Built-in Caddy web server
- WordPress core
- MariaDB 10.11

**Features**:
- Worker mode for improved performance
- Built-in OPcache and APCu
- No separate web server needed
- Optimized for concurrency

**Network**:
- Site-specific network (`{site_name}_default`)
- Connected to "proxy" network for Caddy communication

**Volumes**:
- `wp_content`: WordPress content directory
- `wp_config`: WordPress configuration
- `db_data`: MariaDB data

**Template Variables**:
```jinja2
{{ site_name }}         # Unique site identifier
{{ domain }}            # Primary domain (e.g., example.com)
{{ db_name }}           # Database name
{{ db_user }}           # Database user
{{ db_password }}       # Database password
{{ db_mode }}           # Database mode: 'dedicated' or 'shared'
```

**Environment Variables** (auto-configured):
- `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` - Database connection
- `SERVER_NAME` - Domain for FrankenPHP
- `FORCE_HTTPS` - Always "true" (Caddy handles SSL)
- `CACHE_LOC`, `TTL`, `BYPASS_PATH_PREFIX` - Souin cache settings

### 3. OpenLiteSpeed Stack

**Image**: `litespeedtech/openlitespeed:latest`

**Components**:
- OpenLiteSpeed web server
- WordPress (via app installer)
- MariaDB 10.11
- Redis (object caching)
- phpMyAdmin (database management)

**Features**:
- LiteSpeed Cache plugin pre-configured
- Redis object caching integration
- Admin panel on port 7080
- High performance event-driven architecture

**Network**:
- Site-specific network (`{site_name}_default`)
- Connected to "proxy" network
- phpMyAdmin on subdomain (pma.{domain})

**Volumes**:
- `db_data`: MariaDB data
- `redis_data`: Redis persistence
- `lsws_conf`: LiteSpeed configuration
- `lsws_admin_conf`: Admin configuration
- `acme`: SSL certificates (Caddy handles this)
- `lsws_logs`: Access and error logs

**Template Variables**:
```jinja2
{{ site_name }}              # Unique site identifier
{{ domain }}                 # Primary domain
{{ db_name }}                # Database name
{{ db_user }}                # Database user
{{ db_password }}            # Database password
{{ lsws_admin_user }}        # OLS admin username (default: admin)
{{ lsws_admin_pass }}        # OLS admin password
{{ admin_port }}             # OLS admin port (default: 7080)
{{ redis_maxmemory }}        # Redis max memory (default: 256mb)
{{ www_redirect }}           # Redirect www to non-www (optional)
{{ pma_basic_auth }}         # Enable phpMyAdmin basic auth
{{ pma_auth_user }}          # phpMyAdmin auth username
{{ pma_auth_pass_hash }}     # phpMyAdmin auth password hash
```

## Network Isolation

### Proxy Network

**Name**: `proxy`
**Type**: External (must be created manually)
**Purpose**: Shared network for Caddy to communicate with all sites

**Creation**:
```bash
docker network create proxy
```

### Site Networks

**Name**: `{site_name}_default`
**Type**: Internal (created per site)
**Purpose**: Isolate site containers from other sites

**Characteristics**:
- Each site gets dedicated network
- Only site's containers can communicate internally
- Caddy bridges communication via proxy network
- Sites cannot directly access each other

## Automatic HTTPS

### How It Works

1. Site container starts with Caddy labels:
   ```yaml
   labels:
     caddy: example.com
     caddy.reverse_proxy: "{{upstreams 80}}"
     caddy.tls: "internal"
   ```

2. Caddy detects new container via Docker socket

3. Caddy generates configuration automatically

4. Caddy requests SSL certificate from Let's Encrypt

5. Certificate stored in `caddy_data` volume

6. HTTPS enabled automatically (no manual config)

### Certificate Management

**Provider**: Let's Encrypt / ZeroSSL
**Renewal**: Automatic (60 days before expiry)
**Storage**: Docker volume `caddy_data`
**Rate Limits**: 50 certs/week per domain (use staging for testing)

**Staging Mode** (for testing):
```yaml
# In Caddyfile.j2
acme_ca https://acme-staging-v02.api.letsencrypt.org/directory
```

## Health Checks

All services include health checks for reliability:

### Caddy
- **Check**: Admin API availability
- **Interval**: 30s
- **Timeout**: 10s
- **Start Period**: 10s

### FrankenWP
- **Check**: PHP-FPM health
- **Interval**: 30s
- **Timeout**: 10s
- **Start Period**: 60s (WordPress init)

### OpenLiteSpeed
- **Check**: HTTP response on localhost
- **Interval**: 30s
- **Timeout**: 10s
- **Start Period**: 60s

### MariaDB
- **Check**: Connection + InnoDB initialized
- **Interval**: 30s
- **Timeout**: 10s
- **Start Period**: 30s

### Redis
- **Check**: PING command
- **Interval**: 30s
- **Timeout**: 10s
- **Start Period**: 10s

## Security Considerations

### 1. Docker Socket Access
- Mounted read-only to Caddy
- Only Caddy container has access
- Site containers have no socket access

### 2. Network Isolation
- Each site on separate network
- No direct inter-site communication
- Only Caddy bridges networks

### 3. Credentials
- Database passwords in compose files (not images)
- Use strong passwords (min 20 chars)
- Consider Docker secrets for production

### 4. Admin Access
- OLS admin panel bound to 127.0.0.1 only
- phpMyAdmin on separate subdomain
- Optional basic auth for phpMyAdmin

### 5. TLS/SSL
- Caddy handles all HTTPS termination
- Backend containers use HTTP internally
- Automatic certificate renewal

## Template Rendering

Templates use Jinja2 syntax for variable substitution.

### Example: Render FrankenWP Template

```python
from jinja2 import Template

template = Template(open('templates/frankenwp/docker-compose.yml.j2').read())
output = template.render(
    site_name='mysite',
    domain='example.com',
    db_name='wp_mysite',
    db_user='wp_user',
    db_password='SecurePass123!',
    num_workers=2,
    www_redirect=False
)

with open('docker-compose.yml', 'w') as f:
    f.write(output)
```

### Example: Render OLS Template

```python
from jinja2 import Template

template = Template(open('templates/ols/docker-compose.yml.j2').read())
output = template.render(
    site_name='mysite',
    domain='example.com',
    db_name='wp_mysite',
    db_user='wp_user',
    db_password='SecurePass123!',
    lsws_admin_user='admin',
    lsws_admin_pass='AdminPass123!',
    admin_port=7080,
    redis_maxmemory='256mb',
    www_redirect=False,
    pma_basic_auth=True,
    pma_auth_user='admin',
    pma_auth_pass_hash='$2y$10$...'  # bcrypt hash
)

with open('docker-compose.yml', 'w') as f:
    f.write(output)
```

## Deployment Workflow

### 1. Initial Setup

```bash
# Create proxy network
docker network create proxy

# Deploy Caddy
cd /opt/vps-wp-manager/caddy
docker compose up -d
```

### 2. Deploy Site

```bash
# Render template
python3 cli/render_template.py \
  --template templates/frankenwp/docker-compose.yml.j2 \
  --output sites/mysite/docker-compose.yml \
  --vars site_name=mysite domain=example.com ...

# Start site
cd sites/mysite
docker compose up -d
```

### 3. Verify

```bash
# Check Caddy logs
docker logs caddy_proxy

# Check site containers
docker ps | grep mysite

# Test HTTPS
curl -I https://example.com
```

## Troubleshooting

### Issue: Certificate not issued

**Cause**: DNS not pointing to server, firewall blocking ports 80/443

**Solution**:
```bash
# Check DNS
dig example.com

# Check ports
sudo netstat -tuln | grep -E ':(80|443)'

# Check Caddy logs
docker logs caddy_proxy
```

### Issue: Site not accessible

**Cause**: Container not on proxy network, incorrect labels

**Solution**:
```bash
# Verify network
docker network inspect proxy

# Check container networks
docker inspect mysite_wp | grep -A 10 Networks

# Verify labels
docker inspect mysite_wp | grep -A 20 Labels
```

### Issue: Database connection failed

**Cause**: DB not initialized, incorrect credentials

**Solution**:
```bash
# Check DB health
docker exec mysite_db healthcheck.sh --connect

# Check logs
docker logs mysite_db

# Verify credentials in compose file
```

## Performance Tuning

### FrankenWP

**Worker Count**: Set based on CPU cores
```yaml
NUM_WORKERS=4  # For 4 CPU cores
```

**Memory**: Adjust PHP memory limit
```yaml
MEMORY_LIMIT=512M
```

### OpenLiteSpeed

**MariaDB Buffer Pool**: Set to 50-70% of available RAM
```yaml
INNODB_BUFFER_POOL_SIZE=2G
```

**Redis Max Memory**: Set based on object cache needs
```yaml
REDIS_MAXMEMORY=512mb
```

**Connection Pool**: Adjust for traffic
```yaml
MYSQL_MAX_CONNECTIONS=200
```

## Backup Strategy

### Volumes to Backup

**Per Site**:
- `{site_name}_wp_content` - WordPress files
- `{site_name}_db_data` - Database
- `{site_name}_redis_data` - Redis cache (optional)

**Global**:
- `caddy_data` - SSL certificates
- `caddy_config` - Caddy configuration

### Backup Commands

```bash
# Backup site database
docker exec mysite_db mysqldump -u wp_user -p wp_mysite > backup.sql

# Backup WordPress files
docker run --rm -v mysite_wp_content:/data -v $(pwd):/backup \
  alpine tar czf /backup/wp-content.tar.gz -C /data .

# Backup Caddy certificates
docker run --rm -v caddy_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/caddy-certs.tar.gz -C /data .
```

## Monitoring

### Container Health

```bash
# Check all containers
docker ps --format "table {{.Names}}\t{{.Status}}"

# Check specific site
docker compose ps
```

### Caddy Metrics

```bash
# Access metrics endpoint
curl http://localhost:2019/metrics

# Optional: Deploy Prometheus + Grafana
```

### Logs

```bash
# Caddy logs
docker logs -f caddy_proxy

# Site logs
docker logs -f mysite_wp
docker logs -f mysite_db

# OLS access logs
docker exec mysite_ols tail -f /usr/local/lsws/logs/access.log
```

## Scaling Considerations

### Vertical Scaling
- Increase container resources (CPU, memory)
- Tune database parameters
- Add more worker processes

### Horizontal Scaling
- Multiple sites on same server (current architecture)
- Future: Distribute sites across multiple VPS
- Use external database cluster (RDS, managed MariaDB)

## Next Steps (Phase 03)

1. Python CLI to render templates
2. Site provisioning automation
3. SSL certificate monitoring
4. Backup automation
5. Health check monitoring
6. Log aggregation
