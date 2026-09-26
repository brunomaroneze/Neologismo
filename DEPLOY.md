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

## 5. Operação do dia a dia

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

## 6. Backup do banco

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

## 7. Nota sobre HSTS

`SECURE_HSTS_SECONDS` manda o navegador **se recusar** a acessar o site por
HTTP durante aquele período, e a diretiva fica memorizada no navegador de
cada visitante. Se o HTTPS quebrar depois, não há como desfazer rapidamente.

Por isso o padrão aqui é `3600` (1 hora). Depois de alguns dias com o
certificado renovando normalmente, suba para `31536000` (1 ano).

## 8. Diagnóstico

| Sintoma | Causa provável |
|---|---|
| Caddy em `Restarting` | Erro de sintaxe no `Caddyfile` — veja `logs caddy` |
| Certificado não emite | DNS ainda não aponta para a VPS, ou 80/443 fechadas |
| `backend` nunca fica `healthy` | Veja `logs backend`; geralmente é `DATABASE_URL` ou migração falhando |
| `DisallowedHost` no log | `DOMINIO` no `.env` não bate com o domínio acessado |
| Erro de CORS no navegador | Idem: `CORS_ALLOWED_ORIGINS` é derivado de `DOMINIO` |
| Frontend chamando `localhost:8000` | A imagem foi buildada sem o build-arg. Rebuild com `--build` |
| Admin sem CSS | `collectstatic` falhou no start — veja `logs backend` |

```bash
# Ver a configuração final que o compose vai aplicar
docker compose -f docker-compose.prod.yml config

# Entrar no container do backend
docker compose -f docker-compose.prod.yml exec backend sh

# Checklist de produção do próprio Django
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py check --deploy
```

## 9. O que ainda não está coberto

Deixado de fora de propósito, para você decidir se precisa:

- **E-mail transacional** (recuperação de senha, aviso de moderação): exige um
  provedor SMTP e as variáveis `EMAIL_*` do Django.
- **Monitoramento de erros** (Sentry ou equivalente): hoje os erros só vão
  para o log do container.
- **CDN** na frente do Caddy.
- **Réplica do banco.** O backup do passo 6 é a rede de proteção atual.
