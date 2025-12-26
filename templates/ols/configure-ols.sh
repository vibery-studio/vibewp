#!/bin/bash
set -e

DOMAIN="${DOMAIN:-localhost}"
VHOST_ROOT="/var/www/vhosts/${DOMAIN}"

echo "[OLS Config] Configuring OpenLiteSpeed for domain: ${DOMAIN}"

# Wait for config volume to be ready
if [ ! -d "/usr/local/lsws/conf" ]; then
    echo "[OLS Config] Waiting for conf directory..."
    sleep 2
fi

# Create vhost directory structure if it doesn't exist
mkdir -p "${VHOST_ROOT}/logs"
chown -R nobody:nogroup "${VHOST_ROOT}" 2>/dev/null || true

# Configure vhost if not already configured
VHOST_CONF_DIR="/usr/local/lsws/conf/vhosts/${DOMAIN}"
if [ ! -f "${VHOST_CONF_DIR}/vhconf.conf" ]; then
    echo "[OLS Config] Creating vhost configuration for ${DOMAIN}..."

    mkdir -p "${VHOST_CONF_DIR}"

    # Copy template and replace variables
    if [ -f "/tmp/vhconf.conf.template" ]; then
        sed "s|\$VH_ROOT|${VHOST_ROOT}|g" /tmp/vhconf.conf.template > "${VHOST_CONF_DIR}/vhconf.conf"
    else
        echo "[OLS Config] WARNING: vhconf.conf.template not found, using basic config"
        cat > "${VHOST_CONF_DIR}/vhconf.conf" <<EOF
docRoot                   ${VHOST_ROOT}
enableGzip                1

context / {
  allowBrowse             1
  location                ${VHOST_ROOT}/
  rewrite  {
    RewriteFile           .htaccess
  }
}

index {
  indexFiles              index.php, index.html
  autoIndex               0
}

rewrite {
  enable                  1
  logLevel                0
}
EOF
    fi

    echo "[OLS Config] Vhost configuration created"
fi

# Update httpd_config.conf to add our vhost
HTTPD_CONF="/usr/local/lsws/conf/httpd_config.conf"
if ! grep -q "virtualHost ${DOMAIN}" "${HTTPD_CONF}" 2>/dev/null; then
    echo "[OLS Config] Adding virtualHost to httpd_config.conf..."

    # Backup original
    cp "${HTTPD_CONF}" "${HTTPD_CONF}.bak"

    # Add virtualHost block before the first listener or at the end
    cat >> "${HTTPD_CONF}" <<EOF

virtualHost ${DOMAIN} {
  vhRoot                  ${VHOST_ROOT}
  configFile              conf/vhosts/${DOMAIN}/vhconf.conf
  allowSymbolLink         1
  enableScript            1
  restrained              0
  setUIDMode              0
}
EOF

    echo "[OLS Config] VirtualHost added"
fi

# Update listeners to map to our vhost
if ! grep -q "map.*${DOMAIN}" "${HTTPD_CONF}" 2>/dev/null; then
    echo "[OLS Config] Updating listener mappings..."

    # Replace "map Example *" with our domain in Default listener
    sed -i.bak2 "s/map.*Example \*/map ${DOMAIN} */g" "${HTTPD_CONF}"

    # Update docker template member if it exists
    if grep -q "member localhost" "${HTTPD_CONF}"; then
        sed -i.bak3 "s/vhDomain.*localhost.*/vhDomain ${DOMAIN}, */" "${HTTPD_CONF}"
        sed -i.bak4 "s/member localhost/member ${DOMAIN}/" "${HTTPD_CONF}"
    fi

    echo "[OLS Config] Listener mappings updated"
fi

echo "[OLS Config] Configuration complete for ${DOMAIN}"
echo "[OLS Config] Document root: ${VHOST_ROOT}"

# Start LiteSpeed using the original entrypoint
exec /entrypoint.sh "$@"
