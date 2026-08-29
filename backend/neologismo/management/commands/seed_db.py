import csv
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from neologismo.models import Contexto, Neologismo
from usuario.models import Usuario


class Command(BaseCommand):
    help = 'Importa os neologismos do arquivo BancoDeNeologismos.csv'

    def handle(self, *args, **kwargs):
        csv_path = Path(__file__).resolve().parents[2] / 'data' / 'BancoDeNeologismos.csv'
        if not csv_path.exists():
            raise FileNotFoundError(f'Arquivo CSV não encontrado: {csv_path}')

        importador, _ = Usuario.objects.get_or_create(
            username='importador_csv',
            defaults={'email': 'importador-csv@neoscopio.local'},
        )
        importador.set_unusable_password()
        importador.save(update_fields=['password'])

        criados = 0
        atualizados = 0
        with csv_path.open(encoding='utf-8-sig', newline='') as csv_file:
            for row in csv.DictReader(csv_file, delimiter=';'):
                titulo = row['Neologismo'].strip()
                if not titulo:
                    continue

                contextos = [
                    {
                        'citacao': row[f'Contexto {numero}'].strip(),
                        'link': row[f'Fonte {numero}'].strip(),
                    }
                    for numero in range(1, 4)
                    if row[f'Contexto {numero}'].strip()
                ]
                data_registro = self.parse_data(row['Carimbo de data/hora'])
                defaults = {
                    'data_registro': data_registro,
                    'classe_gramatical': row['Classe gramatical'].strip(),
                    'tipologia': row['Tipologia'].strip(),
                    'elaborado_por': row['Elaborado por:'].strip(),
                    'definicao': 'Definição não disponível na fonte original.',
                    'contexto_uso': contextos[0]['citacao'] if contextos else '',
                    'tags': [row['Tipologia'].strip()] if row['Tipologia'].strip() else [],
                    'status': 'aprovado',
                }

                with transaction.atomic():
                    neologismo, criado = Neologismo.objects.update_or_create(
                        titulo=titulo,
                        autor=importador,
                        defaults=defaults,
                    )
                    neologismo.contextos.all().delete()
                    Contexto.objects.bulk_create(
                        [Contexto(neologismo=neologismo, **contexto) for contexto in contextos]
                    )

                criados += criado
                atualizados += not criado

        self.stdout.write(self.style.SUCCESS(
            f'Importação concluída: {criados} criados e {atualizados} atualizados.'
        ))

    @staticmethod
    def parse_data(valor):
        try:
            return timezone.make_aware(datetime.strptime(valor.strip(), '%d/%m/%Y %H:%M'))
        except (TypeError, ValueError):
            return None