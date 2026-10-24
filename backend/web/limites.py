"""Limite de tentativas para os formulários do site.

A API tem os throttles do DRF; os formulários HTML do site não passam por
eles. Sem isto, curtir e enviar verbetes pelo site não teriam limite. Usa o
mesmo cache do throttle do DRF (tabela no Postgres em produção), então o
limite vale para todos os workers do gunicorn.
"""

from django.core.cache import cache

# escopo: (tentativas, janela em segundos) — os mesmos valores da API.
# Login, cadastro e senha ficam com os limites do próprio allauth
# (ACCOUNT_RATE_LIMITS); aqui só o que é do site.
LIMITES = {
    'envio': (30, 3600),
    'curtida': (120, 60),
}


def _ip(request):
    # Atrás do nginx o IP real chega em X-Real-IP; o backend só escuta em
    # 127.0.0.1, então o header não pode ser forjado por quem vem de fora.
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '')


def excedeu(request, escopo):
    """Conta uma tentativa e diz se o limite do escopo foi ultrapassado."""
    tentativas, janela = LIMITES[escopo]
    quem = request.user.pk if request.user.is_authenticated else _ip(request)
    chave = f'web:limite:{escopo}:{quem}'

    # `add` só cria se não existir: a janela começa na primeira tentativa.
    if cache.add(chave, 1, janela):
        return False
    try:
        return cache.incr(chave) > tentativas
    except ValueError:
        # A chave expirou entre o `add` e o `incr`.
        cache.add(chave, 1, janela)
        return False
