#!/usr/bin/env sh
set -eu

DOMAIN="${1:-uni-guru.in}"
EMAIL="${2:-ops@uni-guru.in}"

docker compose run --rm certbot certonly \
  --webroot \
  -w /var/www/certbot \
  --email "${EMAIL}" \
  --agree-tos \
  --no-eff-email \
  -d "${DOMAIN}" \
  -d "www.${DOMAIN}"

docker compose exec nginx nginx -s reload
