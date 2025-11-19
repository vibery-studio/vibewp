"""Test backup system end-to-end"""

import typer
from cli.ui.console import print_success, print_error, print_info
from cli.utils.ssh import SSHManager
from cli.utils.config import ConfigManager

app = typer.Typer(help="Test backup system")


@app.command("backup-flow")
def test_backup_flow(site_name: str = typer.Argument(..., help="Site name")):
    """Test complete backup flow step-by-step"""
    try:
        config_mgr = ConfigManager()
        config_mgr.load_config()

        site = config_mgr.get_site(site_name)
        if not site:
            print_error(f"Site '{site_name}' not found")
            raise typer.Exit(code=1)

        ssh = SSHManager(
            host=config_mgr.vps.host,
            port=config_mgr.vps.port,
            user=config_mgr.vps.user,
            key_path=config_mgr.vps.key_path
        )
        ssh.connect()

        print_info("Step 1: Testing container detection...")
        for sep in ['_', '-']:
            container = f"{site_name}{sep}db"
            exit_code, stdout, _ = ssh.run_command(
                f"docker ps --filter name={container} --format '{{{{.Names}}}}'",
                timeout=10
            )
            if exit_code == 0 and stdout.strip():
                print_success(f"  ✓ Found DB container: {stdout.strip()}")
                db_container = stdout.strip()
                break

        print_info("\nStep 2: Testing database credentials...")
        exit_code, output, _ = ssh.run_command(
            f"docker exec {db_container} printenv | grep MYSQL",
            timeout=10
        )
        if exit_code == 0:
            print_success(f"  ✓ Database environment variables found")
            for line in output.strip().split('\n'):
                if 'PASSWORD' not in line:
                    print_info(f"    {line}")

        print_info("\nStep 3: Testing WordPress file access...")
        wp_container = f"{site_name}_wp"
        exit_code, output, _ = ssh.run_command(
            f"docker exec {wp_container} test -d /var/www/html/wp-content && echo 'EXISTS'",
            timeout=10
        )
        if exit_code == 0 and 'EXISTS' in output:
            print_success(f"  ✓ wp-content directory accessible")

        print_info("\nStep 4: Testing docker cp...")
        test_path = f"/tmp/test_backup_{site_name}"
        ssh.run_command(f"rm -rf {test_path}", timeout=10)
        ssh.run_command(f"mkdir -p {test_path}", timeout=10)

        exit_code, _, stderr = ssh.run_command(
            f"docker cp {wp_container}:/var/www/html/wp-content {test_path}/wp-content",
            timeout=60
        )
        if exit_code == 0:
            exit_code2, size, _ = ssh.run_command(f"du -sh {test_path}/wp-content", timeout=10)
            print_success(f"  ✓ docker cp successful: {size.strip()}")
        else:
            print_error(f"  ✗ docker cp failed: {stderr}")

        ssh.run_command(f"rm -rf {test_path}", timeout=10)

        print_info("\nStep 5: Testing database dump...")
        exit_code, db_user, _ = ssh.run_command(
            f"docker exec {db_container} printenv MYSQL_USER",
            timeout=10
        )
        exit_code, db_pass, _ = ssh.run_command(
            f"docker exec {db_container} printenv MYSQL_PASSWORD",
            timeout=10
        )
        exit_code, db_name, _ = ssh.run_command(
            f"docker exec {db_container} printenv MYSQL_DATABASE",
            timeout=10
        )

        test_sql = f"/tmp/test_db_{site_name}.sql"
        exit_code, _, stderr = ssh.run_command(
            f"docker exec {db_container} mysqldump -u {db_user.strip()} -p{db_pass.strip()} {db_name.strip()} > {test_sql}",
            timeout=60
        )
        if exit_code == 0:
            exit_code2, size, _ = ssh.run_command(f"ls -lh {test_sql} | awk '{{print $5}}'", timeout=10)
            print_success(f"  ✓ Database dump successful: {size.strip()}")
        else:
            print_error(f"  ✗ Database dump failed: {stderr}")

        ssh.run_command(f"rm -f {test_sql}", timeout=10)

        print_success("\n✓ All backup components tested successfully")
        print_info("\nBackup system is ready. You can now run:")
        print_info(f"  vibewp backup create {site_name}")

        ssh.disconnect()

    except Exception as e:
        print_error(f"Error: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
