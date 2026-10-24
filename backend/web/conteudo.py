"""Conteúdo fixo das páginas institucionais.

Textos idênticos aos do frontend anterior.
"""

# A equipe fica no banco (web.models.MembroEquipe) e é gerida pelo painel.

# As indicações de leitura ficam no banco (web.models.Referencia) e são
# geridas pelo painel.

PASSOS = [
    {
        'titulo': 'Registre',
        'texto': (
            'Cadastre uma palavra nova com definição, classe gramatical, '
            'exemplos de uso e até citações com fonte.'
        ),
    },
    {
        'titulo': 'Explore',
        'texto': (
            'Navegue e pesquise pelos neologismos já registrados, filtrando '
            'por categorias como internetês, anglicismo e gíria.'
        ),
    },
    {
        'titulo': 'Discuta',
        'texto': (
            'Curta, comente e ajude a comunidade a entender como e onde cada '
            'palavra está sendo usada.'
        ),
    },
]

OBJETIVOS = [
    {
        'titulo': 'Linguagem viva',
        'texto': (
            'Tratar o português como ele realmente é: uma língua viva, '
            'moldada todos os dias por quem fala.'
        ),
    },
    {
        'titulo': 'Registro confiável',
        'texto': (
            'Cada sugestão passa por moderação antes de ser publicada, '
            'garantindo qualidade e seriedade ao acervo.'
        ),
    },
    {
        'titulo': 'Colaboração aberta',
        'texto': (
            'Qualquer pessoa pode contribuir. O banco de neologismos cresce '
            'com a participação de toda a comunidade.'
        ),
    },
]

# Sugestões do campo de classe gramatical no formulário de envio.
CLASSES_GRAMATICAIS = [
    'Substantivo',
    'Substantivo uniforme',
    'Verbo transitivo direto',
    'Verbo intransitivo',
    'Adjetivo',
    'Adjetivo uniforme',
    'Advérbio',
    'Interjeição',
    'Locução',
]
