# Deploy — VPS única com Docker Compose

Este guia sobe o Neoscópio inteiro (Postgres + Django + Next + HTTPS) em uma
máquina só. O Caddy é o único serviço exposto à internet e cuida do
certificado TLS sozinho.

```
internet ──▶ Caddy :80/:443 ──┬──▶ backend:8000   (/api, /admin, /static, /media)
                              └──▶ frontend:3000  (todo o resto)
                                       │
                                     db:5432       (rede interna, sem porta no host)
```

## 1. Pré-requisitos

- Uma VPS com Ubuntu 22.04+ (1 vCPU / 2 GB de RAM já roda; 2 vCPU / 4 GB é
  confortável).
- Um domínio com o registro **A** (e **AAAA**, se houver IPv6) apontando para
  o IP da VPS. **Configure o DNS antes de subir**: o Caddy só consegue emitir
  o certificado se o domínio já resolver para esta máquina.
- Portas 80 e 443 abertas no firewall.
- O Postgres do Compose é a imagem oficial, onde o usuário da aplicação pode
  instalar extensões — a busca sem acento depende da extensão `unaccent`, que
  a migração `0008_unaccent` liga sozinha. Se você trocar por um Postgres
  gerenciado, habilite `unaccent` no painel antes do primeiro `migrate`.

```bash
# Docker + plugin do Compose
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"   # saia e entre de novo para valer

# Firewall
sudo ufw allow OpenSSH
sudo ufw allow 80,443/tcp
sudo ufw enable
```

## 2. Clonar e configurar

```bash
git clone <url-do-repositorio> neoscopio
cd neoscopio

cp .env.prod.example .env
```

Preencha o `.env`. Os três valores que você precisa gerar:

```bash
# SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# POSTGRES_PASSWORD
openssl rand -base64 32
```

| Variável | O que é |
|---|---|
| `DOMINIO` | Domínio sem `https://`. Ex.: `neoscopio.com.br` |
| `EMAIL_ACME` | E-mail do registro Let's Encrypt (avisos de expiração) |
| `SECRET_KEY` | Chave do Django. **Trocar depois invalida todas as sessões e tokens** |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciais do banco |
| `SECURE_HSTS_SECONDS` | Comece em `3600`. Veja a nota sobre HSTS abaixo |
| `GUNICORN_WORKERS` | Regra prática: `(2 × núcleos) + 1` |

O compose de produção **falha na hora** se `DOMINIO`, `EMAIL_ACME`,
`SECRET_KEY` ou as credenciais do banco estiverem vazias — é de propósito,
para não subir um site com configuração pela metade.

## 3. Subir

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

O primeiro start leva alguns minutos (build das duas imagens + emissão do
certificado). Acompanhe:

```bash
docker compose -f docker-compose.prod.yml logs -f
```

Quando `backend` aparecer como `healthy`, está no ar:

```bash
docker compose -f docker-compose.prod.yml ps
curl https://SEU-DOMINIO/api/health/     # {"status":"ok","banco":true}
```

## 4. Criar o usuário administrador

As migrações rodam sozinhas no start. Falta só a conta de moderação:

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py createsuperuser
```

> **Importante:** `createsuperuser` cria a conta com `is_staff` e
> `is_superuser`, mas **não** com `is_admin` — e é `is_admin` que o frontend
> usa para liberar o painel de moderação. Promova a conta depois:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py shell -c \
  "from django.contrib.auth import get_user_model; U=get_user_model(); u=U.objects.get(username='SEU_USUARIO'); u.is_admin=True; u.save(); print('promovido')"
```

