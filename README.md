# Neoscópio

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)

Dicionário colaborativo dos neologismos do português brasileiro. Qualquer
pessoa cadastrada envia uma palavra; a equipe modera; o que é aprovado entra
no dicionário público e pode ser curtido.

**Stack:** Django 6 + DRF (API) · Next.js 16 + Tailwind 4 (web) · PostgreSQL 17
· Docker Compose.

## Subir em desenvolvimento

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: <http://localhost:3000>
- API: <http://localhost:8000/api>
- Documentação da API (Swagger): <http://localhost:8000/api/docs>
- Admin do Django: <http://localhost:8000/admin>

Popule a base com verbetes de demonstração e um usuário `admin` / `admin123`:

```bash
docker compose exec backend python manage.py seed_fake_data
```

> Em desenvolvimento os e-mails **não são enviados**: eles são impressos no log
> do backend. É assim que você lê o link de recuperação de senha:
>
> ```bash
> docker compose logs backend | grep -A5 redefinir-senha
> ```

## Deploy em produção

Veja **[DEPLOY.md](DEPLOY.md)** — VPS única com Docker Compose, Caddy e HTTPS
automático.

## Rodar sem Docker

<details>
<summary>Backend</summary>

Precisa de um PostgreSQL rodando (o `ArrayField` de tags é específico do
Postgres; SQLite não serve nem para os testes).

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export DEBUG=True
export SECRET_KEY=dev
export DATABASE_URL="postgres://usuario:senha@127.0.0.1:5432/neoscopio"

python manage.py migrate
python manage.py seed_fake_data
python manage.py runserver
```

</details>

<details>
<summary>Frontend</summary>

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api npm run dev
```

</details>

## Testes e verificações

O CI (`.github/workflows/ci.yml`) roda tudo isso em cada push e PR. Para rodar
localmente:

```bash
# Backend — 66 testes (permissões, moderação, curtidas, validação, busca,
# recuperação de senha, e-mails)
cd backend && python manage.py test

# Nenhuma migração pendente e checklist de produção
python manage.py makemigrations --check --dry-run
python manage.py check --deploy

# Frontend
cd frontend
npx tsc --noEmit
npx eslint src --max-warnings 0
npm run build
npm audit --audit-level=high
```

O CI também builda as duas imagens Docker de produção e valida o
`docker-compose.prod.yml`, para que um erro de Dockerfile apareça no PR e não
no deploy.

## Estrutura

```
backend/
  config/         settings, urls, paginação, healthcheck, envio de e-mail
  templates/      templates de e-mail (HTML + texto puro)
  neologismo/     modelo, serializers, views, permissões, seeds
  usuario/        usuário customizado, cadastro, login, logout, senha
frontend/
  instrumentation*.ts  inicialização do Sentry (cliente e servidor)
  src/
    app/          rotas (App Router)
    components/   Header, Footer, cards, toast, botão de curtir
    hooks/        useAuth, useNeologismos
    lib/api.ts    cliente da API e sessão
    types/        contratos compartilhados com a API
```

## A API

Documentação viva em `/api/docs`. Os pontos principais:

| Método | Rota | Quem pode |
|---|---|---|
| `GET` | `/api/neologismos/` | Público (só aprovados) |
| `GET` | `/api/neologismos/{id}/` | Público; o autor também vê o próprio rascunho |
| `POST` | `/api/neologismos/` | Autenticado (entra como `pendente`) |
| `PATCH`/`DELETE` | `/api/neologismos/{id}/` | Autor (enquanto não aprovado) ou equipe |
| `POST` | `/api/neologismos/{id}/curtir/` | Autenticado (alterna a curtida) |
| `GET` | `/api/neologismos/meus/` | Autenticado (os próprios envios, qualquer status) |
| `GET` | `/api/neologismos/facetas/` | Público (tags e classes com contagem) |
| `POST` | `/api/neologismos/{id}/aprovar\|rejeitar\|reativar/` | Equipe |
| `GET` | `/api/neologismos/resumo/` | Equipe (contadores por status) |
| `POST` | `/api/cadastro/` · `/api/login/` · `/api/logout/` | Público / autenticado |
| `GET` | `/api/me/` | Autenticado |
| `POST` | `/api/senha/recuperar/` | Público (dispara o e-mail; responde 200 mesmo se o e-mail não existe) |
| `POST` | `/api/senha/redefinir/` | Público (com o `uid` e `token` do link) |
| `GET` | `/api/health/` | Público (usado pelo healthcheck do container) |

Listagens aceitam `?search=`, `?tag=`, `?classe=`,
`?ordering=recentes|antigos|populares|alfabetica`, `?page=` e `?page_size=`, e
respondem paginado:

```json
{ "count": 42, "page": 1, "total_pages": 2, "next": "...", "previous": null, "results": [] }
```

Autenticação por token no header: `Authorization: Token <chave>`.

## E-mail e monitoramento

Os dois são **opcionais e desligados por padrão** — o site funciona sem eles.

| | Sem configurar | Configurando |
|---|---|---|
| **E-mail** (`EMAIL_HOST`) | Envios descartados em silêncio: ninguém recupera senha, nenhum aviso de moderação chega | Recuperação de senha e aviso ao autor quando o verbete é aprovado/rejeitado |
| **Sentry** (`SENTRY_DSN*`) | SDK inerte, nenhuma requisição sai da aplicação | Erros de backend e frontend agregados, com sourcemaps |

Falha de e-mail **nunca** derruba a ação do usuário: aprovar um verbete
funciona com o SMTP fora do ar, e a falha vai para o log. Veja o
[DEPLOY.md](DEPLOY.md) para configurar os dois.

## Variáveis de ambiente

Descritas em [`.env.example`](.env.example) (desenvolvimento) e
[`.env.prod.example`](.env.prod.example) (produção).

Três pegadinhas que vale saber de antemão:

- **`NEXT_PUBLIC_*` é embutido no bundle em tempo de build**, não lido em
  runtime. Mudar essas variáveis exige rebuild da imagem do frontend.
- **Com `DEBUG=False`, o Django exige `SECRET_KEY` e `ALLOWED_HOSTS`** e
  recusa subir sem eles. É intencional: evita produção assinando sessões com
  uma chave de exemplo.
- **O rate limit depende de um cache compartilhado.** Em produção o cache vive
  numa tabela do Postgres, criada pelo entrypoint. Com o `LocMemCache` padrão,
  cada worker do gunicorn contaria por conta própria e o limite de login viraria
  N vezes mais frouxo.
