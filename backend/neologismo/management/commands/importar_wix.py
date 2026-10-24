import json
from datetime import date, datetime, time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from neologismo.models import Contexto, Neologismo
from usuario.models import Usuario

ARQUIVO = Path(__file__).resolve().parents[2] / 'data' / 'neologismos_wix.json'


class Command(BaseCommand):
    help = (
        'Importa os neologismos que só existiam no site antigo (Wix), lidos de '
        'neologismos_wix.json. Verbete com o mesmo título já no banco, em '
        'qualquer status, é mantido como está.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--simular',
            action='store_true',
            help='Mostra o que seria importado sem gravar nada.',
        )

    def handle(self, *args, **options):
        verbetes = json.loads(ARQUIVO.read_text(encoding='utf-8'))

        # Mesmo autor dos verbetes vindos da planilha: são o mesmo acervo.
        importador, criado = Usuario.objects.get_or_create(
            username='importador_csv',
            defaults={'email': 'importador-csv@neoscopio.local'},
        )
        if criado:
            importador.set_unusable_password()
            importador.save(update_fields=['password'])

        criados, mantidos = [], []
        for dados in verbetes:
            titulo = dados['titulo']
            if Neologismo.objects.filter(titulo__iexact=titulo).exists():
                mantidos.append(titulo)
                continue
            criados.append(titulo)
            if options['simular']:
                continue

            contextos = dados['contextos']
            with transaction.atomic():
                neologismo = Neologismo.objects.create(
                    titulo=titulo,
                    autor=importador,
                    status=Neologismo.APROVADO,
                    data_registro=timezone.make_aware(
                        datetime.combine(date.fromisoformat(dados['data_registro']), time())
                    ),
                    classe_gramatical=dados['classe_gramatical'],
                    tipologia=dados['tipologia'],
                    # Igual à planilha: o site antigo não tinha definição, e as
                    # tags seguem a tipologia, como no resto do acervo.
                    definicao='Definição não disponível na fonte original.',
                    contexto_uso=contextos[0]['citacao'] if contextos else '',
                    tags=[dados['tipologia']] if dados['tipologia'] else [],
                )
                Contexto.objects.bulk_create([
                    Contexto(neologismo=neologismo, **contexto) for contexto in contextos
                ])

        verbo = 'Seriam criados' if options['simular'] else 'Criados'
        self.stdout.write(self.style.SUCCESS(f'{verbo} {len(criados)}: {", ".join(criados)}'))
        if mantidos:
            self.stdout.write(self.style.WARNING(
                f'Já existiam, mantidos sem alteração ({len(mantidos)}): {", ".join(mantidos)}'
            ))
