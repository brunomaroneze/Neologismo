from django import forms
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError as ErroDRF

from neologismo.models import Neologismo
from neologismo.serializers import MAX_TAGS, NeologismoSerializer

from .models import AreaTematica, MembroEquipe, Referencia

TIPOS_FOTO = ('image/jpeg', 'image/png', 'image/webp')
TAMANHO_MAXIMO_FOTO = 8 * 1024 * 1024


class VerbeteForm(forms.ModelForm):
    """Edição de um verbete pela moderação, com as mesmas regras do envio."""

    tags = forms.CharField(
        required=False,
        help_text=f'Separe por vírgulas, até {MAX_TAGS}.',
    )

    class Meta:
        model = Neologismo
        fields = [
            'titulo', 'classe_gramatical', 'tipologia',
            'definicao', 'contexto_uso', 'elaborado_por',
        ]
        labels = {
            'titulo': 'Palavra',
            'classe_gramatical': 'Classe gramatical',
            'tipologia': 'Processo de formação',
            'definicao': 'Definição',
            'contexto_uso': 'Frase de exemplo',
            'elaborado_por': 'Elaborado por',
        }
        widgets = {
            'definicao': forms.Textarea(attrs={'rows': 5}),
            'contexto_uso': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and 'tags' not in self.initial:
            self.initial['tags'] = ', '.join(self.instance.tags)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'entrada')

    # As validações vêm do serializer da API: o painel não pode aceitar o que
    # o formulário de envio recusaria.
    def clean_titulo(self):
        return self._validar('validate_titulo', self.cleaned_data['titulo'])

    def clean_definicao(self):
        return self._validar('validate_definicao', self.cleaned_data['definicao'])

    def clean_tags(self):
        brutas = [t for t in self.cleaned_data['tags'].split(',') if t.strip()]
        return self._validar('validate_tags', brutas)

    def _validar(self, metodo, valor):
        try:
            return getattr(NeologismoSerializer(), metodo)(valor)
        except ErroDRF as erro:
            raise forms.ValidationError(erro.detail) from erro

    def save(self, commit=True):
        verbete = super().save(commit=False)
        verbete.tags = self.cleaned_data['tags']
        if commit:
            verbete.save()
        return verbete


class MembroEquipeForm(forms.ModelForm):
    # Campo do formulário, não do modelo: a imagem enviada não é gravada como
    # veio, passa antes por MembroEquipe.preparar_foto.
    foto = forms.ImageField(
        label='Foto',
        required=False,
        help_text='JPG, PNG ou WebP de até 8 MB. A foto é cortada em quadrado no centro.',
        widget=forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
    )
    remover_foto = forms.BooleanField(label='Remover a foto atual', required=False)

    class Meta:
        model = MembroEquipe
        fields = ['nome', 'funcao', 'bio', 'grupo', 'ativo']
        labels = {
            'nome': 'Nome', 'funcao': 'Função', 'bio': 'Frase de apresentação', 'grupo': 'Grupo',
        }
        help_texts = {
            'nome': (
                'Para indicar outra instituição, use “Nome - SIGLA”, '
                'como em “Beatriz Latini - UFMG”.'
            ),
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'maxlength': 300}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            if nome not in ('ativo', 'remover_foto'):
                campo.widget.attrs.setdefault('class', 'entrada')

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto:
            if foto.size > TAMANHO_MAXIMO_FOTO:
                raise forms.ValidationError('A foto passa de 8 MB. Envie uma imagem menor.')
            # content_type aqui vem do Pillow (forms.ImageField abre o arquivo),
            # não do nome nem do que o navegador declarou.
            if foto.content_type not in TIPOS_FOTO:
                raise forms.ValidationError('Envie a foto em JPG, PNG ou WebP.')
        return foto

    def save(self, commit=True):
        membro = super().save(commit=False)
        enviada = self.cleaned_data.get('foto')
        if enviada:
            # O ImageField já conferiu que é uma imagem de verdade; aqui ela é
            # cortada, reduzida e regravada (o arquivo original não é guardado).
            membro.preparar_foto(enviada)
        elif self.cleaned_data.get('remover_foto') and membro.foto:
            membro.foto.delete(save=False)
            membro.foto = ''
        if commit:
            membro.save()
        return membro


class PerfilForm(forms.ModelForm):
    """Dados do próprio perfil. O e-mail muda pela tela de e-mails do allauth,
    que exige confirmação do endereço novo."""

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name']
        labels = {'first_name': 'Nome', 'last_name': 'Sobrenome'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'entrada')


class ReferenciaForm(forms.ModelForm):
    class Meta:
        model = Referencia
        fields = [
            'area', 'categoria', 'autoria', 'titulo', 'publicado_em', 'detalhes', 'ano', 'idioma',
            'url',
        ]
        labels = {'area': 'Área temática', 'titulo': 'Título', 'url': 'Link'}
        help_texts = {'url': 'DOI, página da editora ou repositório.'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['area'].empty_label = 'Escolha uma área'
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'entrada')

    def clean_ano(self):
        from django.utils import timezone

        ano = self.cleaned_data['ano']
        if not 1500 <= ano <= timezone.now().year + 1:
            raise forms.ValidationError('Informe um ano válido, com quatro dígitos.')
        return ano

    def clean_autoria(self):
        return self.cleaned_data['autoria'].strip().rstrip('.')

    def clean_titulo(self):
        return self.cleaned_data['titulo'].strip().rstrip('.')


class AreaTematicaForm(forms.ModelForm):
    class Meta:
        model = AreaTematica
        fields = ['nome', 'cor']
        labels = {'nome': 'Nova área temática', 'cor': 'Cor'}
        error_messages = {'nome': {'unique': 'Já existe uma área com esse nome.'}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'entrada')