Para popular a base com verbetes de demonstração (**apenas em homologação**):

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py seed_fake_data
```

## 5. E-mail transacional

O site usa e-mail para **confirmar a conta no cadastro** (obrigatório),
**recuperação de senha** e **aviso ao autor** quando o verbete dele é aprovado
ou rejeitado.

Sem `EMAIL_HOST` preenchido o Django descarta os envios em silêncio. Como a
confirmação de e-mail é obrigatória, **ninguém consegue concluir o cadastro**
nesse estado. Enquanto o e-mail não estiver configurado, um administrador pode
confirmar contas à mão em **Painel → Usuários → Confirmar e-mail**.

### Gmail com senha de app (configuração atual)

1. Na conta Google que vai enviar, ative a **verificação em duas etapas**.
2. Em <https://myaccount.google.com/apppasswords>, crie uma senha de app
   chamada "Neoscópio" e copie as 16 letras (sem os espaços).
3. No `.env` da VPS:

```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=sua.conta@gmail.com
EMAIL_HOST_PASSWORD=abcdefghijklmnop
DEFAULT_FROM_EMAIL=Neoscópio <sua.conta@gmail.com>
```

Limites do Gmail: cerca de 500 e-mails por dia, e o remetente precisa ser o
próprio endereço do Gmail. Se o volume crescer, ou para enviar como
`@neoscopio.com.br`, troque por um serviço transacional (abaixo).

### Serviço transacional (alternativa)

Resend, Brevo, SendGrid e Amazon SES têm plano gratuito suficiente para este
projeto e permitem remetente no domínio do site. Preencha no `.env`:

```bash
EMAIL_HOST=smtp.resend.com
EMAIL_PORT=587
EMAIL_HOST_USER=resend
EMAIL_HOST_PASSWORD=<a chave da API>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Neoscópio <nao-responda@neoscopio.com.br>
```

### Autentique o domínio

O `DEFAULT_FROM_EMAIL` precisa ser de um domínio que você autenticou no
provedor, com os registros **SPF** e **DKIM** no DNS. Sem isso o e-mail sai,
mas cai em spam — que é pior do que não enviar, porque parece funcionar.

### Testando

```bash
# Dispara um e-mail de teste
docker compose -f docker-compose.prod.yml exec backend python manage.py shell -c \
  "from django.core.mail import send_mail; send_mail('Teste', 'Funcionou.', None, ['voce@exemplo.com'])"
```

Falhas de envio **nunca** derrubam a ação do usuário: elas vão para o log do
container (e para o Sentry, se configurado). Para investigar:

```bash
docker compose -f docker-compose.prod.yml logs backend | grep -i "Falha ao enviar"
```

## 5.1. Login com Google e Facebook

Os botões "Continuar com Google" e "Continuar com Facebook" só aparecem quando
as credenciais do provedor estão no `.env`. Depois de preencher, recrie o
backend (`... up -d backend`).

**Google** — <https://console.cloud.google.com/apis/credentials>

1. Crie um projeto, configure a **tela de consentimento OAuth** (tipo
   "Externo", nome "Neoscópio", e-mail de suporte, domínio do site) e publique.
2. *Criar credenciais → ID do cliente OAuth → Aplicativo da Web*.
3. **URI de redirecionamento autorizado:**
   `https://SEU-DOMINIO/conta/google/login/callback/`
4. Copie para o `.env`: `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET`.

**Facebook** — <https://developers.facebook.com/apps>

1. *Criar app → Autenticar e solicitar dados dos usuários com o Login do
   Facebook*.
2. Em *Login do Facebook → Configurações*, **URI de redirecionamento do OAuth
   válido:** `https://SEU-DOMINIO/conta/facebook/login/callback/`
3. Em *Configurações do app → Básico*, preencha a URL da política de
   privacidade e coloque o app em modo **Ao vivo**.
4. Copie para o `.env`: `FACEBOOK_APP_ID` (ID do app) e `FACEBOOK_APP_SECRET`
   (chave secreta).

O Google entrega e-mails já verificados, então quem entra pelo Google não
precisa confirmar nada. O Facebook não garante isso: o site pede a confirmação
pelo próprio e-mail. Uma conta social com o mesmo e-mail de uma conta existente
entra nessa conta, em vez de criar outra.

## 5.2. Detector de neologismos

