"""Doctor command for system health checks and diagnostics"""

import typer
import os
import subprocess
from pathlib import Path
from typing import List, Tuple
from cli.ui.console import print_success, print_error, print_info, print_warning

app = typer.Typer(help="System diagnostics and health checks")


class HealthCheck:
    """Individual health check"""
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.passed = False
        self.message = ""
        self.fix_suggestion = ""

    def success(self, message: str = ""):
        self.passed = True
        self.message = message or "OK"

    def fail(self, message: str, fix: str = ""):
        self.passed = False
        self.message = message
        self.fix_suggestion = fix


class DoctorChecker:
    """System health checker"""

    def __init__(self):
        self.checks: List[HealthCheck] = []
        self.categories = {
            "system": "System Requirements",
            "docker": "Docker Environment",
            "ssh": "SSH Configuration",
            "config": "VibeWP Configuration",
            "network": "Network & Connectivity",
            "permissions": "File Permissions"
        }

    def add_check(self, check: HealthCheck):
        """Add a health check"""
        self.checks.append(check)

    def run_all(self) -> Tuple[int, int]:
        """Run all health checks and return (passed, total)"""
        # System checks
        self.check_os()
        self.check_python()
        self.check_git()
        self.check_curl()

        # Docker checks
        self.check_docker_installed()
        self.check_docker_running()
        self.check_docker_compose()
        self.check_docker_network()
        self.check_caddy_proxy()

        # SSH checks
        self.check_ssh_service()
        self.check_ssh_key()
        self.check_ssh_connection()

        # Config checks
        self.check_config_exists()
        self.check_config_valid()
        self.check_install_dir()
        self.check_templates()

        # Network checks
        self.check_internet()
        self.check_dns()

        # Permission checks
        self.check_config_permissions()
        self.check_docker_permissions()

        passed = sum(1 for c in self.checks if c.passed)
        total = len(self.checks)
        return passed, total

    def check_os(self):
        """Check operating system"""
        check = HealthCheck("Operating System", "system")
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    content = f.read()
                    if "Ubuntu" in content:
                        # Extract version
                        for line in content.split('\n'):
                            if line.startswith('VERSION_ID'):
                                version = line.split('"')[1]
                                if version in ["22.04", "24.04"]:
                                    check.success(f"Ubuntu {version} LTS")
                                else:
                                    check.fail(
                                        f"Ubuntu {version} (unsupported)",
                                        "Install Ubuntu 22.04 or 24.04 LTS"
                                    )
                                break
                    else:
                        check.fail("Not Ubuntu", "VibeWP requires Ubuntu 22.04 or 24.04 LTS")
            else:
                check.fail("Cannot detect OS", "Ensure you're running Ubuntu")
        except Exception as e:
            check.fail(f"Error: {e}", "Check OS installation")
        self.add_check(check)

    def check_python(self):
        """Check Python version"""
        check = HealthCheck("Python Version", "system")
        try:
            result = subprocess.run(
                ["python3", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                check.success(version)
            else:
                check.fail("Python3 not found", "Install: apt-get install python3")
        except Exception as e:
            check.fail(f"Error: {e}", "Install: apt-get install python3")
        self.add_check(check)

    def check_git(self):
        """Check Git installation"""
        check = HealthCheck("Git", "system")
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                check.success(result.stdout.strip())
            else:
                check.fail("Git not found", "Install: apt-get install git")
        except Exception as e:
            check.fail(f"Error: {e}", "Install: apt-get install git")
        self.add_check(check)

    def check_curl(self):
        """Check curl installation"""
        check = HealthCheck("curl", "system")
        try:
            result = subprocess.run(
                ["curl", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.split('\n')[0]
                check.success(version)
            else:
                check.fail("curl not found", "Install: apt-get install curl")
        except Exception as e:
            check.fail(f"Error: {e}", "Install: apt-get install curl")
        self.add_check(check)

    def check_docker_installed(self):
        """Check if Docker is installed"""
        check = HealthCheck("Docker Installed", "docker")
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                check.success(version)
            else:
                check.fail(
                    "Docker not found",
                    "Install: curl -fsSL https://get.docker.com | sh"
                )
        except FileNotFoundError:
            check.fail(
                "Docker not found",
                "Install: curl -fsSL https://get.docker.com | sh"
            )
        except Exception as e:
            check.fail(f"Error: {e}", "Check Docker installation")
        self.add_check(check)

    def check_docker_running(self):
        """Check if Docker daemon is running"""
        check = HealthCheck("Docker Daemon", "docker")
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                check.success("Running")
            else:
                check.fail(
                    "Docker daemon not running",
                    "Start: systemctl start docker"
                )
        except Exception as e:
            check.fail(f"Error: {e}", "Start: systemctl start docker")
        self.add_check(check)

    def check_docker_compose(self):
        """Check Docker Compose"""
        check = HealthCheck("Docker Compose", "docker")
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                check.success(version)
            else:
                check.fail(
                    "Docker Compose not found",
                    "Install: apt-get install docker-compose-plugin"
                )
        except Exception as e:
            check.fail(f"Error: {e}", "Install: apt-get install docker-compose-plugin")
        self.add_check(check)

    def check_docker_network(self):
        """Check proxy network exists"""
        check = HealthCheck("Proxy Network", "docker")
        try:
            result = subprocess.run(
                ["docker", "network", "ls"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and "proxy" in result.stdout:
                check.success("Exists")
            else:
                check.fail(
                    "Proxy network missing",
                    "Create: docker network create proxy"
                )
        except Exception as e:
            check.fail(f"Error: {e}", "Create: docker network create proxy")
        self.add_check(check)

    def check_caddy_proxy(self):
        """Check if Caddy proxy is running"""
        check = HealthCheck("Caddy Proxy", "docker")
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and "caddy_proxy" in result.stdout:
                check.success("Running")
            else:
                check.fail(
                    "Caddy proxy not running",
                    "Deploy: cd /opt/vibewp && docker compose -f templates/caddy/docker-compose.yml up -d"
                )
        except Exception as e:
            check.fail(f"Error: {e}", "Deploy Caddy proxy")
        self.add_check(check)

    def check_ssh_service(self):
        """Check SSH service"""
        check = HealthCheck("SSH Service", "ssh")
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "ssh"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and "active" in result.stdout:
                check.success("Active")
            else:
                check.fail(
                    "SSH service not running",
                    "Start: systemctl start ssh"
                )
        except Exception as e:
            check.fail(f"Error: {e}", "Start: systemctl start ssh")
        self.add_check(check)

    def check_ssh_key(self):
        """Check SSH key exists"""
        check = HealthCheck("SSH Key", "ssh")
        key_path = Path.home() / ".ssh" / "id_rsa"
        if key_path.exists():
            check.success(f"Found at {key_path}")
        else:
            check.fail(
                "SSH key not found",
                "Generate: ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ''"
            )
        self.add_check(check)

    def check_ssh_connection(self):
        """Check SSH connection to localhost"""
        check = HealthCheck("SSH Localhost", "ssh")
        try:
            result = subprocess.run(
                ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
                 "localhost", "echo", "ok"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and "ok" in result.stdout:
                check.success("Connected")
            else:
                check.fail(
                    "Cannot connect to localhost",
                    "Add key: cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys"
                )
        except Exception as e:
            check.fail(f"Error: {e}", "Check SSH configuration")
        self.add_check(check)

    def check_config_exists(self):
        """Check config file exists"""
        check = HealthCheck("Config File", "config")
        config_path = Path.home() / ".vibewp" / "sites.yaml"
        if config_path.exists():
            check.success(f"Found at {config_path}")
        else:
            check.fail(
                "Config file missing",
                "Initialize: vibewp config init"
            )
        self.add_check(check)

    def check_config_valid(self):
        """Check config file is valid YAML"""
        check = HealthCheck("Config Valid", "config")
        config_path = Path.home() / ".vibewp" / "sites.yaml"
        if config_path.exists():
            try:
                import yaml
                with open(config_path) as f:
                    data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        check.success("Valid YAML")
                    else:
                        check.fail("Invalid config structure", "Check YAML syntax")
            except Exception as e:
                check.fail(f"Invalid YAML: {e}", "Fix YAML syntax errors")
        else:
            check.fail("Config file missing", "Initialize: vibewp config init")
        self.add_check(check)

    def check_install_dir(self):
        """Check installation directory"""
        check = HealthCheck("Install Directory", "config")
        install_dir = Path("/opt/vibewp")
        if install_dir.exists() and (install_dir / "cli").exists():
            check.success(f"Found at {install_dir}")
        else:
            check.fail(
                "Installation directory incomplete",
                "Reinstall: curl -fsSL https://raw.githubusercontent.com/vibery-studio/vibewp/main/install.sh | sudo bash"
            )
        self.add_check(check)

    def check_templates(self):
        """Check template directory"""
        check = HealthCheck("Templates", "config")
        template_dir = Path("/opt/vibewp/templates")
        if template_dir.exists():
            templates = list(template_dir.glob("**/*.yml"))
            check.success(f"Found {len(templates)} templates")
        else:
            check.fail("Template directory missing", "Reinstall VibeWP")
        self.add_check(check)

    def check_internet(self):
        """Check internet connectivity"""
        check = HealthCheck("Internet", "network")
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "5", "8.8.8.8"],
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                check.success("Connected")
            else:
                check.fail("No internet connection", "Check network configuration")
        except Exception as e:
            check.fail(f"Error: {e}", "Check network configuration")
        self.add_check(check)

    def check_dns(self):
        """Check DNS resolution"""
        check = HealthCheck("DNS Resolution", "network")
        try:
            result = subprocess.run(
                ["nslookup", "google.com"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                check.success("Working")
            else:
                check.fail("DNS resolution failed", "Check /etc/resolv.conf")
        except FileNotFoundError:
            # nslookup might not be installed, try alternative
            try:
                result = subprocess.run(
                    ["getent", "hosts", "google.com"],
                    capture_output=True,
                    timeout=10
                )
                if result.returncode == 0:
                    check.success("Working")
                else:
                    check.fail("DNS resolution failed", "Check /etc/resolv.conf")
            except Exception as e:
                check.fail(f"Error: {e}", "Install: apt-get install dnsutils")
        except Exception as e:
            check.fail(f"Error: {e}", "Check DNS configuration")
        self.add_check(check)

    def check_config_permissions(self):
        """Check config directory permissions"""
        check = HealthCheck("Config Permissions", "permissions")
        config_dir = Path.home() / ".vibewp"
        if config_dir.exists():
            stat_info = config_dir.stat()
            mode = oct(stat_info.st_mode)[-3:]
            if mode == "700":
                check.success("Correct (700)")
            else:
                check.fail(
                    f"Incorrect permissions ({mode})",
                    "Fix: chmod 700 ~/.vibewp"
                )
        else:
            check.fail("Config directory missing", "Create: mkdir -p ~/.vibewp && chmod 700 ~/.vibewp")
        self.add_check(check)

    def check_docker_permissions(self):
        """Check Docker socket permissions"""
        check = HealthCheck("Docker Socket", "permissions")
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                check.success("Accessible")
            else:
                check.fail(
                    "Cannot access Docker",
                    "Add user to docker group: usermod -aG docker $USER (logout required)"
                )
        except Exception as e:
            check.fail(f"Error: {e}", "Check Docker permissions")
        self.add_check(check)

    def print_report(self):
        """Print health check report"""
        print_info("\n=== VibeWP Health Check Report ===\n")

        # Group by category
        for cat_key, cat_name in self.categories.items():
            cat_checks = [c for c in self.checks if c.category == cat_key]
            if not cat_checks:
                continue

            print_info(f"\n{cat_name}:")
            for check in cat_checks:
                status = "✓" if check.passed else "✗"
                color_fn = print_success if check.passed else print_error

                # Print check result
                print(f"  [{status}] {check.name}: ", end="")
                color_fn(check.message)

                # Print fix suggestion if failed
                if not check.passed and check.fix_suggestion:
                    print_warning(f"      → {check.fix_suggestion}")

        # Summary
        passed, total = sum(1 for c in self.checks if c.passed), len(self.checks)
        print_info(f"\n{'='*50}")
        if passed == total:
            print_success(f"All checks passed! ({passed}/{total})")
        else:
            print_warning(f"Checks passed: {passed}/{total}")
            print_info(f"\nRun the suggested fixes above, then rerun: vibewp doctor")


@app.command()
def run():
    """Run comprehensive system health checks"""
    try:
        print_info("Running VibeWP diagnostics...\n")

        checker = DoctorChecker()
        checker.run_all()
        checker.print_report()

        # Exit code based on results
        passed, total = sum(1 for c in checker.checks if c.passed), len(checker.checks)
        if passed == total:
            raise typer.Exit(0)
        else:
            raise typer.Exit(1)

    except KeyboardInterrupt:
        print_info("\nDiagnostics cancelled")
        raise typer.Exit(1)
    except Exception as e:
        print_error(f"Error running diagnostics: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
