#!/bin/bash
set -e

ENV="${1:-local}"
COMMIT_MSG="${2:-deploy lavamaster}"

VPS_HOST="root@5.75.162.179"
VPS_STAGE_DIR="/app/lavamaster_stage"
VPS_PROD_DIR="/app/lavamaster"

case $ENV in
    local)
        source venv/bin/activate
        python manage.py makemigrations
        python manage.py migrate
        python manage.py runserver 0.0.0.0:8000
        ;;

    stage)
        echo "Starting staging deployment ..."
        git add .
        git commit -m "$COMMIT_MSG" --allow-empty
        git push
        ssh "$VPS_HOST" <<EOF
cd "$VPS_STAGE_DIR"
git pull
docker compose -f docker-compose.stage.yml --env-file .env.stage down
docker compose -f docker-compose.stage.yml --env-file .env.stage up --build -d --remove-orphans
docker compose -f docker-compose.stage.yml --env-file .env.stage ps
EOF
        echo "Staging deployment completed"
        ;;

    prod)
        echo "Starting production deployment..."
        git add .
        git commit -m "$COMMIT_MSG" --allow-empty
        git push
        ssh "$VPS_HOST" <<EOF
cd "$VPS_PROD_DIR"
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod down
docker compose -f docker-compose.prod.yml --env-file .env.prod up --build -d --remove-orphans
docker compose -f docker-compose.prod.yml --env-file .env.prod ps
EOF
        echo "Production deployment completed"
        ;;

    *)
        echo "Usage: $0 {local|stage|prod} [commit_message]"
        exit 1
        ;;
esac
