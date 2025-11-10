"""GitHub API client for version checking and release management."""

import requests
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class GitHubRelease:
    """GitHub release information."""
    version: str
    tag_name: str
    name: str
    body: str
    published_at: datetime
    html_url: str
    prerelease: bool
    assets: List[Dict[str, Any]]

    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> "GitHubRelease":
        """Create GitHubRelease from GitHub API response."""
        # Remove 'v' prefix from tag_name to get version
        version = data['tag_name'].lstrip('v')

        return cls(
            version=version,
            tag_name=data['tag_name'],
            name=data['name'],
            body=data['body'],
            published_at=datetime.fromisoformat(data['published_at'].replace('Z', '+00:00')),
            html_url=data['html_url'],
            prerelease=data['prerelease'],
            assets=data.get('assets', [])
        )


class GitHubAPIError(Exception):
    """GitHub API related errors."""
    pass


class GitHubRateLimitError(GitHubAPIError):
    """GitHub API rate limit exceeded."""
    pass


class GitHubClient:
    """GitHub API client for VibeWP version management."""

    REPO_OWNER = "vibery-studio"
    REPO_NAME = "vibewp"
    BASE_URL = "https://api.github.com"

    # Cache settings
    CACHE_TTL = timedelta(minutes=5)

    def __init__(self, token: Optional[str] = None, timeout: int = 10):
        """
        Initialize GitHub client.

        Args:
            token: Optional GitHub personal access token for higher rate limits
            timeout: Request timeout in seconds (default: 10s)
        """
        self.token = token
        self.timeout = timeout
        self._cache: Dict[str, tuple[datetime, Any]] = {}

        # Setup session with headers
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': f'{self.REPO_NAME}-cli/1.0'
        })

        if token:
            self.session.headers['Authorization'] = f'token {token}'

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached response if not expired."""
        if key in self._cache:
            cached_time, data = self._cache[key]
            if datetime.now() - cached_time < self.CACHE_TTL:
                logger.debug(f"Using cached response for {key}")
                return data
        return None

    def _set_cache(self, key: str, data: Any) -> None:
        """Cache response with timestamp."""
        self._cache[key] = (datetime.now(), data)

    def _make_request(self, endpoint: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Make GitHub API request with error handling.

        Args:
            endpoint: API endpoint path
            use_cache: Whether to use cached response

        Returns:
            JSON response data

        Raises:
            GitHubRateLimitError: If rate limit exceeded
            GitHubAPIError: For other API errors
        """
        cache_key = f"request:{endpoint}"

        # Check cache first
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        url = f"{self.BASE_URL}{endpoint}"

        try:
            logger.debug(f"Making GitHub API request: {url}")
            response = self.session.get(url, timeout=self.timeout)

            # Check rate limit
            if response.status_code == 403:
                rate_limit_remaining = response.headers.get('X-RateLimit-Remaining', 'unknown')
                if rate_limit_remaining == '0':
                    reset_time = response.headers.get('X-RateLimit-Reset', 'unknown')
                    raise GitHubRateLimitError(
                        f"GitHub API rate limit exceeded. "
                        f"Resets at: {datetime.fromtimestamp(int(reset_time)) if reset_time != 'unknown' else 'unknown'}"
                    )
                raise GitHubAPIError(f"GitHub API forbidden (403): {response.text}")

            # Check for not found
            if response.status_code == 404:
                raise GitHubAPIError(f"GitHub resource not found (404): {endpoint}")

            # Raise for other errors
            response.raise_for_status()

            data = response.json()

            # Cache successful response
            if use_cache:
                self._set_cache(cache_key, data)

            return data

        except requests.exceptions.Timeout:
            raise GitHubAPIError(f"GitHub API request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise GitHubAPIError(f"Failed to connect to GitHub API: {e}")
        except requests.exceptions.RequestException as e:
            raise GitHubAPIError(f"GitHub API request failed: {e}")

    def get_latest_release(self, include_prerelease: bool = False) -> Optional[GitHubRelease]:
        """
        Get latest release from GitHub.

        Args:
            include_prerelease: If True, include pre-release versions

        Returns:
            GitHubRelease object or None if no releases found
        """
        try:
            if include_prerelease:
                # Get all releases and filter manually
                releases = self.get_all_releases()
                if not releases:
                    return None
                return releases[0]  # First is latest
            else:
                # Use GitHub's latest endpoint (excludes pre-releases)
                endpoint = f"/repos/{self.REPO_OWNER}/{self.REPO_NAME}/releases/latest"
                data = self._make_request(endpoint)
                return GitHubRelease.from_api_response(data)

        except GitHubAPIError as e:
            logger.error(f"Failed to fetch latest release: {e}")
            return None

    def get_all_releases(self, limit: int = 10) -> List[GitHubRelease]:
        """
        Get all releases from GitHub.

        Args:
            limit: Maximum number of releases to fetch

        Returns:
            List of GitHubRelease objects, sorted by published date (newest first)
        """
        try:
            endpoint = f"/repos/{self.REPO_OWNER}/{self.REPO_NAME}/releases?per_page={limit}"
            data = self._make_request(endpoint)

            releases = [GitHubRelease.from_api_response(release) for release in data]

            # Sort by published date, newest first
            releases.sort(key=lambda r: r.published_at, reverse=True)

            return releases

        except GitHubAPIError as e:
            logger.error(f"Failed to fetch releases: {e}")
            return []

    def get_release_by_tag(self, tag: str) -> Optional[GitHubRelease]:
        """
        Get specific release by tag.

        Args:
            tag: Release tag (e.g., 'v1.0.0' or '1.0.0')

        Returns:
            GitHubRelease object or None if not found
        """
        # Ensure tag has 'v' prefix for GitHub API
        if not tag.startswith('v'):
            tag = f'v{tag}'

        try:
            endpoint = f"/repos/{self.REPO_OWNER}/{self.REPO_NAME}/releases/tags/{tag}"
            data = self._make_request(endpoint)
            return GitHubRelease.from_api_response(data)

        except GitHubAPIError as e:
            logger.error(f"Failed to fetch release {tag}: {e}")
            return None

    def check_rate_limit(self) -> Dict[str, Any]:
        """
        Check current GitHub API rate limit status.

        Returns:
            Dict with rate limit information
        """
        try:
            endpoint = "/rate_limit"
            data = self._make_request(endpoint, use_cache=False)
            return data['rate']

        except GitHubAPIError as e:
            logger.error(f"Failed to check rate limit: {e}")
            return {'limit': 'unknown', 'remaining': 'unknown', 'reset': 'unknown'}
