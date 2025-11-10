"""Tests for GitHub API client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from cli.utils.github import (
    GitHubClient,
    GitHubRelease,
    GitHubAPIError,
    GitHubRateLimitError
)


class TestGitHubRelease:
    """Test GitHubRelease data class."""

    def test_from_api_response(self):
        """Test creating GitHubRelease from API response."""
        api_data = {
            'tag_name': 'v1.0.0',
            'name': 'Version 1.0.0',
            'body': 'Release notes here',
            'published_at': '2025-01-01T12:00:00Z',
            'html_url': 'https://github.com/vibery-studio/vibewp/releases/tag/v1.0.0',
            'prerelease': False,
            'assets': []
        }

        release = GitHubRelease.from_api_response(api_data)

        assert release.version == '1.0.0'  # 'v' prefix removed
        assert release.tag_name == 'v1.0.0'
        assert release.name == 'Version 1.0.0'
        assert release.prerelease is False

    def test_from_api_response_with_v_prefix(self):
        """Test version extraction removes 'v' prefix."""
        api_data = {
            'tag_name': 'v2.5.3',
            'name': 'Test',
            'body': 'Test',
            'published_at': '2025-01-01T12:00:00Z',
            'html_url': 'https://test.com',
            'prerelease': False,
            'assets': []
        }

        release = GitHubRelease.from_api_response(api_data)
        assert release.version == '2.5.3'


class TestGitHubClient:
    """Test GitHub API client."""

    def test_initialization(self):
        """Test client initialization."""
        client = GitHubClient()
        assert client.timeout == 10
        assert client.token is None

        client_with_token = GitHubClient(token='test_token')
        assert client_with_token.token == 'test_token'

    def test_initialization_with_custom_timeout(self):
        """Test client with custom timeout."""
        client = GitHubClient(timeout=30)
        assert client.timeout == 30

    @patch('cli.utils.github.requests.Session.get')
    def test_get_latest_release_success(self, mock_get):
        """Test getting latest release successfully."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tag_name': 'v1.0.0',
            'name': 'Version 1.0.0',
            'body': 'Release notes',
            'published_at': '2025-01-01T12:00:00Z',
            'html_url': 'https://github.com/vibery-studio/vibewp/releases/tag/v1.0.0',
            'prerelease': False,
            'assets': []
        }
        mock_response.headers = {}
        mock_get.return_value = mock_response

        client = GitHubClient()
        release = client.get_latest_release()

        assert release is not None
        assert release.version == '1.0.0'
        assert release.tag_name == 'v1.0.0'

    @patch('cli.utils.github.requests.Session.get')
    def test_get_latest_release_rate_limit(self, mock_get):
        """Test handling rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.headers = {
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': '1640000000'
        }
        mock_response.text = 'Rate limit exceeded'
        mock_get.return_value = mock_response

        client = GitHubClient()
        release = client.get_latest_release()

        # Should return None on error (logged internally)
        assert release is None

    @patch('cli.utils.github.requests.Session.get')
    def test_get_latest_release_not_found(self, mock_get):
        """Test handling 404 error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = 'Not found'
        mock_get.return_value = mock_response

        client = GitHubClient()
        release = client.get_latest_release()

        assert release is None

    @patch('cli.utils.github.requests.Session.get')
    def test_get_latest_release_timeout(self, mock_get):
        """Test handling timeout."""
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout()

        client = GitHubClient()
        release = client.get_latest_release()

        assert release is None

    @patch('cli.utils.github.requests.Session.get')
    def test_get_all_releases(self, mock_get):
        """Test getting all releases."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'tag_name': 'v1.1.0',
                'name': 'Version 1.1.0',
                'body': 'Latest',
                'published_at': '2025-02-01T12:00:00Z',
                'html_url': 'https://github.com/vibery-studio/vibewp/releases/tag/v1.1.0',
                'prerelease': False,
                'assets': []
            },
            {
                'tag_name': 'v1.0.0',
                'name': 'Version 1.0.0',
                'body': 'First',
                'published_at': '2025-01-01T12:00:00Z',
                'html_url': 'https://github.com/vibery-studio/vibewp/releases/tag/v1.0.0',
                'prerelease': False,
                'assets': []
            }
        ]
        mock_response.headers = {}
        mock_get.return_value = mock_response

        client = GitHubClient()
        releases = client.get_all_releases()

        assert len(releases) == 2
        # Should be sorted by date, newest first
        assert releases[0].version == '1.1.0'
        assert releases[1].version == '1.0.0'

    @patch('cli.utils.github.requests.Session.get')
    def test_get_release_by_tag(self, mock_get):
        """Test getting specific release by tag."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tag_name': 'v1.0.0',
            'name': 'Version 1.0.0',
            'body': 'Release notes',
            'published_at': '2025-01-01T12:00:00Z',
            'html_url': 'https://github.com/vibery-studio/vibewp/releases/tag/v1.0.0',
            'prerelease': False,
            'assets': []
        }
        mock_response.headers = {}
        mock_get.return_value = mock_response

        client = GitHubClient()
        release = client.get_release_by_tag('1.0.0')

        assert release is not None
        assert release.version == '1.0.0'

    @patch('cli.utils.github.requests.Session.get')
    def test_check_rate_limit(self, mock_get):
        """Test checking rate limit."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'rate': {
                'limit': 60,
                'remaining': 59,
                'reset': 1640000000
            }
        }
        mock_response.headers = {}
        mock_get.return_value = mock_response

        client = GitHubClient()
        rate_limit = client.check_rate_limit()

        assert rate_limit['limit'] == 60
        assert rate_limit['remaining'] == 59

    def test_caching(self):
        """Test response caching."""
        client = GitHubClient()

        # Set cache
        client._set_cache('test_key', {'data': 'value'})

        # Get from cache
        cached = client._get_cached('test_key')
        assert cached == {'data': 'value'}

    def test_cache_expiration(self):
        """Test cache expiration."""
        from datetime import timedelta
        client = GitHubClient()

        # Set cache with old timestamp
        old_time = datetime.now() - timedelta(minutes=10)
        client._cache['test_key'] = (old_time, {'data': 'value'})

        # Should return None for expired cache
        cached = client._get_cached('test_key')
        assert cached is None
