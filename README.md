# Neoscópio

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
[![Entrega](../../actions/workflows/cd.yml/badge.svg)](../../actions/workflows/cd.yml)
[![CodeQL](../../actions/workflows/codeql.yml/badge.svg)](../../actions/workflows/codeql.yml)

Banco de neologismos do português brasileiro. Qualquer
pessoa cadastrada envia uma palavra; a equipe modera; o que é aprovado entra
no banco público e pode ser curtido.

**Stack:** Django 6 (site em templates + API com DRF) · PostgreSQL 17 · Docker
Compose.

## Subir em desenvolvimento

```bash
cp .env.example .env
docker compose up --build
```

- Site: <http://localhost:8000>
- API: <http://localhost:8000/api>
- Documentação da API (Swagger): <http://localhost:8000/api/docs>
- Admin do Django: <http://localhost:8000/admin>

Popule a base com verbetes de demonstração e um usuário `admin` (administrador
do painel). A senha é gerada na hora e aparece uma vez na saída do comando; para
escolher, use `--admin-password`:

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

## Testes e verificações

```bash
# Backend — 82 testes (permissões, moderação, curtidas, validação, busca sem
# acento, cache de facetas, recuperação de senha, e-mails)
cd backend
pip install -r requirements.txt -r requirements-dev.txt

ruff check .                                  # lint
coverage run manage.py test && coverage report # testes + piso de 80%
python manage.py makemigrations --check --dry-run
python manage.py check --deploy
```

## Pipeline

Duas workflows, encadeadas:

**`ci.yml` — qualidade.** Roda em todo PR e em push na `develop`:

| Job | O que verifica |
|---|---|
| Backend | ruff, `manage.py check`, migrações pendentes, testes com cobertura mínima, checklist de produção do Django, validade do schema OpenAPI |
| Auditoria | `pip-audit` — falha em CVE conhecida |
| Compose | os três arquivos de Compose são válidos |
| Imagens | a imagem Docker de produção compila |

**`cd.yml` — entrega.** Roda em push na `main`, em tag `v*` ou à mão:

```
Qualidade  ->  Publicar imagens  ->  Deploy na VPS  ->  Verificação
(ci.yml)       (ghcr.io, tag        (ssh, pull +        (health, home
                sha-<commit>)        up -d)              e sitemap)
```

A primeira etapa é o `ci.yml` inteiro, chamado como workflow reutilizável:
não existe caminho de deploy que pule os testes. O deploy só acontece com os
secrets cadastrados no environment `producao`; sem eles o job para com a
mensagem do que falta, antes de tentar conectar. O passo a passo da
configuração está na seção 9 do [DEPLOY.md](DEPLOY.md).

Completam a pipeline o **CodeQL** (análise estática de segurança em PR e
semanalmente) e o **Dependabot** (atualização agrupada de pip, actions e
imagens Docker, com o CI validando cada PR).

## Estrutura

```
backend/
  config/         settings, urls, paginação, healthcheck, envio de e-mail
  templates/      templates de e-mail (HTML + texto puro)
  neologismo/     modelo, serializers, views, permissões, seeds
  usuario/        usuário customizado, cadastro, login, logout, senha
  detector/       detector de neologismos
  web/            o site: views, painel do administrador, templates, CSS e JS
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

`?search=` **ignora acento e caixa** (via extensão `unaccent` do Postgres) e
procura no título, na definição, no exemplo de uso e nas tags: `?search=voce`
encontra "Vocezinho". `?tag=` aceita a tag sem acento — `?tag=internetes`
casa com `Internetês`.


```json
{ "count": 42, "page": 1, "total_pages": 2, "next": "...", "previous": null, "results": [] }
```

Autenticação por token no header: `Authorization: Token <chave>`.

## Descoberta e compartilhamento

Um dicionário público só serve se as pessoas acharem os verbetes. Três coisas
cobrem isso:

- **`/sitemap.xml`** lista todos os verbetes aprovados, com a data da última
  alteração de cada um. É gerado a cada requisição, então um verbete aprovado
  hoje já entra no sitemap.
- **`/robots.txt`** libera o acervo e mantém fora do índice as rotas que só
  levariam a uma tela de login (painel, envio, conta).
- **Cada verbete tem seus próprios metadados** (`title`, `description`, OG e
  Twitter cards), em `backend/web/templates/web/verbete.html`. Um link colado no WhatsApp mostra a
  palavra e a definição, não o título genérico do site.

A pipeline de entrega confere o sitemap depois de cada deploy, porque é o
tipo de coisa que quebra em silêncio.

## E-mail e monitoramento

Os dois são **opcionais e desligados por padrão** — o site funciona sem eles.

| | Sem configurar | Configurando |
|---|---|---|
| **E-mail** (`EMAIL_HOST`) | Envios descartados em silêncio: ninguém recupera senha, nenhum aviso de moderação chega | Recuperação de senha e aviso ao autor quando o verbete é aprovado/rejeitado |
| **Sentry** (`SENTRY_DSN*`) | SDK inerte, nenhuma requisição sai da aplicação | Erros do Django agregados |

Falha de e-mail **nunca** derruba a ação do usuário: aprovar um verbete
funciona com o SMTP fora do ar, e a falha vai para o log. Veja o
[DEPLOY.md](DEPLOY.md) para configurar os dois.

## Variáveis de ambiente

Descritas em [`.env.example`](.env.example) (desenvolvimento) e
[`.env.prod.example`](.env.prod.example) (produção).

Duas pegadinhas que vale saber de antemão:

- **Com `DEBUG=False`, o Django exige `SECRET_KEY` e `ALLOWED_HOSTS`** e
  recusa subir sem eles. É intencional: evita produção assinando sessões com
  uma chave de exemplo.
- **O rate limit depende de um cache compartilhado.** Em produção o cache vive
  numa tabela do Postgres, criada pelo entrypoint. Com o `LocMemCache` padrão,
  cada worker do gunicorn contaria por conta própria e o limite de login viraria
  N vezes mais frouxo.
