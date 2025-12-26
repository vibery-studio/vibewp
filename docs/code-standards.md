# VibeWP - Code Standards & Conventions

**Version**: 1.6.2 | **Last Updated**: 2025-12-25

## Overview

Coding standards for VibeWP ensure consistency, maintainability, and security across 50+ Python files and 30+ utility modules.

## Language & Runtime

- **Language**: Python 3.10+
- **Type Hints**: 100% coverage (mandatory)
- **Linting**: Enforced via pre-commit hooks
- **Formatting**: Black (88 char line length)

## Naming Conventions

### Files
- **Commands**: `site.py`, `domain.py`, `backup.py` (lowercase, underscores)
- **Utils**: `system_auditor.py`, `remote_backup.py` (descriptive, underscores)
- **Tests**: `test_backup.py`, `test_site.py` (test_ prefix)

### Classes
- **PascalCase**: `SiteManager`, `DockerOrchestrator`, `SecurityAuditor`
- **Suffixes**: `Manager`, `Handler`, `Auditor`, `Scanner`, `Generator`

### Functions/Methods
- **snake_case**: `create_site()`, `add_domain()`, `scan_malware()`
- **Verbs**: `get_`, `create_`, `delete_`, `list_`, `check_`, `scan_`, `validate_`
- **Boolean**: `is_running()`, `has_error()`, `can_delete()`

### Variables
- **snake_case**: `site_name`, `config_path`, `db_password`
- **Constants**: `UPPERCASE`: `DEFAULT_PHP_VERSION`, `MAX_DOMAIN_COUNT`
- **Config keys**: `snake_case` in YAML: `wpscan_api_token`, `install_method`

### Parameters/Arguments
- **Consistency**: Match config keys exactly
  - YAML: `install_method` → Param: `install_method` (not `install_type`)
  - YAML: `wpscan_api_token` → Param: `wpscan_api_token` (not `api_token`)

## Type Hints

### Mandatory
```python
# Command functions
@app.command()
def create_site(
    site_name: str,
    domain: str,
    wp_type: Literal["frankenwp", "ols"] = "frankenwp",
    admin_email: str = "",
) -> None:
    """Create WordPress site with type enforcement."""
    pass

# Utility functions
def get_site_info(site_name: str) -> dict[str, Any]:
    """Fetch site configuration from YAML."""
    pass

# Class methods
def add_domain(self, site_name: str, domain: str) -> bool:
    """Add domain with boolean success indicator."""
    pass

# Lists/Dicts
def list_sites() -> list[str]:
    """Return list of site names."""
    pass

def get_config() -> dict[str, Any]:
    """Return configuration dictionary."""
    pass
```

### Type Aliases (Pydantic)
```python
from pydantic import BaseModel

class SiteConfig(BaseModel):
    """Type-safe site configuration."""
    domain: str
    type: Literal["frankenwp", "ols"]
    status: Literal["running", "stopped"]
    created: str  # ISO timestamp
```

### Exceptions
```python
def delete_site(site_name: str) -> None:
    """Delete site with typed exceptions."""
    try:
        # operation
        pass
    except FileNotFoundError as e:
        raise RuntimeError(f"Config not found: {site_name}") from e
    except docker.errors.APIError as e:
        raise RuntimeError(f"Docker error: {e.explanation}") from e
```

## Code Organization

### Directory Structure
```
cli/
├── commands/           # Command entry points
│   ├── __init__.py     # Command app registration
│   ├── site.py         # @app.command() functions
│   ├── domain.py
│   └── backup.py
├── utils/              # Reusable utilities
│   ├── __init__.py     # Public exports
│   ├── docker.py       # Docker orchestration
│   ├── config.py       # Config management
│   └── validators.py   # Validation utilities
├── ui/                 # User interface
│   ├── console.py      # Rich formatting
│   └── menu.py         # Questionary menus
└── main.py             # CLI app initialization
```

### Command Structure
```python
# cli/commands/site.py
import typer
from pathlib import Path
from cli.utils.docker import DockerManager
from cli.utils.config import ConfigManager

app = typer.Typer(help="Manage WordPress sites")

@app.command()
def create(
    site_name: str = typer.Option(..., help="Site name (domain-like)"),
    domain: str = typer.Option(..., help="Primary domain"),
    wp_type: str = typer.Option("frankenwp", help="frankenwp|ols"),
) -> None:
    """Create new WordPress site."""
    config = ConfigManager()
    docker = DockerManager(config)
    # Implementation
    typer.echo(f"✅ Site {site_name} created")
```

