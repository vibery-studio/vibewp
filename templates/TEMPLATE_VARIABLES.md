# Template Variables Reference

## Overview

All Docker Compose templates use Jinja2 syntax for variable substitution. This document lists all available variables for each template.

## Common Variables (All Templates)

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `site_name` | string | Yes | - | Unique site identifier (alphanumeric, no spaces) |
| `domain` | string | Yes | - | Primary domain (e.g., example.com) |
| `db_name` | string | Yes | - | Database name |
| `db_user` | string | Yes | - | Database username |
| `db_password` | string | Yes | - | Database password (min 20 chars recommended) |
| `www_redirect` | boolean | No | `false` | Redirect www.domain to domain |
| `admin_email` | string | No | `admin@{domain}` | Email for Let's Encrypt notifications |

## FrankenWP Template Variables

**Template**: `vibewp/templates/frankenwp/docker-compose.yml.j2`

### WordPress Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `num_workers` | integer | No | `2` | FrankenPHP worker processes (1 per CPU core recommended) |
| `memory_limit` | string | No | `256M` | PHP memory limit |
| `max_upload_size` | string | No | `64M` | Maximum file upload size |
| `max_execution_time` | integer | No | `300` | PHP max execution time (seconds) |

### Database Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `mysql_max_connections` | integer | No | `100` | Maximum database connections |
| `innodb_buffer_pool_size` | string | No | `256M` | InnoDB buffer pool size |
| `innodb_log_file_size` | string | No | `64M` | InnoDB log file size |

### TLS Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `tls_mode` | string | No | `internal` | Certificate mode (internal = Let's Encrypt) |

### Example Usage

```python
from jinja2 import Template

template = Template(open('vibewp/templates/frankenwp/docker-compose.yml.j2').read())
output = template.render(
    # Required
    site_name='mysite',
    domain='example.com',
    db_name='wp_mysite',
    db_user='wp_user',
    db_password='SecurePassword123!',

    # Optional
    num_workers=4,
    www_redirect=True,
    admin_email='admin@example.com',
    memory_limit='512M',
    max_upload_size='128M'
)
```

## OpenLiteSpeed Template Variables

**Template**: `vibewp/templates/ols/docker-compose.yml.j2`

### OpenLiteSpeed Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `lsws_admin_user` | string | No | `admin` | OLS admin panel username |
| `lsws_admin_pass` | string | Yes | - | OLS admin panel password |
| `admin_port` | integer | No | `7080` | OLS admin panel port (bound to 127.0.0.1) |

### Redis Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `redis_maxmemory` | string | No | `256mb` | Redis max memory limit |
| `redis_maxmemory_policy` | string | No | `allkeys-lru` | Redis eviction policy |

### Database Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `mysql_max_connections` | integer | No | `100` | Maximum database connections |
| `innodb_buffer_pool_size` | string | No | `512M` | InnoDB buffer pool size |
| `innodb_log_file_size` | string | No | `128M` | InnoDB log file size |
| `query_cache_size` | string | No | `32M` | MySQL query cache size |

### phpMyAdmin Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `pma_subdomain` | string | No | `pma.{domain}` | phpMyAdmin subdomain |
| `pma_basic_auth` | boolean | No | `false` | Enable HTTP basic auth |
| `pma_auth_user` | string | Conditional | - | Basic auth username (if pma_basic_auth=true) |
| `pma_auth_pass_hash` | string | Conditional | - | Basic auth password hash (bcrypt) |

### Performance Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `memory_limit` | string | No | `512M` | PHP memory limit |
| `max_upload_size` | string | No | `128M` | Maximum file upload size |
| `max_execution_time` | integer | No | `300` | PHP max execution time (seconds) |

### Example Usage

```python
from jinja2 import Template

template = Template(open('vibewp/templates/ols/docker-compose.yml.j2').read())
output = template.render(
    # Required
    site_name='mysite',
    domain='example.com',
    db_name='wp_mysite',
    db_user='wp_user',
    db_password='SecurePassword123!',
    lsws_admin_pass='AdminPassword123!',

    # Optional
    lsws_admin_user='admin',
    admin_port=7080,
    redis_maxmemory='512mb',
    www_redirect=True,
    pma_basic_auth=True,
    pma_auth_user='admin',
    pma_auth_pass_hash='$2y$10$abc...def',  # bcrypt hash
    memory_limit='1G',
    max_upload_size='256M'
)
```