O painel tem a aba **Detector**: a equipe cola um texto e o sistema aponta as
palavras que não estão no léxico de referência, com classe gramatical,
processo de formação sugerido e a frase de contexto. Adaptado de
[neologism_detector](https://github.com/brunomaroneze/neologism_detector).

- **Léxico:** ≈480 mil palavras em `backend/detector/dados/lexico.txt.gz`,
  carregadas no banco pelo `entrypoint.sh` no primeiro start
  (`importar_lexico --se-vazio`, ≈15 s). Para recarregar:
  `python manage.py importar_lexico`.
- **spaCy:** o modelo `pt_core_news_sm` está em `requirements-modelos.txt`
  (fora do `requirements.txt` porque não vem do PyPI e o pip-audit não o
  audita). Ele é carregado no primeiro uso de cada worker (≈2 s, ≈150 MB).
- **Classificador:** é treinado no próprio servidor, no primeiro uso, com
  `dados/treino.csv` mais os neologismos aprovados que têm processo de
  formação, e refeito a cada 6 horas.
- **Falsos positivos:** "Não é neologismo" guarda a palavra em
  `PalavraIgnorada`, e ela some das próximas análises.

## 6. Monitoramento de erros (Sentry)

Opcional, e desligado por padrão: sem DSN o SDK fica inerte e nada sai da
aplicação.

Crie dois projetos no Sentry — um Django e um Next.js — e preencha:

```bash
SENTRY_DSN_BACKEND=https://...    # privado, só o container vê
SENTRY_DSN_FRONTEND=https://...   # vai para o bundle público (é o normal)
SENTRY_ENVIRONMENT=production
```

O DSN do frontend ser público é o funcionamento esperado do Sentry no
navegador: um DSN só permite enviar eventos, não ler nada.

Para os stack traces apontarem para o seu código em vez do bundle minificado,
adicione as três variáveis de sourcemap e **rebuilde o frontend**:

```bash
SENTRY_ORG=sua-org
SENTRY_PROJECT=neoscopio-frontend
SENTRY_AUTH_TOKEN=<token com permissão de release>

docker compose -f docker-compose.prod.yml up -d --build frontend
```

Os sourcemaps são enviados ao Sentry e **apagados do bundle público** — sem
isso, o código-fonte original ficaria servido junto com o site.

O que fica de fora de propósito: `traces_sample_rate` é `0.0` (só erros, sem
tracing), replay de sessão está desligado, e `send_default_pii` é `False` — os
e-mails e nomes de usuário do banco não saem para um serviço terceiro.

## 7. Operação do dia a dia

```bash
# Atualizar para a última versão do código
git pull
docker compose -f docker-compose.prod.yml up -d --build

# Logs de um serviço
docker compose -f docker-compose.prod.yml logs -f backend

# Shell do Django
docker compose -f docker-compose.prod.yml exec backend python manage.py shell

# Reiniciar só o backend
docker compose -f docker-compose.prod.yml restart backend

# Parar tudo (os dados do banco ficam no volume)
docker compose -f docker-compose.prod.yml down
```

> `down -v` **apaga o volume do Postgres junto**. Nunca use em produção sem
> ter o backup em mãos.

## 8. Backup do banco

Sem isto, uma VPS perdida leva o dicionário inteiro.

```bash
# Backup manual
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > backup-$(date +%F).sql.gz

# Restaurar
gunzip -c backup-2026-09-25.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

Diário às 3h, via `crontab -e` do root:

```cron
0 3 * * * cd /caminho/para/neoscopio && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U neoscopio neoscopio | gzip > /var/backups/neoscopio-$(date +\%F).sql.gz && find /var/backups -name 'neoscopio-*.sql.gz' -mtime +14 -delete
```

Copie os dumps para fora da VPS (S3, Backblaze, outra máquina) — backup que
mora no mesmo disco não é backup.

## 9. Deploy automático pelo GitHub Actions

As etapas acima são o deploy manual, e continuam valendo — é o caminho a usar
na primeira subida e sempre que algo der errado. Esta seção é a automação de
tudo isso: o workflow `.github/workflows/cd.yml`.

### O que ele faz

```
push na main/develop  ->  Qualidade  ->  Publicar imagens  ->  Deploy na VPS  ->  Verificação
                  (ci.yml)       (GHCR)               (ssh)              (curl)
```

1. **Qualidade** — chama o `ci.yml` inteiro: lint, 82 testes do backend com
   cobertura, tipos, lint e testes do frontend, build do Next, auditoria de
   CVE e validação dos arquivos de Compose. Qualquer falha aqui para a
   pipeline antes de ela tocar a VPS.
2. **Publicar imagens** — constrói backend e frontend e publica no GitHub
   Container Registry (`ghcr.io`), com a tag `sha-<commit>`.
3. **Deploy na VPS** — entra por SSH, sincroniza a configuração com o commit,
   baixa as imagens e sobe. As migrações rodam no entrypoint do backend, como
   em qualquer start.
4. **Verificação** — de fora, pela internet: `/api/health/` com banco
   acessível, a Home respondendo 200 e o `sitemap.xml` com URLs.

A diferença prática em relação ao `up -d --build` manual é que a VPS deixa de
compilar: ela baixa a imagem que a CI já construiu e testou. Deploy mais
rápido, sem consumir CPU da máquina que está servindo o site, e o que roda em
produção é exatamente o artefato que passou nos testes.

### Preparar a VPS

Crie um usuário só para o deploy, com acesso ao Docker e nada além disso:

```bash
# Na VPS, como root
adduser --disabled-password --gecos "" deploy
usermod -aG docker deploy
chown -R deploy:deploy /caminho/para/neoscopio
```

> Pertencer ao grupo `docker` equivale a ter root na máquina — é inerente ao
> Docker, não uma falha desta configuração. O que o usuário separado dá é
> rastreabilidade (dá para ver o que o deploy fez) e a possibilidade de
> revogar só essa chave sem mexer na sua.

Na **sua máquina**, gere o par de chaves do deploy:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/neoscopio_deploy -C "deploy-neoscopio" -N ""

# Instale a chave pública na VPS
ssh-copy-id -i ~/.ssh/neoscopio_deploy.pub deploy@SEU_IP

# Pegue a identidade do servidor (evita ataque de man-in-the-middle no CI)
ssh-keyscan -p 22 SEU_IP
```

### Cadastrar no GitHub

Em **Settings > Environments**, crie o environment `producao`. É nele que os
segredos de produção ficam, e é onde se liga **Required reviewers** se você
quiser que todo deploy espere uma aprovação sua.

**Secrets** (Settings > Environments > producao > Secrets):

| Secret | Valor |
|---|---|
| `SSH_HOST` | IP ou hostname da VPS |
| `SSH_USER` | `deploy` |
| `SSH_PRIVATE_KEY` | conteúdo de `~/.ssh/neoscopio_deploy` (a chave **privada**, inteira, com as linhas `BEGIN`/`END`) |
| `SSH_HOST_KEY` | a saída do `ssh-keyscan` acima |
| `SENTRY_DSN_FRONTEND` | opcional — DSN do projeto de frontend |
| `SENTRY_AUTH_TOKEN` | opcional — para subir os sourcemaps |

**Variables** (mesma tela, aba Variables — não são segredo, aparecem no log):

| Variable | Valor |
|---|---|
| `DOMINIO` | `neoscopio.com.br` |
| `CAMINHO_PROJETO` | caminho do repositório na VPS, ex. `/home/deploy/neoscopio` |
| `SSH_PORT` | opcional, padrão `22` |
| `COMPOSE_EXTRA` | opcional. `docker-compose.nginx.yml` quando a VPS usa nginx em vez do Caddy (seção 12) |
| `SENTRY_ORG` / `SENTRY_PROJECT` | opcionais, junto do token acima |

`DOMINIO` é variable e não secret porque ele é embutido no bundle do frontend
em tempo de build: está no HTML de qualquer forma.

Falta algum dos obrigatórios? O primeiro passo do job de deploy para e diz
exatamente qual — ele não tenta conectar sem isso.

### Como disparar

- **Automático:** todo push na `main` ou na `develop`. Hoje as duas publicam
  no mesmo `DOMINIO` (o ambiente de teste); quando existir um servidor de
  produção separado, a `main` precisa de variáveis próprias.
- **Versão marcada:** uma tag `v*` (ex. `v1.2.0`) também publica as imagens
  como `1.2.0`, `1.2` e `latest`.
- **À mão:** aba **Actions > Entrega > Run workflow**, escolhendo o branch ou
  a tag. A opção *"Só publicar as imagens"* constrói sem mexer na VPS.

### Rollback

As imagens ficam no GHCR com a tag do commit, então voltar é subir a imagem
anterior — não precisa esperar build nenhum:

```bash
# Na VPS, com o commit que funcionava
export IMAGEM_BACKEND=ghcr.io/brunomaroneze/neologismo-backend:sha-<commit>
export IMAGEM_FRONTEND=ghcr.io/brunomaroneze/neologismo-frontend:sha-<commit>

docker compose -f docker-compose.prod.yml -f docker-compose.deploy.yml up -d
```

> **Atenção:** rollback de imagem não desfaz migração de banco. Se o commit
> defeituoso aplicou uma migração destrutiva, o caminho é o backup do passo 8.

### Primeira vez

A automação não substitui a primeira subida: o `.env` de produção, o volume
do Postgres e o certificado do Caddy precisam existir antes. Faça os passos
1 a 4 à mão, confirme o site no ar, e só então use a pipeline.

## 10. Nota sobre HSTS

`SECURE_HSTS_SECONDS` manda o navegador **se recusar** a acessar o site por
HTTP durante aquele período, e a diretiva fica memorizada no navegador de
cada visitante. Se o HTTPS quebrar depois, não há como desfazer rapidamente.

Por isso o padrão aqui é `3600` (1 hora). Depois de alguns dias com o
certificado renovando normalmente, suba para `31536000` (1 ano).

## 11. Diagnóstico

| Sintoma | Causa provável |
|---|---|
| Caddy em `Restarting` | Erro de sintaxe no `Caddyfile` — veja `logs caddy` |
| Certificado não emite | DNS ainda não aponta para a VPS, ou 80/443 fechadas |
| `backend` nunca fica `healthy` | Veja `logs backend`; geralmente é `DATABASE_URL` ou migração falhando |
| `DisallowedHost` no log | `DOMINIO` no `.env` não bate com o domínio acessado |
| Erro de CORS no navegador | Idem: `CORS_ALLOWED_ORIGINS` é derivado de `DOMINIO` |
| Frontend chamando `localhost:8000` | A imagem foi buildada sem o build-arg. Rebuild com `--build` |
| Admin sem CSS | `collectstatic` falhou no start — veja `logs backend` |
| Rate limit mais frouxo que o configurado | A tabela de cache não foi criada. Rode `exec backend python manage.py createcachetable` |
| E-mail não chega | `EMAIL_HOST` vazio, ou domínio sem SPF/DKIM (caiu em spam) |
| Migração falha em `CREATE EXTENSION unaccent` | O usuário do Postgres não pode instalar extensões. Na imagem oficial ele pode; em Postgres gerenciado, habilite `unaccent` pelo painel antes do `migrate` |
| Busca voltou a diferenciar acento | A migração `0008_unaccent` não rodou. Confirme com `exec backend python manage.py showmigrations neologismo` |
| `sitemap.xml` vazio com o site no ar | O frontend não alcança o backend internamente. Confira `API_URL_INTERNA` no compose e `exec frontend wget -qO- http://backend:8000/api/health/` |
| Filtros da Home desatualizados | Cache de facetas. É invalidado a cada escrita; para forçar, `exec backend python manage.py shell -c "from django.core.cache import cache; cache.clear()"` |

```bash
# Ver a configuração final que o compose vai aplicar
docker compose -f docker-compose.prod.yml config

# Entrar no container do backend
docker compose -f docker-compose.prod.yml exec backend sh

# Checklist de produção do próprio Django
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py check --deploy
```

## 12. VPS que já tem nginx (em vez do Caddy)

Se a VPS já roda um nginx atendendo outros sites nas portas 80/443, o Caddy
não pode subir. Use o override `docker-compose.nginx.yml`, que desliga o Caddy
e publica backend e frontend só em `127.0.0.1`:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.nginx.yml up -d --build
```

- O `.env` continua precisando de `EMAIL_ACME` preenchido (qualquer e-mail):
  o compose de produção valida a variável mesmo com o Caddy desligado.
- No nginx, use o modelo `deploy/nginx-neoscopio.conf`: `/api`, `/admin` e
  `/static` vão para `127.0.0.1:8000`, o resto para `127.0.0.1:3000`.
- **Não rode o `docker-compose.yml` de desenvolvimento em produção.** Com
  `npm run dev` atrás de um domínio, o Next 16 bloqueia os recursos de dev
  (`/_next/hmr`) para origens fora de `allowedDevOrigins`, a página nunca é
  hidratada e os cards ficam carregando para sempre — sem nenhuma chamada à API.

## 13. O que ainda não está coberto

Deixado de fora de propósito, para você decidir se precisa:

- **CDN** na frente do Caddy.
- **Réplica do banco.** O backup do passo 8 é a rede de proteção atual.
- **Fila de tarefas.** Os e-mails são enviados na própria request. No volume
  deste projeto isso é suficiente; se um dia o envio ficar lento, o caminho é
  Celery ou django-q.
