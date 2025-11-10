"""Input validation functions for VibeWP CLI"""

import re
from typing import Optional
from pathlib import Path


def validate_site_name(name: str) -> tuple[bool, Optional[str]]:
    """
    Validate site name (alphanumeric, underscores, hyphens only)

    Args:
        name: Site name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Site name cannot be empty"

    if len(name) < 3:
        return False, "Site name must be at least 3 characters"

    if len(name) > 63:
        return False, "Site name must be less than 63 characters"

    if not re.match(r'^[a-z0-9][a-z0-9_-]*[a-z0-9]$', name):
        return False, "Site name must start and end with alphanumeric, contain only lowercase letters, numbers, underscores, and hyphens"

    # Reserved names
    reserved = ['test', 'admin', 'root', 'system', 'default', 'localhost']
    if name.lower() in reserved:
        return False, f"Site name '{name}' is reserved"

    return True, None


def validate_domain(domain: str) -> tuple[bool, Optional[str]]:
    """
    Validate domain name format

    Args:
        domain: Domain name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not domain:
        return False, "Domain cannot be empty"

    # Simple domain regex
    pattern = r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$'

    if not re.match(pattern, domain.lower()):
        return False, "Invalid domain format (e.g., example.com or sub.example.com)"

    # Check for at least one dot (require TLD)
    if '.' not in domain:
        return False, "Domain must include TLD (e.g., .com, .org)"

    # Check length
    if len(domain) > 253:
        return False, "Domain too long (max 253 characters)"

    # Check individual labels
    labels = domain.split('.')
    for label in labels:
        if len(label) > 63:
            return False, f"Domain label '{label}' too long (max 63 characters)"
        if not label or label.startswith('-') or label.endswith('-'):
            return False, f"Invalid domain label '{label}'"

    return True, None


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email address

    Args:
        email: Email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email cannot be empty"

    # Simple email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(pattern, email):
        return False, "Invalid email format (e.g., user@example.com)"

    if len(email) > 254:
        return False, "Email too long (max 254 characters)"

    # Check for @ symbol
    if email.count('@') != 1:
        return False, "Email must contain exactly one @ symbol"

    return True, None


def validate_port(port: int) -> tuple[bool, Optional[str]]:
    """
    Validate port number

    Args:
        port: Port number to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(port, int):
        return False, "Port must be an integer"

    if port < 1 or port > 65535:
        return False, "Port must be between 1 and 65535"

    # Check for privileged ports
    if port < 1024:
        return True, f"Warning: Port {port} is privileged (requires root)"

    return True, None


def validate_ip(ip: str) -> tuple[bool, Optional[str]]:
    """
    Validate IPv4 address

    Args:
        ip: IP address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not ip:
        return False, "IP address cannot be empty"

    # IPv4 regex
    pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
    match = re.match(pattern, ip)

    if not match:
        return False, "Invalid IPv4 format (e.g., 192.168.1.1)"

    # Check each octet
    for octet in match.groups():
        if int(octet) > 255:
            return False, f"IP octet {octet} exceeds 255"

    return True, None


def validate_path(path: str, must_exist: bool = False) -> tuple[bool, Optional[str]]:
    """
    Validate file/directory path

    Args:
        path: Path to validate
        must_exist: Whether path must exist

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path:
        return False, "Path cannot be empty"

    try:
        path_obj = Path(path).expanduser()

        if must_exist and not path_obj.exists():
            return False, f"Path does not exist: {path}"

        return True, None

    except Exception as e:
        return False, f"Invalid path: {e}"


def validate_wordpress_type(wp_type: str) -> tuple[bool, Optional[str]]:
    """
    Validate WordPress type

    Args:
        wp_type: WordPress type to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_types = ['frankenwp', 'ols', 'classic']

    if not wp_type:
        return False, "WordPress type cannot be empty"

    if wp_type.lower() not in valid_types:
        return False, f"Invalid WordPress type. Must be one of: {', '.join(valid_types)}"

    return True, None


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"

    if len(password) < 12:
        return False, "Password must be at least 12 characters"

    # Check for character variety
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)

    if not (has_lower and has_upper and has_digit and has_special):
        return False, "Password must contain uppercase, lowercase, digit, and special character"

    return True, None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing/replacing unsafe characters

    Args:
        filename: Filename to sanitize

    Returns:
        Sanitized filename
    """
    # Remove path separators and unsafe chars
    sanitized = re.sub(r'[\\/:*?"<>|]', '', filename)

    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')

    # Remove multiple consecutive underscores/hyphens
    sanitized = re.sub(r'[_-]+', '_', sanitized)

    # Remove leading/trailing underscores/hyphens
    sanitized = sanitized.strip('_-')

    # Ensure not empty
    if not sanitized:
        sanitized = "unnamed"

    return sanitized
