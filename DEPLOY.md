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

O site usa e-mail para duas coisas: **recuperação de senha** e **aviso ao
autor** quando o verbete dele é aprovado ou rejeitado.

Sem `EMAIL_HOST` preenchido o site **não quebra** — o Django passa a descartar
os envios em silêncio. O efeito prático é que ninguém consegue recuperar a
senha e nenhum aviso de moderação chega. É um estado válido para homologação,
não para produção.

### Escolhendo um provedor

Não use SMTP de Gmail pessoal: limite baixo e bloqueio quase garantido.
Serviços transacionais têm plano gratuito suficiente para este projeto
(Resend, Brevo, SendGrid, Amazon SES). Preencha no `.env`:

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

## 9. Nota sobre HSTS

`SECURE_HSTS_SECONDS` manda o navegador **se recusar** a acessar o site por
HTTP durante aquele período, e a diretiva fica memorizada no navegador de
cada visitante. Se o HTTPS quebrar depois, não há como desfazer rapidamente.

Por isso o padrão aqui é `3600` (1 hora). Depois de alguns dias com o
certificado renovando normalmente, suba para `31536000` (1 ano).

## 10. Diagnóstico

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

```bash
# Ver a configuração final que o compose vai aplicar
docker compose -f docker-compose.prod.yml config

# Entrar no container do backend
docker compose -f docker-compose.prod.yml exec backend sh

# Checklist de produção do próprio Django
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py check --deploy
```

## 11. O que ainda não está coberto

Deixado de fora de propósito, para você decidir se precisa:

- **CDN** na frente do Caddy.
- **Réplica do banco.** O backup do passo 8 é a rede de proteção atual.
- **Deploy automático.** O CI valida cada push (testes, lint, build das
  imagens), mas não publica nada: subir para a VPS continua sendo
  `git pull && docker compose -f docker-compose.prod.yml up -d --build`.
- **Fila de tarefas.** Os e-mails são enviados na própria request. No volume
  deste projeto isso é suficiente; se um dia o envio ficar lento, o caminho é
  Celery ou django-q.
