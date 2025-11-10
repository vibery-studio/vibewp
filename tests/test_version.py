"""Tests for version utilities."""

import pytest
from cli.utils.version import (
    SemanticVersion,
    parse_version,
    compare_versions,
    is_newer_version,
    version_to_tuple
)


class TestSemanticVersion:
    """Test SemanticVersion class."""

    def test_str_representation(self):
        """Test string representation."""
        v = SemanticVersion(1, 2, 3)
        assert str(v) == "1.2.3"

        v_pre = SemanticVersion(1, 2, 3, prerelease="beta")
        assert str(v_pre) == "1.2.3-beta"

        v_build = SemanticVersion(1, 2, 3, prerelease="beta", build="123")
        assert str(v_build) == "1.2.3-beta+123"

    def test_equality(self):
        """Test version equality."""
        v1 = SemanticVersion(1, 2, 3)
        v2 = SemanticVersion(1, 2, 3)
        v3 = SemanticVersion(1, 2, 4)

        assert v1 == v2
        assert v1 != v3

    def test_comparison(self):
        """Test version comparison."""
        v1 = SemanticVersion(1, 0, 0)
        v2 = SemanticVersion(2, 0, 0)
        v3 = SemanticVersion(1, 1, 0)
        v4 = SemanticVersion(1, 0, 1)

        assert v1 < v2
        assert v1 < v3
        assert v1 < v4
        assert v2 > v1
        assert v3 > v1

    def test_prerelease_comparison(self):
        """Test pre-release version comparison."""
        v1 = SemanticVersion(1, 0, 0, prerelease="alpha")
        v2 = SemanticVersion(1, 0, 0, prerelease="beta")
        v3 = SemanticVersion(1, 0, 0)

        # Pre-release is less than stable
        assert v1 < v3
        assert v2 < v3

        # Alpha < Beta
        assert v1 < v2


class TestParseVersion:
    """Test version parsing."""

    def test_parse_simple_version(self):
        """Test parsing simple version."""
        v = parse_version("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease is None

    def test_parse_with_v_prefix(self):
        """Test parsing version with 'v' prefix."""
        v = parse_version("v1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3

    def test_parse_with_prerelease(self):
        """Test parsing version with pre-release."""
        v = parse_version("1.2.3-beta")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease == "beta"

        v_rc = parse_version("1.2.3-rc.1")
        assert v_rc.prerelease == "rc.1"

    def test_parse_with_build(self):
        """Test parsing version with build metadata."""
        v = parse_version("1.2.3+build123")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.build == "build123"

    def test_parse_invalid_version(self):
        """Test parsing invalid version."""
        assert parse_version("invalid") is None
        assert parse_version("1.2") is None
        assert parse_version("1.2.3.4") is None
        assert parse_version("") is None


class TestCompareVersions:
    """Test version comparison."""

    def test_compare_equal_versions(self):
        """Test comparing equal versions."""
        assert compare_versions("1.0.0", "1.0.0") == 0
        assert compare_versions("v1.0.0", "1.0.0") == 0

    def test_compare_newer_version(self):
        """Test comparing newer version."""
        assert compare_versions("1.0.0", "2.0.0") == -1
        assert compare_versions("1.0.0", "1.1.0") == -1
        assert compare_versions("1.0.0", "1.0.1") == -1

    def test_compare_older_version(self):
        """Test comparing older version."""
        assert compare_versions("2.0.0", "1.0.0") == 1
        assert compare_versions("1.1.0", "1.0.0") == 1
        assert compare_versions("1.0.1", "1.0.0") == 1

    def test_compare_with_prerelease(self):
        """Test comparing versions with pre-release."""
        assert compare_versions("1.0.0-beta", "1.0.0") == -1
        assert compare_versions("1.0.0", "1.0.0-beta") == 1

    def test_compare_invalid_version(self):
        """Test comparing invalid versions."""
        with pytest.raises(ValueError):
            compare_versions("invalid", "1.0.0")

        with pytest.raises(ValueError):
            compare_versions("1.0.0", "invalid")


class TestIsNewerVersion:
    """Test is_newer_version utility."""

    def test_newer_version(self):
        """Test detecting newer version."""
        assert is_newer_version("1.0.0", "2.0.0") is True
        assert is_newer_version("1.0.0", "1.1.0") is True
        assert is_newer_version("1.0.0", "1.0.1") is True

    def test_not_newer_version(self):
        """Test detecting not newer version."""
        assert is_newer_version("1.0.0", "1.0.0") is False
        assert is_newer_version("2.0.0", "1.0.0") is False

    def test_invalid_version_returns_false(self):
        """Test invalid versions return False."""
        assert is_newer_version("invalid", "1.0.0") is False
        assert is_newer_version("1.0.0", "invalid") is False


class TestVersionToTuple:
    """Test version_to_tuple utility."""

    def test_version_to_tuple(self):
        """Test converting version to tuple."""
        assert version_to_tuple("1.0.0") == (1, 0, 0)
        assert version_to_tuple("v1.2.3") == (1, 2, 3)
        assert version_to_tuple("2.10.5") == (2, 10, 5)

    def test_version_to_tuple_ignores_prerelease(self):
        """Test tuple conversion ignores pre-release."""
        assert version_to_tuple("1.0.0-beta") == (1, 0, 0)

    def test_version_to_tuple_invalid(self):
        """Test tuple conversion with invalid version."""
        with pytest.raises(ValueError):
            version_to_tuple("invalid")