## Caddy Template Variables

**Template**: `vibewp/templates/caddy/Caddyfile.j2`

### Global Configuration

| Variable | Type | Required | Default | Description |
|----------|------|----------|---------|-------------|
| `admin_email` | string | No | `admin@example.com` | Let's Encrypt account email |

### Example Usage

```python
from jinja2 import Template

template = Template(open('vibewp/templates/caddy/Caddyfile.j2').read())
output = template.render(
    admin_email='admin@example.com'
)
```

**Note**: Caddy docker-compose.yml is static (no variables) as it uses Docker labels for auto-configuration.

## Variable Validation Rules

### site_name
- **Pattern**: `^[a-z0-9_-]+$`
- **Length**: 3-30 characters
- **Examples**: `mysite`, `blog-site`, `site_01`

### domain
- **Pattern**: Valid domain format
- **Examples**: `example.com`, `blog.example.com`, `example.co.uk`
- **Invalid**: `http://example.com`, `example.com/path`

### db_name
- **Pattern**: `^[a-zA-Z0-9_]+$`
- **Length**: 3-64 characters
- **Examples**: `wp_mysite`, `wordpress_db`

### db_user
- **Pattern**: `^[a-zA-Z0-9_]+$`
- **Length**: 3-32 characters
- **Examples**: `wp_user`, `dbadmin`

### db_password
- **Pattern**: Strong password (letters, numbers, symbols)
- **Length**: Min 20 characters
- **Examples**: `aB3$xY9@mK7!pQ2#wE5%`

### admin_email
- **Pattern**: Valid email format
- **Examples**: `admin@example.com`, `webmaster@site.com`

## Password Hash Generation

### bcrypt Hash (for phpMyAdmin basic auth)

```bash
# Using htpasswd
htpasswd -nbB admin mypassword

# Output: admin:$2y$10$abc...def
# Use only the hash part after the colon
```

```python
# Using Python bcrypt
import bcrypt

password = b"mypassword"
hashed = bcrypt.hashpw(password, bcrypt.gensalt())
print(hashed.decode())
```

## Security Best Practices

### Password Generation

```bash
# Generate secure random password (20 chars)
openssl rand -base64 32 | cut -c1-20

# Or using Python
python3 -c "import secrets; print(secrets.token_urlsafe(20))"
```

### WordPress Salts

```bash
# Generate WordPress salts
curl -s https://api.wordpress.org/secret-key/1.1/salt/
```

Copy output to .env file or pass as environment variables.

## Environment Variable Files

### FrankenWP .env Structure

```bash
# Site Configuration
SITE_NAME=mysite
DOMAIN=example.com

# Database
DB_NAME=wp_mysite
DB_USER=wp_user
DB_PASSWORD=SecurePassword123!

# WordPress
WORDPRESS_TABLE_PREFIX=wp_
WORDPRESS_DEBUG=false

# Performance
NUM_WORKERS=2
MEMORY_LIMIT=256M
MAX_UPLOAD_SIZE=64M

# Security Salts
WORDPRESS_AUTH_KEY=...
WORDPRESS_SECURE_AUTH_KEY=...
WORDPRESS_LOGGED_IN_KEY=...
WORDPRESS_NONCE_KEY=...
WORDPRESS_AUTH_SALT=...
WORDPRESS_SECURE_AUTH_SALT=...
WORDPRESS_LOGGED_IN_SALT=...
WORDPRESS_NONCE_SALT=...
```

### OLS .env Structure

