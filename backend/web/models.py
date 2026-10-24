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

    INTEGRANTE = 'integrante'
    EX_INTEGRANTE = 'ex-integrante'
    GRUPOS = [
        (INTEGRANTE, 'Integrantes'),
        (EX_INTEGRANTE, 'Ex-integrantes'),
    ]

    nome = models.CharField(max_length=120)
    funcao = models.CharField('função', max_length=120, help_text='Ex.: Graduanda em Letras')
    bio = models.TextField(blank=True, max_length=300)
    foto = models.ImageField(upload_to=caminho_foto, blank=True)
    grupo = models.CharField(max_length=20, choices=GRUPOS, default=INTEGRANTE, db_index=True)
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


# --- Indicações de leitura -----------------------------------------------------

CORES_AREA = [
    ('ameixa', 'Ameixa'),
    ('malva', 'Malva'),
    ('lilas', 'Lilás'),
    ('ceu', 'Azul'),
    ('tinta', 'Preto'),
]


class AreaTematica(models.Model):
    """Agrupa as indicações de leitura (filtro "Área temática")."""

    nome = models.CharField(max_length=80, unique=True)
    cor = models.CharField(max_length=10, choices=CORES_AREA, default='ameixa')

    class Meta:
        ordering = ['nome']
        verbose_name = 'área temática'
        verbose_name_plural = 'áreas temáticas'

    def __str__(self):
        return self.nome


class Referencia(models.Model):
    """Obra do acervo de indicações de leitura."""

    LIVRO = 'livro'
    CAPITULO = 'capitulo'
    PERIODICO = 'periodico'
    ANAIS = 'anais'
    TESE = 'tese'
    DICIONARIO = 'dicionario'
    OUTROS = 'outros'
    CATEGORIAS = [
        (LIVRO, 'Livro'),
        (CAPITULO, 'Capítulo de livro'),
        (PERIODICO, 'Artigo em periódico'),
        (ANAIS, 'Artigo em anais'),
        (TESE, 'Tese, dissertação ou monografia'),
        (DICIONARIO, 'Dicionário ou vocabulário'),
        (OUTROS, 'Outros'),
    ]
    # Nestas categorias o destaque da ABNT vai na obra maior (o "In:").
    CATEGORIAS_DE_PARTE = {CAPITULO, PERIODICO, ANAIS}

    IDIOMAS = [
        ('pt', 'Português'),
        ('en', 'Inglês'),
        ('es', 'Espanhol'),
        ('fr', 'Francês'),
        ('outro', 'Outro'),
    ]

    area = models.ForeignKey(
        AreaTematica, on_delete=models.PROTECT, related_name='referencias',
        verbose_name='área temática',
    )
    categoria = models.CharField(max_length=12, choices=CATEGORIAS, default=LIVRO, db_index=True)
    autoria = models.CharField(
        max_length=300,
        help_text='Como na ABNT: SOBRENOME, Nome. Várias pessoas separadas por ponto e vírgula.',
    )
    titulo = models.CharField('título', max_length=400)
    ano = models.PositiveSmallIntegerField(db_index=True)
    publicado_em = models.CharField(
        'publicado em', max_length=300, blank=True,
        help_text='Periódico, livro ou evento onde o texto saiu (aparece como “In:”).',
    )
    detalhes = models.CharField(
        max_length=300, blank=True,
        help_text='Edição, local, editora, volume, páginas. Ex.: 3. ed. São Paulo: Ática',
    )
    idioma = models.CharField(max_length=5, choices=IDIOMAS, default='pt')
    url = models.URLField('link', max_length=500, blank=True)
    criada_em = models.DateTimeField('adicionada em', auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-criada_em', '-id']
        verbose_name = 'referência'
        verbose_name_plural = 'referências'

    def __str__(self):
        return f'{self.autoria} ({self.ano}). {self.titulo}'

    @property
    def destaca_publicacao(self):
        return self.categoria in self.CATEGORIAS_DE_PARTE and bool(self.publicado_em)
