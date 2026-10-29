"""Consultas de verbetes compartilhadas pela API e pelas páginas do site.

A API (NeologismoViewSet) e as views do app `web` filtram e anotam os
verbetes do mesmo jeito; manter as regras num lugar só evita que a busca da
página inicial e a da API passem a dar resultados diferentes.
"""

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, IntegerField, OuterRef, Q, Subquery, TextField
from django.db.models.functions import Cast, Coalesce

from . import facetas as indice_facetas
from .models import CurtidaAnonima, Neologismo

ORDENACOES = {
    'recentes': ['-data_criacao', '-id'],
    'antigos': ['data_criacao', 'id'],
    'populares': ['-likes_count', '-data_criacao'],
    'alfabetica': ['titulo', 'id'],
}


def anotados(usuario, visitante=None):
    """Queryset com as contagens e a curtida do usuário já anotadas.

    As contagens vêm anotadas em vez de `obj.likes.count()` para não
    disparar uma query por verbete renderizado. `visitante` é o cookie de
    quem navega sem conta (web/visitante.py) e decide `curtido_por_mim`
    quando não há usuário logado.
    """
    # Subquery, e não um terceiro Count com join: somado aos joins de likes
    # e deslikes, ele multiplicaria as linhas agrupadas por verbete.
    anonimas = Coalesce(
        Subquery(
            CurtidaAnonima.objects.filter(neologismo=OuterRef('pk'))
            .order_by().values('neologismo')
            .annotate(total=Count('pk')).values('total'),
            output_field=IntegerField(),
        ),
        0,
    )
    qs = (
        Neologismo.objects
        .select_related('autor', 'moderado_por')
        .prefetch_related('contextos')
        .annotate(
            likes_count=Count('likes', distinct=True) + anonimas,
            deslikes_count=Count('deslikes', distinct=True),
        )
        # Ordem explícita: sem ela a paginação pode repetir ou pular itens
        # entre páginas.
        .order_by('-data_criacao', '-id')
    )

    if usuario.is_authenticated:
        qs = qs.annotate(
            curtido_por_mim=Exists(
                get_user_model().objects.filter(
                    pk=usuario.pk,
                    neologismos_curtidos=OuterRef('pk'),
                )
            )
        )
    elif visitante:
        qs = qs.annotate(
            curtido_por_mim=Exists(
                CurtidaAnonima.objects.filter(
                    neologismo=OuterRef('pk'), visitante=visitante,
                )
            )
        )

    return qs


def filtrar(qs, busca='', tag='', classe='', letra='', ordem=''):
    """Aplica os filtros públicos de busca, tag, classe, inicial e ordem."""
    busca = (busca or '').strip()
    if busca:
        # `unaccent` resolve o acento e `icontains` a caixa: quem digita
        # "voce" acha "você" e quem digita "GÍRIA" acha "gíria". As tags
        # são um ArrayField, que o Postgres não aceita em lookup de texto
        # — o cast para text transforma ["Internetês", "Gíria"] numa
        # string pesquisável pelo mesmo caminho.
        qs = qs.annotate(tags_texto=Cast('tags', TextField())).filter(
            Q(titulo__unaccent__icontains=busca)
            | Q(definicao__unaccent__icontains=busca)
            | Q(contexto_uso__unaccent__icontains=busca)
            | Q(tags_texto__unaccent__icontains=busca)
        )

    tag = (tag or '').strip()
    if tag and tag.lower() != 'all':
        # A tag precisa casar com o valor gravado; `canonizar_tag` aceita
        # a versão sem acento que aparece em links copiados à mão.
        qs = qs.filter(tags__contains=[indice_facetas.canonizar_tag(tag)])

    classe = (classe or '').strip()
    if classe:
        qs = qs.filter(classe_gramatical__unaccent__icontains=classe)

    letra = (letra or '').strip()
    if len(letra) == 1 and letra.isalpha():
        # "á" e "a" caem na mesma letra do índice.
        qs = qs.filter(titulo__unaccent__istartswith=letra)

    ordenacao = ORDENACOES.get(ordem or '')
    if ordenacao:
        qs = qs.order_by(*ordenacao)

    return qs
