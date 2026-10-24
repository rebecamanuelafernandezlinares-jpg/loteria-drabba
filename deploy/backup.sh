#!/bin/sh
# Respaldo diario de la base de datos. Guarda los últimos 14 días en ~/respaldos-loteria
set -e
cd "$(dirname "$0")/.."
mkdir -p ~/respaldos-loteria
docker compose exec -T db pg_dump -U loteria loteria | gzip > ~/respaldos-loteria/loteria-$(date +%F).sql.gz
find ~/respaldos-loteria -name 'loteria-*.sql.gz' -mtime +14 -delete
