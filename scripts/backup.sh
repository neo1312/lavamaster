#!/bin/bash
# Backup de bases de datos de Lavamaster (stage + prod) en el VPS.
# Programar en cron: 30 2 * * * /app/lavamaster/scripts/backup.sh >> /var/log/lavamaster_backup.log 2>&1
set -e

BACKUP_DIR="/backups/lavamaster"
STAMP=$(date +%Y%m%d_%H%M)
mkdir -p "$BACKUP_DIR"

backup_db() {
    local COMPOSE_DIR="$1"
    local COMPOSE_FILE="$2"
    local ENV_FILE="$3"
    local NAME="$4"

    cd "$COMPOSE_DIR"
    local CONTAINER=$(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps -q db)
    if [ -z "$CONTAINER" ]; then
        echo "[$STAMP] $NAME: db container not running, skipping"
        return
    fi

    # shellcheck disable=SC1090
    source "$ENV_FILE"
    docker exec "$CONTAINER" pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        | gzip > "$BACKUP_DIR/${NAME}_${STAMP}.sql.gz"
    echo "[$STAMP] $NAME: OK -> $BACKUP_DIR/${NAME}_${STAMP}.sql.gz"
}

backup_db /app/lavamaster_stage docker-compose.stage.yml .env.stage lavamaster_stage
backup_db /app/lavamaster docker-compose.prod.yml .env.prod lavamaster_prod

# Conservar últimos 14 días
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +14 -delete
