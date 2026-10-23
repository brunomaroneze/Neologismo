"""Decisões de moderação, usadas pela API e pelo painel do site."""

from django.utils import timezone

from config.emails import avisar_verbete_aprovado, avisar_verbete_rejeitado

from .models import Neologismo


def _registrar(neologismo, moderador, avisar, **campos):
    for campo, valor in campos.items():
        setattr(neologismo, campo, valor)
    neologismo.moderado_em = timezone.now()
    neologismo.moderado_por = moderador
    neologismo.save()

    # O aviso ao autor é best-effort: `enviar_email` engole a exceção e
    # loga, então o SMTP fora do ar não impede a moderação de acontecer.
    avisar(neologismo)
    return neologismo


def aprovar(neologismo, moderador):
    return _registrar(
        neologismo, moderador, avisar_verbete_aprovado,
        status=Neologismo.APROVADO,
        motivo_rejeicao=None,
    )


def rejeitar(neologismo, moderador, motivo):
    return _registrar(
        neologismo, moderador, avisar_verbete_rejeitado,
        status=Neologismo.REJEITADO,
        motivo_rejeicao=motivo.strip(),
    )


def reativar(neologismo, moderador):
    """Volta um verbete rejeitado para aprovado."""
    return _registrar(
        neologismo, moderador, avisar_verbete_aprovado,
        status=Neologismo.APROVADO,
        motivo_rejeicao=None,
        reativado_em=timezone.now(),
    )
