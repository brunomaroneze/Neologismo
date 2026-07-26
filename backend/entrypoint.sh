#!/bin/sh
set -e

# Aguarda o Postgres ficar disponível antes de subir o Django
if [ -n "$POSTGRES_HOST" ]; then
    echo "Aguardando o Postgres em $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
    until pg_isready -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -q; do
        sleep 1
    done
    echo "Postgres disponivel."
fi

# Aplica migrações e coleta estáticos
python manage.py migrate --noinput
python manage.py collectstatic --noinput 2>/dev/null || true

# Executa o comando do container (runserver em dev, gunicorn em prod)
exec "$@"