### Utility Structure
```python
# cli/utils/docker.py
from typing import Any
from docker import client as docker_client
import docker.errors

class DockerManager:
    """Manages Docker containers and networks."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.client = docker_client.from_env()

    def create_network(self, network_name: str) -> None:
        """Create isolated Docker network."""
        try:
            self.client.networks.create(
                network_name,
                driver="bridge",
                check_duplicate=True,
            )
        except docker.errors.APIError as e:
            raise RuntimeError(f"Network creation failed: {e}") from e

    def get_container(self, container_name: str) -> Any:
        """Get container by name, typed as docker.models.containers.Container."""
        try:
            return self.client.containers.get(container_name)
        except docker.errors.NotFound as e:
            raise RuntimeError(f"Container not found: {container_name}") from e
```

## Configuration Management

### YAML Schema
```yaml
vps:
  host: "192.0.2.1"
  port: 22
  user: "root"
  key_path: "~/.ssh/id_rsa"
  install_method: "pip"
  wpscan_api_token: "optional"

sites:
  sitename:
    domain: "example.com"
    type: "frankenwp"
    status: "running"
    created: "2025-12-25T10:00:00Z"
    domains:
      - "www.example.com"
```

### Config Loading
```python
# cli/utils/config.py
import yaml
from pathlib import Path
from typing import Any

class ConfigManager:
    """Load/save configuration from ~/.vibewp/sites.yaml"""

    def __init__(self) -> None:
        self.config_path = Path.home() / ".vibewp" / "sites.yaml"

    def load(self) -> dict[str, Any]:
        """Load config with error handling."""
        if not self.config_path.exists():
            raise RuntimeError(
                f"Config not found: {self.config_path}\n"
                f"Run: vibewp config init"
            )

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f) or {}

        return config

    def save(self, config: dict[str, Any]) -> None:
        """Save config atomically with 0o600 permissions."""
        self.config_path.parent.mkdir(mode=0o700, exist_ok=True)

        # Atomic write
        temp_path = self.config_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        temp_path.chmod(0o600)
        temp_path.replace(self.config_path)
```

## Security Best Practices

### Credentials
```python
# Generate secure passwords
import secrets
import string

def generate_db_password(length: int = 32) -> str:
    """Generate cryptographically secure password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Store in config only
config['sites']['mysite']['db_password'] = generate_db_password()
```

### Permissions
```python
# Always use 0o600 for config files
config_path.chmod(0o600)

# Always use 0o700 for directories
config_dir.mkdir(mode=0o700, exist_ok=True)
```

### SSH Operations
```python
# Use Paramiko, never shell execution
import paramiko

def execute_command(host: str, command: str) -> str:
    """Execute SSH command safely."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username='root')

    try:
        stdin, stdout, stderr = client.exec_command(command)
        return stdout.read().decode()
    finally:
        client.close()
```

### No Secrets in Logs
```python
# Bad: logs password
logger.info(f"Password: {db_password}")

# Good: no sensitive data
logger.info(f"Database configured for {site_name}")

# Acceptable: redacted
logger.debug(f"DB pass: {db_password[:4]}****")
```

## Testing Standards

### Structure
```
tests/
├── unit/
│   ├── test_validators.py
│   ├── test_config.py
│   └── test_credentials.py
├── integration/
│   ├── test_site_creation.py
│   └── test_backup_restore.py
└── conftest.py  # Fixtures
```

### Test Format
```python
# tests/unit/test_validators.py
import pytest
from cli.utils.validators import validate_domain

class TestValidateDomain:
    """Test domain validation."""

    def test_valid_domain(self) -> None:
        """Valid domains pass validation."""
        assert validate_domain("example.com") is None

    def test_invalid_domain_no_tld(self) -> None:
        """Reject domain without TLD."""
        with pytest.raises(ValueError, match="Invalid domain"):
            validate_domain("example")

    def test_subdomain(self) -> None:
        """Accept subdomains."""
        assert validate_domain("blog.example.com") is None
```

### Coverage
- Minimum 80% for core utilities
- 100% for validators
- 50% for commands (integration tested)

## Error Handling

### Exception Hierarchy
```python
class VibeWPError(Exception):
    """Base exception for VibeWP."""
    pass

class ConfigError(VibeWPError):
    """Configuration file errors."""
    pass

class DockerError(VibeWPError):
    """Docker orchestration errors."""
    pass

class ValidationError(VibeWPError):
    """Input validation errors."""
    pass
```

### Error Messages
```python
# Bad: generic
raise RuntimeError("Error")

# Good: specific + actionable
raise ValidationError(
    f"Domain already exists: {domain}\n"
    f"Use: vibewp domain remove {site_name} {domain}"
)

# Good: context + suggestion
except docker.errors.APIError as e:
    raise DockerError(
        f"Failed to create container: {container_name}\n"
        f"Check: docker ps -a | grep {site_name}\n"
        f"Error: {e.explanation}"
    ) from e
```

## Documentation Standards

