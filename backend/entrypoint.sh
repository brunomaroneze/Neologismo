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

# Tabela de cache usada pelo throttle do DRF. O comando é idempotente: se a
# tabela já existe, ele avisa e segue. Sem ela, cada worker do gunicorn
# contaria o rate limit por conta própria.
if [ "${DEBUG:-False}" != "True" ]; then
    python manage.py createcachetable

    # Coleta os estáticos do admin e do Swagger. Não é silenciado: se o
    # collectstatic quebrar, o admin sobe sem CSS e ninguém percebe.
    python manage.py collectstatic --noinput
fi

exec "$@"
