"""Conteúdo fixo das páginas institucionais."""

# A equipe fica no banco (web.models.MembroEquipe) e é gerida pelo painel.

# As indicações de leitura ficam no banco (web.models.Referencia) e são
# geridas pelo painel.

PASSOS = [
    {
        'titulo': 'Registre',
        'texto': (
            'Cadastre a palavra com a definição e a classe gramatical. Se '
            'tiver, inclua um exemplo de uso e citações com fonte.'
        ),
    },
    {
        'titulo': 'Explore',
        'texto': (
            'Pesquise os neologismos já registrados e filtre por tags como '
            'internetês ou anglicismo.'
        ),
    },
    {
        'titulo': 'Discuta',
        'texto': (
            'Curta as palavras que você já ouviu por aí e mande citações que '
            'mostrem onde cada uma aparece.'
        ),
    },
]

OBJETIVOS = [
    {
        'titulo': 'Linguagem viva',
        'texto': (
            'Registrar o português como ele é falado hoje, sem esperar que a '
            'palavra chegue ao dicionário.'
        ),
    },
    {
        'titulo': 'Registro confiável',
        'texto': (
            'Toda sugestão passa pela equipe antes de ser publicada. Entra no '
            'banco o que tem definição clara e, de preferência, fonte.'
        ),
    },
    {
        'titulo': 'Colaboração aberta',
        'texto': (
            'Qualquer pessoa pode enviar uma palavra. Basta criar uma conta.'
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
