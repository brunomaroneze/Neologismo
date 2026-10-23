"""Leva a equipe, até aqui fixa em web/conteudo.py, para o banco.

As fotos que estavam em web/static/web/equipe/ são copiadas para o armazenamento
de mídia, de onde o painel passa a gerenciá-las.
"""

from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import migrations
from django.utils.text import slugify

EQUIPE = [
    ('Prof. Ana Maria Ribeiro', 'Coordenadora', 'Rock sempre. Samba às vezes. Sertanejo nunca.'),
    ('Fernanda Assef', 'Graduanda em Letras', 'Absolutamente viciada em trabalhar e jamais recusa um docinho.'),
    ('Julia Magnavita', 'Graduanda em Letras', 'A vida já me ensinou muita coisa, mas preferia ter continuado burra.'),
    ('Matheus Lima', 'Graduado em Letras', 'Fui tentar me encontrar e me perdi mais ainda.'),
    ('Amanda Candido', 'Graduanda em Letras', 'Vivendo para encontrar a linha entre café insuficiente e café demais.'),
    ('Igor Varejão', 'Graduando em Ciência da Computação', 'O terror dos sites de notícias.'),
    ('Karina Marques', 'Graduanda em Letras', 'Uma estudante de letras quase terminando o alfabeto.'),
    ('Pyetra Werneck', 'Graduanda em Letras', 'Mergulhada no café quente, me entrelaço entre as Letras, a vida fitness, a Moda e o sol poente.'),
    ('Beatriz Latini - UFMG', 'Doutoranda em Letras', 'Neolover. Bookstan. A recatada e do lar, só que não!'),
    ('João Colombo', 'Graduando em Letras', 'Aspirante a ex-carrossel.'),
    ('Luis Eduardo', 'Graduando em Ciência da Computação', ''),
    ('Rômulo Ferreira', 'Graduando em Letras', 'Ama criar listas de reprodução no Spotify e pseudo crítico de cinema.'),
    ('João Victor Ifran', 'Desenvolvedor full stack', 'Responsável pela arquitetura do projeto, integração entre frontend e API e pela experiência de uso da plataforma.'),
    ('Bruno Maroneze - UFGD', 'professor', ''),
]

PASTA_FOTOS = Path(settings.BASE_DIR) / 'web' / 'static' / 'web' / 'equipe'


def criar_equipe(apps, schema_editor):
    MembroEquipe = apps.get_model('web', 'MembroEquipe')
    if MembroEquipe.objects.exists():
        return

    for ordem, (nome, funcao, bio) in enumerate(EQUIPE, start=1):
        membro = MembroEquipe(nome=nome, funcao=funcao, bio=bio, ordem=ordem * 10)
        slug = slugify(nome.split(' - ')[0].replace('Prof. ', ''))
        arquivo = PASTA_FOTOS / f'{slug}.jpg'
        if arquivo.exists():
            membro.foto.save(
                'foto.jpg',
                ContentFile(arquivo.read_bytes()),
                save=False,
            )
        membro.save()


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0001_membro_equipe'),
    ]

    operations = [
        migrations.RunPython(criar_equipe, migrations.RunPython.noop),
    ]
