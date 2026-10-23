"""Invalidação do cache de facetas.

Ligado por sinal, e não dentro das views, para que a edição pelo /admin do
Django e os comandos de seed também derrubem a chave — do contrário a Home
ficaria até cinco minutos mostrando filtros que não correspondem mais ao
acervo.
"""

from django.db.models.signals import post_delete, post_save

from . import facetas
from .models import Neologismo


def registrar():
    post_save.connect(
        facetas.invalidar,
        sender=Neologismo,
        dispatch_uid='facetas_post_save',
    )
    post_delete.connect(
        facetas.invalidar,
        sender=Neologismo,
        dispatch_uid='facetas_post_delete',
    )
