"""Traz para o banco as referências que ficavam fixas em web/conteudo.py."""

from datetime import datetime, timezone

from django.db import migrations

AREAS = [
    ('Neologia e criação lexical', 'ameixa'),
    ('Formação de palavras', 'malva'),
    ('Empréstimos linguísticos', 'ceu'),
    ('Lexicografia e dicionários', 'lilas'),
    ('Teoria linguística', 'tinta'),
]

# (área, categoria, autoria, título, ano, detalhes, url)
REFERENCIAS = [
    ('Neologia e criação lexical', 'livro', 'ALVES, Ieda Maria',
     'Neologismo: criação lexical', 2007, '3. ed. São Paulo: Ática', ''),
    ('Formação de palavras', 'livro', 'BASÍLIO, Margarida',
     'Formação e classes de palavras no português do Brasil', 2004, 'São Paulo: Contexto', ''),
    ('Empréstimos linguísticos', 'livro', 'CARVALHO, Nelly',
     'Empréstimos linguísticos na língua portuguesa', 2009, 'São Paulo: Cortez', ''),
    ('Neologia e criação lexical', 'livro', 'CORREIA, Margarita; ALMEIDA, Gladis Maria de Barcellos',
     'Neologia em português', 2012, 'São Paulo: Parábola Editorial', ''),
    ('Lexicografia e dicionários', 'dicionario', 'HOUAISS, Antônio; VILLAR, Mauro de Salles',
     'Dicionário Houaiss da língua portuguesa', 2009, 'Rio de Janeiro: Objetiva', ''),
    ('Lexicografia e dicionários', 'dicionario', 'ACADEMIA BRASILEIRA DE LETRAS',
     'Vocabulário Ortográfico da Língua Portuguesa (VOLP)', 2021, '6. ed. Rio de Janeiro: ABL',
     'https://www.academia.org.br/nossa-lingua/busca-no-vocabulario'),
    ('Teoria linguística', 'livro', 'SAUSSURE, Ferdinand de',
     'Curso de linguística geral', 2006, '27. ed. São Paulo: Cultrix', ''),
]

# Data fixa no passado: as referências de sempre não devem sair como "nova".
DATA_INICIAL = datetime(2026, 1, 1, 15, tzinfo=timezone.utc)


def criar(apps, schema_editor):
    AreaTematica = apps.get_model('web', 'AreaTematica')
    Referencia = apps.get_model('web', 'Referencia')
    areas = {
        nome: AreaTematica.objects.get_or_create(nome=nome, defaults={'cor': cor})[0]
        for nome, cor in AREAS
    }
    for area, categoria, autoria, titulo, ano, detalhes, url in REFERENCIAS:
        if Referencia.objects.filter(titulo=titulo).exists():
            continue
        Referencia.objects.create(
            area=areas[area], categoria=categoria, autoria=autoria, titulo=titulo,
            ano=ano, detalhes=detalhes, url=url,
        )
    Referencia.objects.update(criada_em=DATA_INICIAL)


class Migration(migrations.Migration):
    dependencies = [('web', '0004_indicacoes_de_leitura')]

    operations = [migrations.RunPython(criar, migrations.RunPython.noop)]
