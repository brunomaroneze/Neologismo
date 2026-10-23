from io import BytesIO
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import models
from django.utils.text import slugify
from PIL import Image, ImageOps

TAMANHO_FOTO = 400


def slug_do_nome(nome):
    """'Prof. Ana Maria Ribeiro' -> 'ana-maria-ribeiro'; tira a instituição."""
    return slugify(nome.split(' - ')[0].replace('Prof. ', '')) or 'membro'


def caminho_foto(membro, nome_arquivo):
    # Nome novo a cada envio: trocar a foto não pode esbarrar no cache do
    # navegador, que guardaria a imagem antiga no mesmo endereço. Só usa
    # campos (não métodos) para funcionar também nas migrações.
    return f'equipe/{slug_do_nome(membro.nome)}-{uuid4().hex[:8]}.jpg'


class MembroEquipe(models.Model):
    """Pessoa listada na página Equipe, gerida pelo painel do administrador."""

    nome = models.CharField(max_length=120)
    funcao = models.CharField('função', max_length=120, help_text='Ex.: Graduanda em Letras')
    bio = models.TextField(blank=True, max_length=300)
    foto = models.ImageField(upload_to=caminho_foto, blank=True)
    ordem = models.PositiveIntegerField(default=0, db_index=True)
    ativo = models.BooleanField('visível no site', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ordem', 'id']
        verbose_name = 'membro da equipe'
        verbose_name_plural = 'membros da equipe'

    def __str__(self):
        return self.nome

    @property
    def iniciais(self):
        partes = self.nome.split(' - ')[0].replace('Prof. ', '').split()
        if not partes:
            return '?'
        return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else '')).upper()

    def preparar_foto(self, arquivo):
        """Corta no centro, reduz para 400x400 e grava como JPEG.

        Fotos de celular chegam com vários megabytes e girando pela
        orientação EXIF; aqui elas viram um quadrado leve e já na posição
        certa, sem ninguém precisar editar a imagem antes de enviar.
        """
        with Image.open(arquivo) as imagem:
            imagem = ImageOps.exif_transpose(imagem).convert('RGB')
            imagem = ImageOps.fit(imagem, (TAMANHO_FOTO, TAMANHO_FOTO), Image.Resampling.LANCZOS)
            saida = BytesIO()
            imagem.save(saida, 'JPEG', quality=85, optimize=True, progressive=True)
        if self.foto:
            self.foto.delete(save=False)
        self.foto.save('foto.jpg', ContentFile(saida.getvalue()), save=False)
