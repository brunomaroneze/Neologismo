import json
import unicodedata
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from web.models import MembroEquipe

ARQUIVO = Path(__file__).resolve().parents[2] / 'data' / 'equipe.json'


def palavras(nome):
    """'Prof. Rômulo Ferreira - UFGD' -> {'romulo', 'ferreira'}."""
    nome = nome.split(' - ')[0].replace('Prof. ', '')
    sem_acento = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode()
    return set(sem_acento.lower().split())


class Command(BaseCommand):
    help = (
        'Sincroniza a página Equipe com web/data/equipe.json. Quem já está no '
        'banco é reconhecido pelo nome (o nome curto antigo contido no nome '
        'completo) e mantém foto e bio. Ninguém é apagado.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--simular',
            action='store_true',
            help='Mostra o que mudaria sem gravar nada.',
        )

    def handle(self, *args, **options):
        dados = json.loads(ARQUIVO.read_text(encoding='utf-8'))
        existentes = list(MembroEquipe.objects.all())
        usados = set()
        relatorio = {'atualizados': [], 'criados': []}

        with transaction.atomic():
            for grupo in (MembroEquipe.INTEGRANTE, MembroEquipe.EX_INTEGRANTE):
                for ordem, pessoa in enumerate(dados[grupo]):
                    alvo = palavras(pessoa['nome'])
                    candidatos = [
                        m for m in existentes
                        if m.pk not in usados and palavras(m.nome) <= alvo
                    ]
                    if len(candidatos) == 1:
                        membro = candidatos[0]
                        usados.add(membro.pk)
                        relatorio['atualizados'].append(f'{membro.nome} -> {pessoa["nome"]}')
                    else:
                        # Nenhum ou mais de um parecido: cria em vez de arriscar
                        # trocar a foto de uma pessoa pela de outra.
                        membro = MembroEquipe()
                        relatorio['criados'].append(pessoa['nome'])
                    membro.nome = pessoa['nome']
                    membro.funcao = pessoa['funcao']
                    membro.grupo = grupo
                    membro.ordem = ordem
                    membro.ativo = True
                    if not options['simular']:
                        membro.save()
            if options['simular']:
                transaction.set_rollback(True)

        fora = [m.nome for m in existentes if m.pk not in usados]
        prefixo = '(simulação) ' if options['simular'] else ''
        self.stdout.write(self.style.SUCCESS(
            f'{prefixo}Atualizados {len(relatorio["atualizados"])}, '
            f'criados {len(relatorio["criados"])}.'
        ))
        for linha in relatorio['atualizados']:
            self.stdout.write(f'  = {linha}')
        for nome in relatorio['criados']:
            self.stdout.write(f'  + {nome}')
        if fora:
            self.stdout.write(self.style.WARNING(
                'Não estão no arquivo e ficaram como estavam: ' + ', '.join(fora)
            ))
