"""
Django settings do projeto Neoscópio.

Toda configuração sensível vem de variáveis de ambiente. O arquivo é escrito
para funcionar em dois modos:

- desenvolvimento (DEBUG=True): defaults permissivos, sem HTTPS;
- produção (DEBUG=False): exige SECRET_KEY e ALLOWED_HOSTS, liga HSTS,
  cookies seguros e redirecionamento para HTTPS.

Referência: https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(os.path.join(BASE_DIR, '.env'))


def env_bool(name, default=False):
    """Lê um booleano do ambiente aceitando True/true/1/yes/on."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ('1', 'true', 'yes', 'on')


def env_list(name, default=''):
    """Lê uma lista separada por vírgula, ignorando itens vazios."""
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(',') if item.strip()]


def env_int(name, default):
    try:
        return int(os.getenv(name, ''))
    except ValueError:
        return default


# --- Modo de execução -------------------------------------------------------

DEBUG = env_bool('DEBUG', False)

# Em produção a chave é obrigatória: sem fallback silencioso, que é o jeito
# clássico de subir um site assinando sessões com uma chave pública.
SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-chave-apenas-para-desenvolvimento'
    else:
        raise ImproperlyConfigured(
            'SECRET_KEY precisa estar definida quando DEBUG=False. '
            'Gere uma com: python -c "import secrets; print(secrets.token_urlsafe(64))"'
        )

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', '127.0.0.1,localhost' if DEBUG else '')
if not DEBUG and not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        'ALLOWED_HOSTS precisa listar os domínios do site quando DEBUG=False. '
        'Ex.: ALLOWED_HOSTS=neoscopio.com.br,www.neoscopio.com.br'
    )


# --- Aplicações -------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # postgres
    'django.contrib.postgres',

    # rest framework
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',

    # apps do projeto
    'neologismo',
    'usuario',
    'drf_spectacular',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

if not DEBUG:
    # WhiteNoise serve os estáticos do Django (admin e Swagger) sob gunicorn,
    # sem precisar de um Nginx apontando para STATIC_ROOT. Em desenvolvimento
    # o runserver já faz isso e o middleware só emitiria avisos.
    MIDDLEWARE.insert(2, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# --- Banco de dados ---------------------------------------------------------

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ImproperlyConfigured(
        'DATABASE_URL não definida. '
        'Ex.: postgres://usuario:senha@db:5432/banco_neologismo'
    )

DATABASES = {
    'default': dj_database_url.parse(
        DATABASE_URL,
        # Mantém a conexão aberta (melhora latência no Postgres).
        conn_max_age=env_int('DB_CONN_MAX_AGE', 600),
        conn_health_checks=True,
        ssl_require=env_bool('DB_SSL_REQUIRE', False),
    )
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Autenticação -----------------------------------------------------------

AUTH_USER_MODEL = 'usuario.Usuario'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Internacionalização ----------------------------------------------------

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# --- Arquivos estáticos -----------------------------------------------------

STATIC_URL = 'static/'
# Destino do collectstatic. Sem isso o comando falha e o admin fica sem CSS.
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        # Versiona e comprime os estáticos; em DEBUG usa o backend simples
        # para não exigir collectstatic durante o desenvolvimento.
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        ),
    },
}

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'


# --- Django REST Framework --------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        # Permite navegar pela API logado no /admin durante o desenvolvimento.
        'rest_framework.authentication.SessionAuthentication',
    ],

    # Leitura pública, escrita exige autenticação. Cada ViewSet restringe
    # mais que isso (dono do verbete ou staff) via permissões de objeto.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],

    # Paginação obrigatória: sem ela a Home baixaria a base inteira.
    'DEFAULT_PAGINATION_CLASS': 'config.pagination.PaginacaoPadrao',
    'PAGE_SIZE': env_int('API_PAGE_SIZE', 24),

    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': os.getenv('THROTTLE_ANON', '120/min'),
        'user': os.getenv('THROTTLE_USER', '600/min'),
        # Escopos específicos, aplicados nas views correspondentes.
        'login': os.getenv('THROTTLE_LOGIN', '10/min'),
        'cadastro': os.getenv('THROTTLE_CADASTRO', '10/hour'),
        'envio': os.getenv('THROTTLE_ENVIO', '30/hour'),
        'curtida': os.getenv('THROTTLE_CURTIDA', '120/min'),
    },

    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'API do Neoscópio',
    'DESCRIPTION': 'Dicionário colaborativo de neologismos do português brasileiro.',
    'VERSION': '2.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}


# --- CORS / CSRF ------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env_list(
    'CORS_ALLOWED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000' if DEBUG else ''
)

CSRF_TRUSTED_ORIGINS = env_list(
    'CSRF_TRUSTED_ORIGINS',
    'http://localhost:3000,http://127.0.0.1:3000' if DEBUG else ''
)

CORS_ALLOW_HEADERS = [
    'accept',
    'authorization',
    'content-type',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_ALLOW_METHODS = ['DELETE', 'GET', 'OPTIONS', 'PATCH', 'POST', 'PUT']


# --- Segurança em produção --------------------------------------------------

# Atrás do Caddy/Nginx, o Django só sabe que a request veio por HTTPS
# através deste header. Sem ele, SECURE_SSL_REDIRECT entra em loop.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'

    # HSTS: comece com um valor baixo (ex.: 3600) e suba para 31536000
    # depois de confirmar que o HTTPS está estável, porque o navegador
    # memoriza a diretiva e não há como desfazer rapidamente.
    SECURE_HSTS_SECONDS = env_int('SECURE_HSTS_SECONDS', 3600)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', True)
    SECURE_HSTS_PRELOAD = env_bool('SECURE_HSTS_PRELOAD', False)


# --- Logging ----------------------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'padrao': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'padrao',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.getenv('LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
