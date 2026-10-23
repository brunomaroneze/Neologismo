# --- Estágio 1: dependências ------------------------------------------------
# Instala os pacotes em um venv próprio para copiar só o resultado adiante,
# deixando o compilador e os headers de build fora da imagem final.
FROM python:3.13-slim AS dependencias

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


# --- Estágio 2: imagem final ------------------------------------------------
FROM python:3.13-slim AS final

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# postgresql-client fornece o pg_isready usado pelo entrypoint.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Usuário sem privilégios: um processo comprometido não vira root no container.
RUN useradd --create-home --shell /usr/sbin/nologin neoscopio

COPY --from=dependencias /opt/venv /opt/venv

WORKDIR /app
COPY --chown=neoscopio:neoscopio . .

# staticfiles/ e media/ precisam existir e pertencer ao usuário da aplicação,
# porque o collectstatic roda no start.
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R neoscopio:neoscopio /app/staticfiles /app/media \
    && chmod +x /app/entrypoint.sh

USER neoscopio

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
# Padrão de desenvolvimento; o compose de produção sobrescreve com gunicorn.
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
