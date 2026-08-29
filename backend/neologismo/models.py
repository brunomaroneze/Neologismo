from django.contrib.auth.models import AbstractUser
from django.db import models
#from django.core.validators import MinValueValidator
from django.conf import settings
from django.contrib.postgres.fields import ArrayField

# Create your models here.
class Neologismo (models.Model):
    #sobre o neologismo

    data_registro = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Data e hora de registro informada na fonte dos dados'
    )

    #campos antigos que mudaram de nome
    titulo = models.CharField(max_length=50, help_text='Nome do neologismo')
    definicao = models.TextField(help_text='Descrição completa do significado') 
    contexto_uso = models.TextField(help_text='Frase de exemplo demonstrando o uso') 
    
    #novos campos
    classe_gramatical = models.CharField(max_length=50, help_text='Substantivo, Verbo, Adjetivo, etc.')
    tipologia = models.CharField(
        max_length=100,
        blank=True,
        help_text='Processo de formação do neologismo. Ex: derivação prefixal'
    )
    elaborado_por = models.CharField(
        max_length=150,
        blank=True,
        help_text='Nome informado como elaborador na fonte dos dados'
    )
    
    # tags (array[str], opcional) - Usando ArrayField do Postgres
    tags = ArrayField(
        models.CharField(max_length=50), 
        blank=True, 
        default=list,
        help_text='Lista de strings. Ex: ["Internetês", "Anglicismo"]'
    )

    # Status de Moderação (Enum)
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aprovado', 'Aprovado'),
        ('rejeitado', 'Rejeitado'),
    ]
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
          default='pendente'
    )
    
    # Campos de Moderação (Novos v2.0)
    motivo_rejeicao = models.TextField(blank=True, null=True, help_text='Texto explicativo do admin ao rejeitar')
    reativado_em = models.DateTimeField(blank=True, null=True, help_text='Data em que o admin reativou após rejeição')

    # --- Auditoria e Relacionamentos ---
    data_criacao = models.DateTimeField(auto_now_add=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='meus_neologismos'
    )

    #area de curtidas
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='neologismos_curtidos',
        blank=True
    )
            
    deslikes = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='neologismos_rejeitados',
        blank=True
    )

    @property
    def total_likes(self):
        return self.likes.count()
    
    @property
    def total_deslikes(self):
        return self.deslikes.count()
    
    def __str__(self):
        return self.titulo


class Contexto(models.Model):
    """Citação estruturada de uso de um neologismo (vários por verbete).

    O site original lista múltiplas citações com a fonte e link de origem.
    """
    neologismo = models.ForeignKey(
        Neologismo,
        on_delete=models.CASCADE,
        related_name='contextos'
    )
    citacao = models.TextField(help_text='Frase/trecho onde o neologismo aparece')
    fonte = models.CharField(
        max_length=200,
        blank=True,
        help_text='Quem disse ou onde foi publicado. Ex: "@usuario no X"'
    )
    link = models.URLField(max_length=500, blank=True, help_text='Link para a fonte original')
    data_criacao = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['data_criacao']

    def __str__(self):
        return f'Contexto de {self.neologismo.titulo}'