```bash
# Site Configuration
SITE_NAME=mysite
DOMAIN=example.com

# Database
DB_NAME=wp_mysite
DB_USER=wp_user
DB_PASSWORD=SecurePassword123!

# OLS Admin
LSWS_ADMIN_USER=admin
LSWS_ADMIN_PASS=AdminPassword123!
ADMIN_PORT=7080

# Redis
REDIS_MAXMEMORY=256mb

# phpMyAdmin
PMA_BASIC_AUTH=true
PMA_AUTH_USER=admin
PMA_AUTH_PASS_HASH=$2y$10$...

# Performance
MEMORY_LIMIT=512M
MAX_UPLOAD_SIZE=128M
MYSQL_MAX_CONNECTIONS=100
INNODB_BUFFER_POOL_SIZE=512M

# Security Salts
WORDPRESS_AUTH_KEY=...
WORDPRESS_SECURE_AUTH_KEY=...
WORDPRESS_LOGGED_IN_KEY=...
WORDPRESS_NONCE_KEY=...
WORDPRESS_AUTH_SALT=...
WORDPRESS_SECURE_AUTH_SALT=...
WORDPRESS_LOGGED_IN_SALT=...
WORDPRESS_NONCE_SALT=...
```

## CLI Integration (Phase 03)

### Python Template Renderer

```python
# cli/utils/template_renderer.py
from jinja2 import Template, Environment, FileSystemLoader
from pathlib import Path

def render_template(template_name: str, variables: dict) -> str:
    """
    Render Jinja2 template with variables.

    Args:
        template_name: Template file name (e.g., 'frankenwp/docker-compose.yml.j2')
        variables: Dictionary of template variables

    Returns:
        Rendered template as string
    """
    template_dir = Path(__file__).parent.parent / 'templates'
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_name)
    return template.render(**variables)

# Usage
variables = {
    'site_name': 'mysite',
    'domain': 'example.com',
    'db_name': 'wp_mysite',
    'db_user': 'wp_user',
    'db_password': 'SecurePassword123!'
}

output = render_template('frankenwp/docker-compose.yml.j2', variables)
```

### Variable Validation

```python
# cli/utils/validators.py
import re
from typing import Dict, List

def validate_variables(variables: Dict[str, str], template_type: str) -> List[str]:
    """
    Validate template variables.

    Args:
        variables: Dictionary of variables to validate
        template_type: 'frankenwp' or 'ols'

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Common validations
    if not re.match(r'^[a-z0-9_-]+$', variables.get('site_name', '')):
        errors.append("site_name must be lowercase alphanumeric with hyphens/underscores")

    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9-_.]+$', variables.get('domain', '')):
        errors.append("domain must be valid domain format")

    if len(variables.get('db_password', '')) < 20:
        errors.append("db_password must be at least 20 characters")

    # Template-specific validations
    if template_type == 'ols':
        if 'lsws_admin_pass' not in variables:
            errors.append("lsws_admin_pass is required for OLS template")

    return errors
```

## Testing Templates

### Unit Test Example

```python
# tests/test_templates.py
import pytest
from cli.utils.template_renderer import render_template

def test_frankenwp_template():
    variables = {
        'site_name': 'testsite',
        'domain': 'test.com',
        'db_name': 'wp_test',
        'db_user': 'wp_user',
        'db_password': 'SecurePassword123456789!'
    }

    output = render_template('frankenwp/docker-compose.yml.j2', variables)

    assert 'testsite_wp' in output
    assert 'test.com' in output
    assert 'wp_test' in output
    assert 'SecurePassword123456789!' in output

def test_ols_template():
    variables = {
        'site_name': 'testsite',
        'domain': 'test.com',
        'db_name': 'wp_test',
        'db_user': 'wp_user',
        'db_password': 'SecurePassword123456789!',
        'lsws_admin_pass': 'AdminPassword123456789!'
    }

    output = render_template('ols/docker-compose.yml.j2', variables)

    assert 'testsite_ols' in output
    assert 'testsite_redis' in output
    assert 'pma.test.com' in output
```

## Next Steps

Phase 03 will implement:
1. Python CLI to collect variables interactively
2. Variable validation and sanitization
3. Template rendering and deployment
4. Site management commands (start, stop, remove)
5. SSL certificate monitoring
6. Backup and restore commands
