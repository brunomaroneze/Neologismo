#!/bin/sh
set -e

# Aguarda o Postgres ficar disponível antes de subir o Django.
if [ -n "$POSTGRES_HOST" ]; then
    echo "Aguardando o Postgres em $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
    tentativas=0
    until pg_isready -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -q; do
        tentativas=$((tentativas + 1))
        if [ "$tentativas" -ge 60 ]; then
            echo "Postgres não respondeu em 60s. Abortando." >&2
            exit 1
        fi
        sleep 1
    done
    echo "Postgres disponível."
fi

# Aplica as migrações. Falhar aqui precisa derrubar o start: subir a aplicação
# com o schema defasado causa erros 500 difíceis de diagnosticar.
python manage.py migrate --noinput

# Coleta os estáticos do admin e do Swagger. Também não é mais silenciado:
# se o collectstatic quebrar, o admin sobe sem CSS e ninguém percebe.
if [ "${DEBUG:-False}" != "True" ]; then
    python manage.py collectstatic --noinput
fi

exec "$@"
