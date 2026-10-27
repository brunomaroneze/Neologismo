"""Carrega o léxico (≈480 mil palavras) de detector/dados/lexico.txt.gz.

    python manage.py importar_lexico            # recarrega tudo
    python manage.py importar_lexico --se-vazio # só se a tabela estiver vazia

O entrypoint do container roda a versão --se-vazio a cada start, então o
primeiro deploy carrega o léxico e os seguintes não fazem nada.
"""

import gzip
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from detector.models import PalavraLexico

ARQUIVO = Path(__file__).resolve().parents[2] / 'dados' / 'lexico.txt.gz'
LOTE = 5000


class Command(BaseCommand):
    help = 'Importa o léxico usado pelo detector de neologismos.'

    def add_arguments(self, parser):
        parser.add_argument('--se-vazio', action='store_true',
                            help='Não faz nada se o léxico já estiver carregado.')

    def handle(self, *args, se_vazio=False, **options):
        if se_vazio and PalavraLexico.objects.exists():
            self.stdout.write('Léxico já carregado.')
            return

        with gzip.open(ARQUIVO, 'rt', encoding='utf-8') as arquivo:
            palavras = {linha.strip() for linha in arquivo if linha.strip()}
        # Grafias anteriores ao Acordo Ortográfico ("lingüista") valem também
        # sem o trema, que é como o detector procura.
        palavras = sorted(palavras | {p.replace('ü', 'u') for p in palavras if 'ü' in p})

        with transaction.atomic():
            PalavraLexico.objects.all().delete()
            for inicio in range(0, len(palavras), LOTE):
                PalavraLexico.objects.bulk_create(
                    [PalavraLexico(palavra=p) for p in palavras[inicio:inicio + LOTE]],
                    ignore_conflicts=True,
                )

        self.stdout.write(self.style.SUCCESS(f'Léxico carregado: {len(palavras)} palavras.'))
