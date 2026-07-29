# Neoscopio

Projeto com backend Django + frontend Next.js + Postgres, orquestrado por Docker Compose.

## Subir com Docker

1. Ajuste as variáveis no arquivo `.env` na raiz do projeto.
2. Execute:

```bash
docker compose up --build
```

3. Acesse:
	- Frontend: `http://localhost:3000`
	- Backend API: `http://localhost:8000/api`

## Variáveis principais do `.env`

- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: credenciais e banco do Postgres.
- `DB_PORT`: porta do Postgres no host (padrão `5432`).
- `SECRET_KEY`: chave do Django.
- `DEBUG`: modo debug do Django (`True`/`False`).
- `ALLOWED_HOSTS`: hosts permitidos pelo Django (separados por vírgula).
- `CORS_ALLOWED_ORIGINS`: origens permitidas para CORS (separadas por vírgula).
- `CSRF_TRUSTED_ORIGINS`: origens confiáveis para CSRF (separadas por vírgula).
- `BACKEND_PORT`: porta do backend no host (padrão `8000`).
- `FRONTEND_PORT`: porta do frontend no host (padrão `3000`).
- `NEXT_PUBLIC_API_URL`: URL da API usada no navegador (deve apontar para o backend no host).

## Observações de desenvolvimento

- O backend aplica migrações automaticamente no start do container.
- O frontend roda em modo dev com hot-reload.
- Em Windows/OneDrive, o polling de arquivos está habilitado no frontend para melhorar detecção de mudanças.


teste