"""Identificação de quem usa o site sem conta.

Curtir e enviar neologismos não exigem login: o visitante recebe um cookie
assinado com um identificador aleatório, e é por ele que o site sabe o que
essa pessoa já curtiu e quais envios são dela. Apagar o cookie é como trocar
de navegador: as curtidas continuam contadas, mas deixam de aparecer como
"minhas".
"""

import uuid

from django.conf import settings

COOKIE = 'neoscopio_visitante'
# O salt separa esta assinatura das outras feitas com a SECRET_KEY.
SALT = 'web.visitante'
DURACAO = 2 * 365 * 24 * 3600


def obter(request):
    """Identificador do visitante, ou None se ele ainda não tem o cookie."""
    if hasattr(request, '_visitante'):
        return request._visitante
    # Cookie adulterado ou assinado com outra chave vale como ausente.
    return request.get_signed_cookie(COOKIE, default=None, salt=SALT, max_age=DURACAO)


def garantir(request):
    """Devolve o identificador, criando um se preciso (gravado por `gravar`)."""
    visitante = obter(request)
    if not visitante:
        visitante = uuid.uuid4().hex
        request._visitante = visitante
    return visitante


def gravar(request, resposta):
    """Renova o cookie na resposta, para ele só expirar após dois anos parado."""
    visitante = obter(request)
    if visitante:
        resposta.set_signed_cookie(
            COOKIE, visitante, salt=SALT, max_age=DURACAO,
            secure=settings.SESSION_COOKIE_SECURE, httponly=True, samesite='Lax',
        )
    return resposta
