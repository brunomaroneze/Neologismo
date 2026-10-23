from django import template
from django.template.defaultfilters import date as formatar_data
from django.utils.html import format_html

from neologismo.facetas import normalizar

register = template.Library()

# Abreviaturas lexicográficas usuais (Houaiss, Aurélio). Se alguma palavra da
# classe não estiver aqui, a classe é mostrada por extenso: abreviar pela
# metade confundiria mais do que ajudaria.
ABREVIATURAS = {
    'substantivo': 's.',
    'masculino': 'm.',
    'feminino': 'f.',
    'uniforme': 'unif.',
    'verbo': 'v.',
    'transitivo': 't.',
    'intransitivo': 'int.',
    'direto': 'd.',
    'indireto': 'i.',
    'pronominal': 'pron.',
    'adjetivo': 'adj.',
    'adverbio': 'adv.',
    'interjeicao': 'interj.',
    'locucao': 'loc.',
    'substantiva': 'subst.',
    'adjetiva': 'adj.',
    'adverbial': 'adv.',
    'verbal': 'v.',
    'e': 'e',
}


@register.filter
def abreviar_classe(classe):
    """'SUBSTANTIVO FEMININO' -> <abbr title="substantivo feminino">s. f.</abbr>"""
    extenso = ' '.join((classe or '').lower().split())
    if not extenso:
        return ''
    partes = [ABREVIATURAS.get(normalizar(palavra)) for palavra in extenso.split()]
    if not all(partes):
        return extenso
    return format_html('<abbr title="{}">{}</abbr>', extenso, ' '.join(partes))


@register.filter
def data_extenso(valor):
    """'23 de outubro de 2026' — em português o mês vai em minúscula."""
    if not valor:
        return ''
    return formatar_data(valor, r'j \d\e F \d\e Y').lower()


@register.filter
def data_curta(valor):
    """'02 de set. de 2026', o mesmo formato do toLocaleDateString do site antigo."""
    if not valor:
        return ''
    return formatar_data(valor, r'd \d\e b. \d\e Y').lower()


@register.simple_tag(takes_context=True)
def consulta(context, **alteracoes):
    """Querystring atual com as alterações pedidas.

    Valor vazio remove o parâmetro. Qualquer mudança de filtro volta para a
    primeira página, a menos que a própria `pagina` seja a alteração.
    """
    params = context['request'].GET.copy()
    if 'pagina' not in alteracoes:
        params.pop('pagina', None)
    for chave, valor in alteracoes.items():
        if valor in ('', None):
            params.pop(chave, None)
        else:
            params[chave] = valor
    texto = params.urlencode()
    return f'?{texto}' if texto else '?'
