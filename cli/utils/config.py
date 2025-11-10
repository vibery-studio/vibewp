"""Configuration management for VibeWP CLI"""

import os
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class VPSConfig(BaseModel):
    """VPS connection configuration"""
    host: str
    port: int = 22
    user: str
    key_path: str
    wpscan_api_token: Optional[str] = None

    @validator('port')
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v


class WordPressConfig(BaseModel):
    """WordPress default settings"""
    default_admin_email: str = "admin@example.com"
    default_timezone: str = "UTC"
    default_locale: str = "en_US"


class DockerConfig(BaseModel):
    """Docker configuration"""
    base_path: str = "/opt/vibewp"
    network_name: str = "proxy"


class SiteConfig(BaseModel):
    """Individual site configuration"""
    name: str
    domain: str
    type: str  # frankenwp, ols, etc.
    status: str = "running"
    domains: List[str] = Field(default_factory=list)  # Additional domains
    created: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Site name must be alphanumeric with underscores/hyphens')
        return v

    @validator('domains', pre=True, always=True)
    def ensure_domains_list(cls, v, values):
        """Ensure domains list includes primary domain"""
        if not isinstance(v, list):
            v = []
        # If domains is empty, initialize with primary domain
        if not v and 'domain' in values:
            v = [values['domain']]
        return v


