# VibeWP FrankenPHP WordPress Image
# Based on official dunglas/frankenphp-wordpress pattern
FROM dunglas/frankenphp:latest-php8.3

# Install WordPress required PHP extensions
RUN install-php-extensions \
    bcmath \
    exif \
    gd \
    intl \
    mysqli \
    zip \
    imagick \
    opcache

# Copy PHP config and WordPress from official image
COPY --from=wordpress:latest /usr/local/etc/php/conf.d/* /usr/local/etc/php/conf.d/
COPY --from=wordpress:latest /usr/local/bin/docker-entrypoint.sh /usr/local/bin/
COPY --from=wordpress:latest --chown=www-data:www-data /usr/src/wordpress /usr/src/wordpress

WORKDIR /var/www/html

# Set ownership for Caddy data directories
RUN chown -R www-data:www-data /data/caddy && \
    chown -R www-data:www-data /config/caddy

# Modify WordPress entrypoint for FrankenPHP compatibility
RUN sed -i \
    -e 's/\[ "$1" = '\''php-fpm'\'' \]/\[\[ "$1" == frankenphp* \]\]/g' \
    -e 's/php-fpm/frankenphp/g' \
    /usr/local/bin/docker-entrypoint.sh

# Create Caddyfile for WordPress
RUN cat > /etc/caddy/Caddyfile << 'CADDYEOF'
{
    frankenphp
    order php_server before file_server
    auto_https off
}

:80 {
    root * /var/www/html
    encode gzip

    php_server
}
CADDYEOF

# WordPress data volume
VOLUME /var/www/html

# Run as www-data for security
USER www-data

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["frankenphp", "run", "--config", "/etc/caddy/Caddyfile"]
