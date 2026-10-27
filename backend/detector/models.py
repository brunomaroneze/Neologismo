from django.conf import settings
from django.db import models


class PalavraLexico(models.Model):
    """Palavra já dicionarizada: o que está aqui não é candidato a neologismo.

    Carregada de detector/dados/lexico.txt.gz pelo comando importar_lexico.
    """

    palavra = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'palavra do léxico'
        verbose_name_plural = 'palavras do léxico'

    def __str__(self):
        return self.palavra


class PalavraIgnorada(models.Model):
    """Palavra que a moderação marcou como "não é neologismo" (falso positivo).

    Some das próximas análises, sem mexer no léxico original.
    """

    palavra = models.CharField(max_length=100, unique=True)
    marcada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['palavra']
        verbose_name = 'palavra ignorada'
        verbose_name_plural = 'palavras ignoradas'

    def __str__(self):
        return self.palavra
