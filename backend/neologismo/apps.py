from django.apps import AppConfig


class NeologismoConfig(AppConfig):
    name = 'neologismo'

    def ready(self):
        from django.contrib.postgres.lookups import Unaccent
        from django.db.models import CharField, TextField

        from . import signals

        # Habilita `campo__unaccent__icontains` em todo texto do projeto.
        # Sem isto, buscar "voce" não encontra "você" e "cafe" não encontra
        # "cafezinho" — num dicionário de neologismos do português essa é a
        # falha de busca que mais aparece.
        #
        # O registro acontece aqui, uma vez, no carregamento dos apps:
        # `register_lookup` mexe na classe do campo, não na instância.
        CharField.register_lookup(Unaccent)
        TextField.register_lookup(Unaccent)

        signals.registrar()