### Docstrings (Google Style)
```python
def create_site(
    site_name: str,
    domain: str,
    wp_type: str = "frankenwp",
) -> None:
    """Create new WordPress site.

    Deploys Docker containers (wp + db), generates credentials,
    adds domain to Caddy config, and initializes WordPress.

    Args:
        site_name: Unique identifier (alphanumeric, max 32 chars)
        domain: Primary domain (validates DNS before creation)
        wp_type: WordPress engine - "frankenwp" (default) or "ols"

    Raises:
        ValidationError: Invalid site_name or domain format
        ConfigError: Site already exists
        DockerError: Container creation failed
        RuntimeError: DNS validation failed

    Example:
        >>> create_site("myblog", "blog.example.com", "frankenwp")
        ✅ Site myblog created
        Admin: admin@example.com
        Password: (shown once)
    """
    pass
```

### Inline Comments
```python
# Use comments for "why", not "what"

# Bad
x = y + 1  # Add 1 to y

# Good
# Increment retry count after failed connection attempt
retry_count = previous_count + 1

# Acceptable: complex logic
# Check if domain is already in another site's domains list
# to prevent certificate collision in Caddy
if any(d == domain for site_domains in other_sites.values()):
    raise ValidationError(...)
```

## Imports

### Order
```python
# 1. Standard library
import os
import sys
from pathlib import Path
from typing import Any, Literal
import subprocess

# 2. Third-party
import typer
import yaml
from rich.console import Console
import docker

# 3. Local
from cli.utils.config import ConfigManager
from cli.utils.validators import validate_domain
```

### Avoid Star Imports
```python
# Bad
from cli.utils import *

# Good
from cli.utils.config import ConfigManager
from cli.utils.validators import validate_domain
```

## Constants

```python
# At module top level
DEFAULT_PHP_VERSION = "8.3"
DEFAULT_WP_TYPE = "frankenwp"
MAX_SITE_NAME_LENGTH = 32
MAX_DOMAIN_COUNT = 20
DOCKER_NETWORK_PREFIX = "vibewp_"
CADDY_CONFIG_DIR = "/etc/caddy/conf.d"
```

## Formatting

### Black Configuration
```toml
[tool.black]
line-length = 88
target-version = ['py310']
```

### Line Length
- **Soft limit**: 88 characters
- **Hard limit**: 100 characters for URLs/commands
- **Break**: Use parentheses, not backslashes

```python
# Good
command = (
    f"docker run -it {image_name} "
    f"--network={network_name} "
    f"--name={container_name}"
)

# Acceptable (long URL)
url = "https://raw.githubusercontent.com/vibery-studio/vibewp/main/install.sh"
```

## Async & Concurrency

### No Async
- VibeWP is synchronous (Typer runs sync)
- Use multiprocessing for parallel operations
- Keep I/O operations simple (SSH/Docker APIs are blocking)

### Parallel Backup
```python
from concurrent.futures import ThreadPoolExecutor

def upload_backup_to_s3(backup_path: Path, s3_key: str) -> None:
    """Upload backup to S3 with rclone."""
    pass

# Upload multiple backups in parallel
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(upload_backup_to_s3, path, key)
        for path, key in backups
    ]
    for future in futures:
        future.result()  # Wait + handle exceptions
```

## Logging

### Configure
```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Handler setup in main.py
handler = logging.FileHandler(Path.home() / ".vibewp" / "vibewp.log")
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
```

### Usage
```python
logger.info(f"Creating site: {site_name}")
logger.debug(f"Docker network: {network_name}")
logger.warning(f"Low disk space: {available_gb}GB remaining")
logger.error(f"SSH connection failed: {host}:{port}")
```

## Version Management

### Semantic Versioning
```
MAJOR.MINOR.PATCH

1.6.2 = Major(1) + Minor(6, breaking security fixes) + Patch(2, bug fixes)

- Major (1.0.0): Incompatible API changes
- Minor (0.1.0): Backward-compatible features
- Patch (0.0.1): Bug fixes
```

### Version File
```python
# cli/__init__.py
__version__ = "1.6.2"
```

## Git Commit Conventions

### Format
```
type(scope): subject

Body (optional)

Fixes: #123

type: feat|fix|refactor|test|docs|chore
scope: site|domain|security|backup|update
subject: lowercase, present tense, 50 chars max
```

### Examples
```
feat(site): add --skip-dns-validation flag
fix(backup): handle rclone timeout gracefully
refactor(security): consolidate audit commands
docs(readme): update installation instructions
test(site): add test for site creation with OLS
chore(deps): upgrade Typer to 0.13
```

## Code Review Checklist

- [ ] Type hints present (100% coverage)
- [ ] Docstrings complete (Args, Returns, Raises)
- [ ] Error messages actionable
- [ ] No secrets in code/logs
- [ ] Tests pass (pytest -v)
- [ ] Black formatting (black --check .)
- [ ] No unused imports
- [ ] Config keys match YAML schema
- [ ] Variable names consistent
- [ ] Security best practices followed

## Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.10

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
```

## Related Documentation

- **Architecture**: `system-architecture.md`
- **Project Overview**: `project-overview-pdr.md`
- **Codebase Summary**: `codebase-summary.md`
