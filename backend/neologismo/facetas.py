"""Índice de tags e classes gramaticais em uso, com contagem.

A Home monta os filtros a partir daqui, então esta função é chamada em todo
carregamento da página inicial. Como as tags vivem num ArrayField, não há
como o Postgres agrupá-las sozinho: é preciso trazer o array de cada verbete
aprovado e contar em Python. O resultado fica em cache — ele só muda quando
alguém publica, edita ou modera um verbete, e nesse momento o sinal em
`signals.py` invalida a chave.
"""

import unicodedata

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count

from .models import Neologismo

CHAVE_CACHE = 'neologismo:facetas:v1'


def normalizar(valor):
    """Reduz um texto à forma comparável: sem acento e sem caixa.

    Usada para casar ?tag=internetes com a tag gravada como "Internetês".
    """
    decomposto = unicodedata.normalize('NFKD', valor)
    sem_acento = ''.join(c for c in decomposto if not unicodedata.combining(c))
    return sem_acento.casefold().strip()


def calcular():
    aprovados = Neologismo.objects.filter(status=Neologismo.APROVADO)

    contagem_tags = {}
    for tags in aprovados.values_list('tags', flat=True):
        for tag in tags or []:
            contagem_tags[tag] = contagem_tags.get(tag, 0) + 1

    classes = (
        aprovados
        .values('classe_gramatical')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    return {
        'total': aprovados.count(),
        'tags': [
            {'nome': nome, 'total': total}
            for nome, total in sorted(
                contagem_tags.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        'classes': [
            {'nome': c['classe_gramatical'], 'total': c['total']}
            for c in classes
            if c['classe_gramatical']
        ],
    }


def obter():
    """Facetas vindas do cache, recalculando quando a chave expirou."""
    dados = cache.get(CHAVE_CACHE)
    if dados is None:
        dados = calcular()
        cache.set(CHAVE_CACHE, dados, settings.FACETAS_CACHE_TTL)
    return dados


def invalidar(**_):
    cache.delete(CHAVE_CACHE)


def canonizar_tag(tag):
    """Devolve a tag exatamente como está gravada no banco.

    `tags__contains=[...]` compara byte a byte, então um link com
    ?tag=internetes não casaria com "Internetês". Resolvemos pelo índice de
    facetas (que já está em cache) em vez de uma consulta com `unnest`, e
    devolvemos o valor original quando não há correspondência — aí o filtro
    simplesmente não acha nada, que é o resultado correto.
    """
    procurado = normalizar(tag)
    for faceta in obter()['tags']:
        if normalizar(faceta['nome']) == procurado:
            return faceta['nome']
    return tag
