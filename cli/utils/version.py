"""Version utilities for semantic versioning and comparison."""

from typing import Tuple, Optional
import re
from dataclasses import dataclass


@dataclass
class SemanticVersion:
    """Semantic version representation."""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    def __str__(self) -> str:
        """Return version string."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.build:
            version += f"+{self.build}"
        return version

    def __eq__(self, other) -> bool:
        """Check equality."""
        if not isinstance(other, SemanticVersion):
            return False
        return (
            self.major == other.major and
            self.minor == other.minor and
            self.patch == other.patch and
            self.prerelease == other.prerelease
        )

    def __lt__(self, other) -> bool:
        """Compare versions (less than)."""
        if not isinstance(other, SemanticVersion):
            return NotImplemented

        # Compare major.minor.patch
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

        # Handle pre-release comparison
        # No prerelease > prerelease (1.0.0 > 1.0.0-beta)
        if self.prerelease is None and other.prerelease is not None:
            return False
        if self.prerelease is not None and other.prerelease is None:
            return True

        # Both have prerelease, compare alphabetically
        if self.prerelease and other.prerelease:
            return self.prerelease < other.prerelease

        return False

    def __le__(self, other) -> bool:
        """Compare versions (less than or equal)."""
        return self == other or self < other

    def __gt__(self, other) -> bool:
        """Compare versions (greater than)."""
        return not self <= other

    def __ge__(self, other) -> bool:
        """Compare versions (greater than or equal)."""
        return not self < other


def parse_version(version_str: str) -> Optional[SemanticVersion]:
    """
    Parse version string into SemanticVersion object.

    Supports formats:
    - 1.0.0
    - v1.0.0
    - 1.0.0-beta
    - 1.0.0-rc.1
    - 1.0.0+build123

    Args:
        version_str: Version string to parse

    Returns:
        SemanticVersion object or None if invalid
    """
    # Remove 'v' prefix if present
    version_str = version_str.strip().lstrip('v')

    # Regex pattern for semantic versioning
    # Matches: major.minor.patch[-prerelease][+build]
    pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$'

    match = re.match(pattern, version_str)
    if not match:
        return None

    major, minor, patch, prerelease, build = match.groups()

    return SemanticVersion(
        major=int(major),
        minor=int(minor),
        patch=int(patch),
        prerelease=prerelease,
        build=build
    )


def compare_versions(version1: str, version2: str) -> int:
    """
    Compare two version strings.

    Args:
        version1: First version string
        version2: Second version string

    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2

    Raises:
        ValueError: If version strings are invalid
    """
    v1 = parse_version(version1)
    v2 = parse_version(version2)

    if v1 is None:
        raise ValueError(f"Invalid version string: {version1}")
    if v2 is None:
        raise ValueError(f"Invalid version string: {version2}")

    if v1 < v2:
        return -1
    elif v1 > v2:
        return 1
    else:
        return 0


def is_newer_version(current: str, latest: str) -> bool:
    """
    Check if latest version is newer than current.

    Args:
        current: Current version string
        latest: Latest version string

    Returns:
        True if latest > current, False otherwise
    """
    try:
        return compare_versions(current, latest) < 0
    except ValueError:
        # If comparison fails, assume not newer
        return False


def version_to_tuple(version_str: str) -> Tuple[int, int, int]:
    """
    Convert version string to tuple for comparison.

    Args:
        version_str: Version string (e.g., "1.0.0")

    Returns:
        Tuple of (major, minor, patch)

    Raises:
        ValueError: If version string is invalid
    """
    v = parse_version(version_str)
    if v is None:
        raise ValueError(f"Invalid version string: {version_str}")
    return (v.major, v.minor, v.patch)
