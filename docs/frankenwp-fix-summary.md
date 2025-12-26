# FrankenWP SSL and Permission Fix Summary

## Issues Found

1. **SSL/TLS Error**: MariaDB client requires SSL disabled via `MYSQL_HOME=/tmp` + creating `/tmp/my.cnf` with `[client]\nssl=0`
2. **Permission Error**: `wp config create` has PHP file_put_contents() bug - workaround: manually copy wp-config-sample.php then use `wp config set`

## Template Changes

File: `templates/frankenwp/docker-compose.yml.j2`

### wordpress container
Added `MYSQL_SSL: "false"` env var

### wpcli container
- Removed `user: "33:33"` constraint to allow `-u root`
- Added `MYSQL_HOME: /tmp` env var
- Changed command to create `/tmp/my.cnf` with SSL disabled

## Code Changes Needed

File: `cli/utils/wordpress.py` line 95-106

Replace `wp config create` command with:
1. Copy wp-config-sample.php to wp-config.php
2. Use `wp config set` for each DB constant (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST)

This handles special characters in passwords safely.

## Verification

Site created successfully:
- URL: https://site-7.wptest.vibery.app
- HTTP: 200 OK
- Title: "FrankenWP Test" ✓