class VibeWPConfig(BaseModel):
    """Root configuration model"""
    vps: VPSConfig
    wordpress: WordPressConfig = Field(default_factory=WordPressConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    sites: List[SiteConfig] = Field(default_factory=list)


class ConfigManager:
    """Manages VibeWP configuration files"""

    DEFAULT_CONFIG_DIR = Path.home() / ".vibewp"
    DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "sites.yaml"
    DEV_CONFIG_FILE = Path(__file__).parent.parent.parent / ".vibewp-dev.yaml"

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_FILE
        self.config_dir = self.config_path.parent
        self._config: Optional[VibeWPConfig] = None

    def init_config(self) -> None:
        """Initialize configuration directory and file"""
        # Create config directory
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # If config doesn't exist, try to load from dev config
        if not self.config_path.exists():
            if self.DEV_CONFIG_FILE.exists():
                # Load dev config as template
                with open(self.DEV_CONFIG_FILE, 'r') as f:
                    dev_data = yaml.safe_load(f)

                # Create initial config from dev config
                config_data = {
                    'vps': dev_data.get('vps', {}),
                    'wordpress': {
                        'default_admin_email': 'admin@example.com',
                        'default_timezone': 'UTC',
                        'default_locale': 'en_US'
                    },
                    'docker': {
                        'base_path': '/opt/vibewp',
                        'network_name': 'proxy'
                    },
                    'sites': []
                }
            else:
                # Create minimal config
                config_data = {
                    'vps': {
                        'host': '0.0.0.0',
                        'port': 22,
                        'user': 'root',
                        'key_path': '~/.ssh/id_rsa'
                    },
                    'wordpress': {
                        'default_admin_email': 'admin@example.com',
                        'default_timezone': 'UTC',
                        'default_locale': 'en_US'
                    },
                    'docker': {
                        'base_path': '/opt/vibewp',
                        'network_name': 'proxy'
                    },
                    'sites': []
                }

            # Save initial config
            with open(self.config_path, 'w') as f:
                yaml.safe_dump(config_data, f, default_flow_style=False, sort_keys=False)

            # Set permissions to 600
            os.chmod(self.config_path, 0o600)

    def load_config(self) -> VibeWPConfig:
        """Load and validate configuration"""
        if not self.config_path.exists():
            self.init_config()

        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)

        self._config = VibeWPConfig(**data)
        return self._config

    def save_config(self, config: Optional[VibeWPConfig] = None) -> None:
        """Save configuration atomically"""
        if config:
            self._config = config

        if not self._config:
            raise ValueError("No configuration to save")

        # Atomic write: write to temp file, then rename
        temp_path = self.config_path.with_suffix('.tmp')

        with open(temp_path, 'w') as f:
            yaml.safe_dump(
                self._config.model_dump(),
                f,
                default_flow_style=False,
                sort_keys=False
            )

        # Set permissions before rename
        os.chmod(temp_path, 0o600)

        # Atomic rename
        temp_path.rename(self.config_path)

    def get_sites(self) -> List[SiteConfig]:
        """Get list of all sites"""
        if not self._config:
            self.load_config()
        return self._config.sites

    def add_site(self, site: SiteConfig) -> None:
        """Add a new site to registry"""
        if not self._config:
            self.load_config()

        # Check for duplicate site name
        if any(s.name == site.name for s in self._config.sites):
            raise ValueError(f"Site '{site.name}' already exists")

        self._config.sites.append(site)
        self.save_config()

    def remove_site(self, site_name: str) -> bool:
        """Remove a site from registry"""
        if not self._config:
            self.load_config()

        initial_count = len(self._config.sites)
        self._config.sites = [s for s in self._config.sites if s.name != site_name]

        if len(self._config.sites) < initial_count:
            self.save_config()
            return True
        return False

    def get_site(self, site_name: str) -> Optional[SiteConfig]:
        """Get a specific site by name"""
        if not self._config:
            self.load_config()

        for site in self._config.sites:
            if site.name == site_name:
                return site
        return None

    def site_exists(self, site_name: str) -> bool:
        """Check if a site exists"""
        return self.get_site(site_name) is not None

    def update_site_status(self, site_name: str, status: str) -> bool:
        """Update site status"""
        site = self.get_site(site_name)
        if site:
            site.status = status
            self.save_config()
            return True
        return False

    @property
    def vps(self) -> VPSConfig:
        """Get VPS configuration"""
        if not self._config:
            self.load_config()
        return self._config.vps

    @property
    def wordpress(self) -> WordPressConfig:
        """Get WordPress configuration"""
        if not self._config:
            self.load_config()
        return self._config.wordpress

    @property
    def docker(self) -> DockerConfig:
        """Get Docker configuration"""
        if not self._config:
            self.load_config()
        return self._config.docker

    def get_vps_ip(self) -> str:
        """Get VPS IP address"""
        if not self._config:
            self.load_config()
        return self._config.vps.host

    def add_domain_to_site(self, site_name: str, domain: str) -> bool:
        """
        Add domain to site in config

        Args:
            site_name: Site name
            domain: Domain to add

        Returns:
            True if domain was added, False if already exists
        """
        site = self.get_site(site_name)
        if not site:
            raise ValueError(f"Site '{site_name}' not found")

        # Ensure domains list exists
        if not hasattr(site, 'domains') or site.domains is None:
            site.domains = [site.domain]

        # Check if domain already exists
        if domain in site.domains:
            return False

        # Add domain
        site.domains.append(domain)
        self.save_config()
        return True

    def remove_domain_from_site(self, site_name: str, domain: str) -> bool:
        """
        Remove domain from site in config

        Args:
            site_name: Site name
            domain: Domain to remove

        Returns:
            True if domain was removed, False if not found
        """
        site = self.get_site(site_name)
        if not site:
            raise ValueError(f"Site '{site_name}' not found")

        # Ensure domains list exists
        if not hasattr(site, 'domains') or site.domains is None:
            site.domains = [site.domain]

        # Check if domain exists
        if domain not in site.domains:
            return False

        # Don't allow removing the last domain
        if len(site.domains) == 1:
            raise ValueError("Cannot remove the last domain from site")

        # Remove domain
        site.domains.remove(domain)
        self.save_config()
        return True

    def update_site_primary_domain(self, site_name: str, new_primary: str) -> bool:
        """
        Update site's primary domain

        Args:
            site_name: Site name
            new_primary: New primary domain

        Returns:
            True if updated successfully
        """
        site = self.get_site(site_name)
        if not site:
            raise ValueError(f"Site '{site_name}' not found")

        # Ensure domains list exists
        if not hasattr(site, 'domains') or site.domains is None:
            site.domains = [site.domain]

        # Check if new primary is in domains list
        if new_primary not in site.domains:
            raise ValueError(f"Domain '{new_primary}' not found in site domains")

        # Update primary domain
        site.domain = new_primary
        self.save_config()
        return True

    def get_site_domains(self, site_name: str) -> List[str]:
        """
        Get all domains for a site

        Args:
            site_name: Site name

        Returns:
            List of domains
        """
        site = self.get_site(site_name)
        if not site:
            raise ValueError(f"Site '{site_name}' not found")

        # Ensure domains list exists
        if not hasattr(site, 'domains') or site.domains is None:
            return [site.domain]

        return site.domains

    def get_wpscan_token(self) -> Optional[str]:
        """
        Get WPScan API token from configuration

        Returns:
            WPScan API token or None if not configured
        """
        if not self._config:
            self.load_config()
        return self._config.vps.wpscan_api_token

    def set_wpscan_token(self, token: str) -> None:
        """
        Set WPScan API token in configuration

        Args:
            token: WPScan API token

        Note:
            Token is stored securely in config file with 600 permissions
        """
        if not self._config:
            self.load_config()

        self._config.vps.wpscan_api_token = token
        self.save_config()

    def clear_wpscan_token(self) -> None:
        """Clear WPScan API token from configuration"""
        if not self._config:
            self.load_config()

        self._config.vps.wpscan_api_token = None
        self.save_config()
