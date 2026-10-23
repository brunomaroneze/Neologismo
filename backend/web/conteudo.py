"""Conteúdo fixo das páginas institucionais.

Textos idênticos aos do frontend anterior.
"""

# A equipe fica no banco (web.models.MembroEquipe) e é gerida pelo painel.

# Referências em formato ABNT (autor, ano, título, fonte).
REFERENCIAS = [
    {'autoria': 'ALVES, Ieda Maria.', 'titulo': 'Neologismo: criação lexical.',
     'publicacao': '3. ed. São Paulo: Ática, 2007.'},
    {'autoria': 'BASÍLIO, Margarida.', 'titulo': 'Formação e classes de palavras no português do Brasil.',
     'publicacao': 'São Paulo: Contexto, 2004.'},
    {'autoria': 'CARVALHO, Nelly.', 'titulo': 'Empréstimos linguísticos na língua portuguesa.',
     'publicacao': 'São Paulo: Cortez, 2009.'},
    {'autoria': 'CORREIA, Margarita; ALMEIDA, Gladis Maria de Barcellos.', 'titulo': 'Neologia em português.',
     'publicacao': 'São Paulo: Parábola Editorial, 2012.'},
    {'autoria': 'HOUAISS, Antônio; VILLAR, Mauro de Salles.', 'titulo': 'Dicionário Houaiss da língua portuguesa.',
     'publicacao': 'Rio de Janeiro: Objetiva, 2009.'},
    {'autoria': 'ACADEMIA BRASILEIRA DE LETRAS.', 'titulo': 'Vocabulário Ortográfico da Língua Portuguesa (VOLP).',
     'publicacao': '6. ed. Rio de Janeiro: ABL, 2021.',
     'url': 'https://www.academia.org.br/nossa-lingua/busca-no-vocabulario'},
    {'autoria': 'SAUSSURE, Ferdinand de.', 'titulo': 'Curso de linguística geral.',
     'publicacao': '27. ed. São Paulo: Cultrix, 2006.'},
]

PASSOS = [
    {'titulo': 'Registre',
     'texto': 'Cadastre uma palavra nova com definição, classe gramatical, exemplos de uso e até citações com fonte.'},
    {'titulo': 'Explore',
     'texto': 'Navegue e pesquise pelos neologismos já registrados, filtrando por categorias como internetês, anglicismo e gíria.'},
    {'titulo': 'Discuta',
     'texto': 'Curta, comente e ajude a comunidade a entender como e onde cada palavra está sendo usada.'},
]

OBJETIVOS = [
    {'titulo': 'Linguagem viva',
     'texto': 'Tratar o português como ele realmente é: uma língua viva, moldada todos os dias por quem fala.'},
    {'titulo': 'Registro confiável',
     'texto': 'Cada sugestão passa por moderação antes de ser publicada, garantindo qualidade e seriedade ao acervo.'},
    {'titulo': 'Colaboração aberta',
     'texto': 'Qualquer pessoa pode contribuir. O banco de neologismos cresce com a participação de toda a comunidade.'},
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
