"""Consulta ao acervo de indicações de leitura.

Toda a filtragem acontece aqui, no servidor, a partir da querystring: a
página funciona como formulário comum sem JavaScript, e o neoscopio.js só
troca a tabela sem recarregar a página.
"""

import re
from dataclasses import dataclass, field
from datetime import timedelta

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone

from .models import AreaTematica, Referencia

POR_PAGINA = [10, 25, 50, 100]
POR_PAGINA_PADRAO = 25
DIAS_NOVA = 30

# parâmetro -> campo de ordenação (o 2º critério desempata)
ORDENS = {
    'area': ('area__nome', 'autoria'),
    'categoria': ('categoria', 'autoria'),
    'autor': ('autoria', 'ano'),
    'titulo': ('titulo', 'autoria'),
    'ano': ('ano', 'autoria'),
    'adicao': ('criada_em', 'id'),
}
ORDEM_PADRAO = '-adicao'

ANO = re.compile(r'^\s*(\d{4})\s*(?:[-–a]\s*(\d{4})\s*)?$')


@dataclass
class Consulta:
    areas: list = field(default_factory=list)
    categorias: list = field(default_factory=list)
    autor: str = ''
    titulo: str = ''
    ano: str = ''
    busca: str = ''
    ordem: str = ORDEM_PADRAO
    por_pagina: int = POR_PAGINA_PADRAO

    @property
    def filtrando(self):
        return any([self.areas, self.categorias, self.autor, self.titulo, self.ano, self.busca])

    def proxima_ordem(self, coluna):
        """Clicar na coluna já ordenada inverte o sentido."""
        if self.ordem == coluna:
            return f'-{coluna}'
        if self.ordem == f'-{coluna}':
            return coluna
        return '-adicao' if coluna == 'adicao' else coluna

    def sentido(self, coluna):
        if self.ordem == coluna:
            return 'ascending'
        if self.ordem == f'-{coluna}':
            return 'descending'
        return ''


def ler_consulta(params):
    validas = {str(pk) for pk in AreaTematica.objects.values_list('pk', flat=True)}
    categorias = {valor for valor, _ in Referencia.CATEGORIAS}
    ordem = params.get('ordem', ORDEM_PADRAO)
    if ordem.lstrip('-') not in ORDENS:
        ordem = ORDEM_PADRAO
    try:
        por_pagina = int(params.get('por_pagina', POR_PAGINA_PADRAO))
    except ValueError:
        por_pagina = POR_PAGINA_PADRAO
    if por_pagina not in POR_PAGINA:
        por_pagina = POR_PAGINA_PADRAO
    return Consulta(
        areas=[a for a in params.getlist('area') if a in validas],
        categorias=[c for c in params.getlist('categoria') if c in categorias],
        autor=params.get('autor', '').strip()[:100],
        titulo=params.get('titulo', '').strip()[:100],
        ano=params.get('ano', '').strip()[:20],
        busca=params.get('q', '').strip()[:100],
        ordem=ordem,
        por_pagina=por_pagina,
    )


def filtrar(consulta):
    qs = Referencia.objects.select_related('area')
    if consulta.areas:
        qs = qs.filter(area__in=consulta.areas)
    if consulta.categorias:
        qs = qs.filter(categoria__in=consulta.categorias)
    if consulta.autor:
        qs = qs.filter(autoria__unaccent__icontains=consulta.autor)
    if consulta.titulo:
        qs = qs.filter(titulo__unaccent__icontains=consulta.titulo)
    if consulta.ano:
        # "2009" ou um intervalo, "2000-2010"
        achado = ANO.match(consulta.ano)
        if achado:
            inicio, fim = achado.group(1), achado.group(2) or achado.group(1)
            qs = qs.filter(ano__gte=min(inicio, fim), ano__lte=max(inicio, fim))
        else:
            qs = qs.none()
    if consulta.busca:
        termo = consulta.busca
        qs = qs.filter(
            Q(autoria__unaccent__icontains=termo)
            | Q(titulo__unaccent__icontains=termo)
            | Q(publicado_em__unaccent__icontains=termo)
            | Q(detalhes__unaccent__icontains=termo)
            | Q(area__nome__unaccent__icontains=termo)
        )
    campos = ORDENS[consulta.ordem.lstrip('-')]
    prefixo = '-' if consulta.ordem.startswith('-') else ''
    return qs.order_by(*(prefixo + c for c in campos))


def pagina(consulta, numero):
    return Paginator(filtrar(consulta), consulta.por_pagina).get_page(numero)


def areas_com_contagem():
    return AreaTematica.objects.annotate(total=Count('referencias')).order_by('nome')


def limite_nova():
    return timezone.now() - timedelta(days=DIAS_NOVA)
