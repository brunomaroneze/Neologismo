from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.text import slugify


class Neologismo(models.Model):
    # --- Sobre o neologismo ---

    # Metadados vindos da planilha original de neologismos (importação CSV).
    data_registro = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Data e hora de registro informada na fonte dos dados',
    )

    titulo = models.CharField(max_length=50, help_text='Nome do neologismo')
    slug = models.SlugField(
        max_length=70,
        blank=True,
        db_index=True,
        help_text='Versão do título usada na URL. Gerada automaticamente.',
    )
    definicao = models.TextField(help_text='Descrição completa do significado')
    contexto_uso = models.TextField(
        blank=True,
        help_text='Frase de exemplo demonstrando o uso',
    )

    classe_gramatical = models.CharField(
        max_length=50,
        help_text='Substantivo, Verbo, Adjetivo, etc.',
    )
    tipologia = models.CharField(
        max_length=100,
        blank=True,
        help_text='Processo de formação do neologismo. Ex: derivação prefixal',
    )
    elaborado_por = models.CharField(
        max_length=150,
        blank=True,
        help_text='Nome informado como elaborador na fonte dos dados',
    )

    # tags (array[str], opcional) - Usando ArrayField do Postgres
    tags = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        help_text='Lista de strings. Ex: ["Internetês", "Anglicismo"]',
    )

    # --- Moderação ---

    PENDENTE = 'pendente'
    APROVADO = 'aprovado'
    REJEITADO = 'rejeitado'

    STATUS_CHOICES = [
        (PENDENTE, 'Pendente'),
        (APROVADO, 'Aprovado'),
        (REJEITADO, 'Rejeitado'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDENTE,
        # Indexado porque toda listagem filtra por status.
        db_index=True,
    )

    motivo_rejeicao = models.TextField(
        blank=True,
        null=True,
        help_text='Texto explicativo do admin ao rejeitar',
    )
    reativado_em = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Data em que o admin reativou após rejeição',
    )
    moderado_em = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Data da última decisão de moderação',
    )
    moderado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='neologismos_moderados',
        help_text='Quem tomou a última decisão de moderação',
    )

    # --- Auditoria e relacionamentos ---

    data_criacao = models.DateTimeField(auto_now_add=True, db_index=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='meus_neologismos',
    )

    # --- Curtidas ---

    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='neologismos_curtidos',
        blank=True,
    )

    # Mantido por compatibilidade com os dados já gravados. A API pública e a
    # interface não expõem mais deslikes — o painel de moderação pode usar
    # este campo como sinal interno.
    deslikes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='neologismos_rejeitados',
        blank=True,
    )

    class Meta:
        ordering = ['-data_criacao']
        verbose_name = 'neologismo'
        verbose_name_plural = 'neologismos'
        indexes = [
            # A Home sempre pede "aprovados, mais recentes primeiro".
            models.Index(fields=['status', '-data_criacao'], name='neo_status_data_idx'),
        ]

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug and self.titulo:
            self.slug = slugify(self.titulo)[:70]
        super().save(*args, **kwargs)

    @property
    def total_likes(self):
        return self.likes.count()


class Contexto(models.Model):
    """Citação estruturada de uso de um neologismo (vários por verbete).

    O site original lista múltiplas citações com a fonte e link de origem.
    """

    neologismo = models.ForeignKey(
        Neologismo,
        on_delete=models.CASCADE,
        related_name='contextos',
    )
    citacao = models.TextField(help_text='Frase/trecho onde o neologismo aparece')
    fonte = models.CharField(
        max_length=200,
        blank=True,
        help_text='Quem disse ou onde foi publicado. Ex: "@usuario no X"',
    )
    link = models.URLField(
        max_length=500,
        blank=True,
        help_text='Link para a fonte original',
    )
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['data_criacao']
        verbose_name = 'contexto'
        verbose_name_plural = 'contextos'

    def __str__(self):
        return f'Contexto de {self.neologismo.titulo}'
