"""Páginas do site.

As regras de negócio (o que é público, como se busca, como se modera, o que
um verbete precisa ter para ser aceito) não moram aqui: vêm de
`neologismo.consultas`, `neologismo.moderacao` e dos serializers da API. Estas
views só traduzem formulário e querystring para essas peças, para o site e a
API nunca divergirem.
"""

from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth import login as entrar
from django.contrib.auth import logout as sair
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.staticfiles import finders
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.text import slugify
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_GET, require_POST
from rest_framework.authtoken.models import Token

from config.emails import enviar_recuperacao_senha
from neologismo import consultas, moderacao
from neologismo import facetas as indice_facetas
from neologismo.models import Neologismo
from neologismo.serializers import NeologismoSerializer
from usuario.serializers import (
    RecuperarSenhaSerializer,
    RedefinirSenhaSerializer,
    RegistroSerializer,
)

from . import conteudo
from .limites import excedeu

Usuario = get_user_model()

POR_PAGINA = 20
# Na página inicial os cards ficam em 3 colunas: 12 dá 4 linhas cheias.
POR_PAGINA_INICIO = 12
BACKEND_AUTH = 'django.contrib.auth.backends.ModelBackend'

ROTULOS_ORDEM = {
    'recentes': 'Mais recentes',
    'populares': 'Mais curtidos',
    'alfabetica': 'A–Z',
    'antigos': 'Mais antigos',
}

STATUS_ROTULO = {
    Neologismo.PENDENTE: 'Em moderação',
    Neologismo.APROVADO: 'Publicado',
    Neologismo.REJEITADO: 'Rejeitado',
}


# --- Utilidades ---------------------------------------------------------------

def _destino_seguro(request, candidato, padrao='web:inicio'):
    """Só redireciona para endereços do próprio site (evita open redirect)."""
    if candidato and url_has_allowed_host_and_scheme(
        candidato, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return candidato
    return reverse(padrao)


def _erros_planos(erros):
    """Achata os erros de um serializer em {campo: 'mensagem'}."""
    planos = {}
    for campo, mensagens in erros.items():
        if isinstance(mensagens, dict):
            mensagens = list(mensagens.values())
        if isinstance(mensagens, list) and mensagens:
            primeira = mensagens[0]
            if isinstance(primeira, dict):
                # Erro de um item aninhado (ex.: uma citação com link inválido).
                primeira = next(iter(primeira.values()), [''])
                primeira = primeira[0] if isinstance(primeira, list) else primeira
            planos[campo] = str(primeira)
        else:
            planos[campo] = str(mensagens)
    if 'non_field_errors' in planos:
        planos['geral'] = planos.pop('non_field_errors')
    return planos


def equipe_required(view):
    """Restringe à equipe de moderação, com login antes quando preciso."""
    @wraps(view)
    def envolvida(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('web:login')}?next={request.get_full_path()}")
        if not request.user.is_staff:
            return render(request, 'web/sem_permissao.html', status=403)
        return view(request, *args, **kwargs)
    return envolvida


def _visiveis(usuario):
    """Verbetes que o usuário pode abrir individualmente."""
    qs = consultas.anotados(usuario)
    if usuario.is_staff:
        return qs
    visivel = Q(status=Neologismo.APROVADO)
    if usuario.is_authenticated:
        # O autor acompanha o próprio verbete enquanto ele está em moderação.
        visivel |= Q(autor=usuario)
    return qs.filter(visivel)


# --- Consulta pública -----------------------------------------------------------

@require_GET
def inicio(request):
    params = request.GET
    ordem = params.get('ordem') if params.get('ordem') in ROTULOS_ORDEM else 'recentes'
    busca = (params.get('q') or '').strip()
    tag = (params.get('tag') or '').strip()

    qs = consultas.filtrar(
        consultas.anotados(request.user).filter(status=Neologismo.APROVADO),
        busca=busca,
        tag=tag,
        ordem=ordem,
    )
    pagina = Paginator(qs, POR_PAGINA_INICIO).get_page(params.get('pagina'))

    contexto = {
        'pagina': pagina,
        'tags': indice_facetas.obter()['tags'][:8],
        'busca': busca,
        'tag': tag,
        'ordem': ordem,
        'ordens': ROTULOS_ORDEM,
        'tem_filtro': bool(busca or tag or ordem != 'recentes'),
    }
    # "Carregar mais" busca a próxima página só com os cards.
    if params.get('parcial'):
        return render(request, 'web/_cards.html', contexto)
    return render(request, 'web/inicio.html', contexto)


@require_GET
def verbete(request, pk):
    neologismo = get_object_or_404(_visiveis(request.user), pk=pk)
    endereco = request.build_absolute_uri(reverse('web:verbete', args=[pk]))
    return render(request, 'web/verbete.html', {
        'verbete': neologismo,
        'endereco': endereco,
        'hoje': timezone.localdate(),
    })


@require_POST
@login_required
def curtir(request, pk):
    neologismo = get_object_or_404(_visiveis(request.user), pk=pk)
    quer_json = 'application/json' in request.headers.get('Accept', '')

    if excedeu(request, 'curtida'):
        if quer_json:
            return JsonResponse({'detail': 'Muitas curtidas seguidas. Aguarde um minuto.'}, status=429)
        messages.error(request, 'Muitas curtidas seguidas. Aguarde um minuto.')
        return redirect(_destino_seguro(request, request.POST.get('next')))

    with transaction.atomic():
        # Bloqueia a linha para dois cliques rápidos não se atropelarem.
        neologismo = Neologismo.objects.select_for_update().get(pk=neologismo.pk)
        if neologismo.likes.filter(pk=request.user.pk).exists():
            neologismo.likes.remove(request.user)
            curtido = False
        else:
            neologismo.likes.add(request.user)
            curtido = True

    if quer_json:
        return JsonResponse({'curtido': curtido, 'total': neologismo.likes.count()})
    return redirect(_destino_seguro(request, request.POST.get('next')))


# --- Contribuição ---------------------------------------------------------------

def _validar_envio(valores):
    """Mesmas mensagens que o formulário mostrava antes de chegar à API."""
    erros = {}
    if len(valores['titulo'].strip()) < 2:
        erros['titulo'] = 'Informe a palavra (mínimo 2 caracteres).'
    if not valores['classe_gramatical'].strip():
        erros['classe_gramatical'] = 'Escolha a classe gramatical.'
    if len(valores['definicao'].strip()) < 10:
        erros['definicao'] = 'Descreva o significado com pelo menos 10 caracteres.'
    return erros


def enviar(request):
    if not request.user.is_authenticated:
        if request.method == 'POST':
            return redirect(f"{reverse('web:login')}?next={reverse('web:enviar')}")
        return render(request, 'web/enviar.html', {'precisa_entrar': True})

    if request.GET.get('enviado'):
        return render(request, 'web/enviar.html', {'enviado': True})

    valores = {'titulo': '', 'classe_gramatical': '', 'definicao': '', 'contexto_uso': '', 'tags': ''}
    citacoes = []
    erros = {}

    if request.method == 'POST':
        valores = {campo: request.POST.get(campo, '') for campo in valores}
        citacoes = [
            {'citacao': c, 'fonte': f, 'link': l}
            for c, f, l in zip(
                request.POST.getlist('citacao'),
                request.POST.getlist('fonte'),
                request.POST.getlist('link'),
            )
        ]

        erros = _validar_envio(valores)
        if not erros and excedeu(request, 'envio'):
            erros['geral'] = 'Você enviou muitos verbetes na última hora. Tente novamente mais tarde.'
        if not erros:
            dados = {
                **{campo: valores[campo] for campo in ('titulo', 'classe_gramatical', 'definicao', 'contexto_uso')},
                'tags': [t for t in valores['tags'].split(',') if t.strip()],
                # Citações sem texto são descartadas pelo serializer.
                'contextos': [
                    {chave: valor.strip() for chave, valor in c.items()}
                    for c in citacoes
                ],
            }
            serializer = NeologismoSerializer(data=dados, context={'request': request})
            if serializer.is_valid():
                serializer.save(autor=request.user)
                return redirect(f"{reverse('web:enviar')}?enviado=1")
            erros = _erros_planos(serializer.errors)
        if erros and 'geral' not in erros:
            erros['geral'] = 'Revise os campos destacados abaixo.'

    return render(request, 'web/enviar.html', {
        'valores': valores,
        'citacoes': citacoes,
        'erros': erros,
        'classes': conteudo.CLASSES_GRAMATICAIS,
        'sugestoes_tags': [t['nome'] for t in indice_facetas.obter()['tags'][:6]],
    })


@login_required
@require_GET
def meus_envios(request):
    status = request.GET.get('status', '')
    qs = consultas.anotados(request.user).filter(autor=request.user)
    if status in dict(Neologismo.STATUS_CHOICES):
        qs = qs.filter(status=status)
    else:
        status = ''

    return render(request, 'web/meus_envios.html', {
        'pagina': Paginator(qs, POR_PAGINA).get_page(request.GET.get('pagina')),
        'status': status,
        'status_rotulo': STATUS_ROTULO,
        'abas': [
            ('', 'Todos'),
            (Neologismo.PENDENTE, 'Em moderação'),
            (Neologismo.APROVADO, 'Publicados'),
            (Neologismo.REJEITADO, 'Rejeitados'),
        ],
    })


# --- Moderação ------------------------------------------------------------------

@equipe_required
@require_GET
def moderacao_painel(request):
    status = request.GET.get('status')
    if status not in dict(Neologismo.STATUS_CHOICES):
        status = Neologismo.PENDENTE

    contagens = dict(Neologismo.objects.values_list('status').annotate(total=Count('id')))
    qs = consultas.filtrar(
        consultas.anotados(request.user).filter(status=status),
        busca=request.GET.get('q'),
    )
    # A fila de pendentes é atendida por ordem de chegada.
    if status == Neologismo.PENDENTE:
        qs = qs.order_by('data_criacao', 'id')

    return render(request, 'web/moderacao.html', {
        'pagina': Paginator(qs, POR_PAGINA).get_page(request.GET.get('pagina')),
        'status': status,
        'busca': request.GET.get('q', ''),
        'resumo': [
            ('Pendentes', contagens.get(Neologismo.PENDENTE, 0), True),
            ('Publicados', contagens.get(Neologismo.APROVADO, 0), False),
            ('Rejeitados', contagens.get(Neologismo.REJEITADO, 0), False),
            ('Total', sum(contagens.values()), False),
        ],
        'abas': [
            (Neologismo.PENDENTE, 'Pendentes'),
            (Neologismo.APROVADO, 'Publicados'),
            (Neologismo.REJEITADO, 'Rejeitados'),
        ],
    })


@equipe_required
@require_POST
def moderar(request, pk, acao):
    neologismo = get_object_or_404(Neologismo, pk=pk)
    voltar = _destino_seguro(request, request.POST.get('voltar'), 'web:moderacao')

    if acao == 'aprovar':
        moderacao.aprovar(neologismo, request.user)
        messages.success(request, f'"{neologismo.titulo}" foi publicado.')
    elif acao == 'reativar':
        moderacao.reativar(neologismo, request.user)
        messages.success(request, f'"{neologismo.titulo}" voltou para o banco.')
    elif acao == 'rejeitar':
        motivo = request.POST.get('motivo', '').strip()
        if not 5 <= len(motivo) <= 1000:
            messages.info(request, 'Escreva um motivo com pelo menos 5 caracteres.')
        else:
            moderacao.rejeitar(neologismo, request.user, motivo)
            messages.success(request, f'"{neologismo.titulo}" foi rejeitado.')
    else:
        return HttpResponse(status=404)

    return redirect(voltar)


# --- Conta ----------------------------------------------------------------------

def login_view(request):
    destino = request.POST.get('next') or request.GET.get('next', '')
    erro = None
    usuario_digitado = ''

    if request.method == 'POST':
        usuario_digitado = request.POST.get('username', '').strip()
        if not usuario_digitado or not request.POST.get('password'):
            erro = 'Preencha usuário e senha.'
        elif excedeu(request, 'login'):
            erro = 'Muitas tentativas de entrada. Aguarde um minuto e tente novamente.'
        else:
            usuario = authenticate(
                request,
                username=usuario_digitado,
                password=request.POST.get('password', ''),
            )
            if usuario is None:
                erro = 'Usuário ou senha inválidos.'
            else:
                entrar(request, usuario)
                return redirect(_destino_seguro(request, destino))

    return render(request, 'web/conta/login.html', {
        'erro': erro,
        'next': destino,
        'usuario_digitado': usuario_digitado,
    })


@require_POST
def logout_view(request):
    sair(request)
    return redirect('web:inicio')


def cadastro(request):
    valores = {'username': '', 'email': ''}
    erros = {}

    if request.method == 'POST':
        valores = {campo: request.POST.get(campo, '').strip() for campo in valores}
        senha = request.POST.get('password', '')

        if excedeu(request, 'cadastro'):
            erros['geral'] = 'Muitos cadastros a partir desta conexão. Tente novamente mais tarde.'
        elif senha != request.POST.get('password_confirmacao', ''):
            erros['password_confirmacao'] = 'As senhas não coincidem.'
        else:
            serializer = RegistroSerializer(data={**valores, 'password': senha})
            if serializer.is_valid():
                usuario = serializer.save()
                entrar(request, usuario, backend=BACKEND_AUTH)
                return redirect(_destino_seguro(request, request.POST.get('next')))
            erros = _erros_planos(serializer.errors)

    return render(request, 'web/conta/cadastro.html', {
        'valores': valores,
        'erros': erros,
        'next': request.POST.get('next') or request.GET.get('next', ''),
    })


def recuperar_senha(request):
    enviado = False
    erro = None
    email = ''

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if excedeu(request, 'recuperar_senha'):
            erro = 'Muitos pedidos de recuperação. Tente novamente mais tarde.'
        else:
            serializer = RecuperarSenhaSerializer(data={'email': email})
            if serializer.is_valid():
                # Mesma resposta exista ou não a conta: a página não pode
                # servir para descobrir quais e-mails estão cadastrados.
                for usuario in Usuario.objects.filter(
                    email__iexact=serializer.validated_data['email'], is_active=True
                ):
                    enviar_recuperacao_senha(
                        usuario,
                        uid=urlsafe_base64_encode(force_bytes(usuario.pk)),
                        token=default_token_generator.make_token(usuario),
                    )
                enviado = True
            else:
                erro = 'Informe o e-mail da sua conta.'

    return render(request, 'web/conta/recuperar_senha.html', {
        'validade_horas': round(settings.PASSWORD_RESET_TIMEOUT / 3600),
        'enviado': enviado,
        'erro': erro,
        'email': email,
    })


def redefinir_senha(request, uid, token):
    try:
        usuario = Usuario.objects.get(pk=urlsafe_base64_decode(uid).decode())
        link_valido = default_token_generator.check_token(usuario, token)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        link_valido = False

    erros = {}
    if link_valido and request.method == 'POST':
        senha = request.POST.get('password', '')
        if excedeu(request, 'redefinir_senha'):
            erros['geral'] = 'Muitas tentativas. Tente novamente mais tarde.'
        elif senha != request.POST.get('password_confirmacao', ''):
            erros['password_confirmacao'] = 'As senhas não coincidem.'
        else:
            serializer = RedefinirSenhaSerializer(data={'uid': uid, 'token': token, 'password': senha})
            if serializer.is_valid():
                usuario = serializer.validated_data['usuario']
                usuario.set_password(senha)
                usuario.save()
                # Trocar a senha também revoga os tokens da API.
                Token.objects.filter(user=usuario).delete()
                entrar(request, usuario, backend=BACKEND_AUTH)
                messages.success(request, 'Senha atualizada. Você já está conectado.')
                return redirect('web:inicio')
            erros = _erros_planos(serializer.errors)

    return render(request, 'web/conta/redefinir_senha.html', {
        'link_valido': link_valido,
        'erros': erros,
    })


# --- Institucional --------------------------------------------------------------

@require_GET
def sobre(request):
    return render(request, 'web/sobre.html', {
        'passos': conteudo.PASSOS,
        'objetivos': conteudo.OBJETIVOS,
    })


def _membro(dados):
    """Acrescenta a foto (se o arquivo existir) e as iniciais de reserva.

    As fotos ficam em web/static/web/equipe/<nome-em-slug>.jpg|png|webp.
    Quem ainda não tem foto aparece com as iniciais.
    """
    nome = dados['nome'].split(' - ')[0].replace('Prof. ', '')
    slug = slugify(nome)
    foto = next(
        (
            f'web/equipe/{slug}.{extensao}'
            for extensao in ('jpg', 'jpeg', 'png', 'webp')
            if finders.find(f'web/equipe/{slug}.{extensao}')
        ),
        None,
    )
    partes = nome.split()
    iniciais = (partes[0][0] + (partes[-1][0] if len(partes) > 1 else '')).upper()
    return {**dados, 'foto': foto, 'iniciais': iniciais}


@require_GET
def equipe(request):
    return render(request, 'web/equipe.html', {
        'equipe': [_membro(m) for m in conteudo.EQUIPE],
    })


@require_GET
def referencias(request):
    return render(request, 'web/referencias.html', {'referencias': conteudo.REFERENCIAS})


# --- Para buscadores ------------------------------------------------------------

@require_GET
def sitemap(request):
    verbetes = (
        Neologismo.objects.filter(status=Neologismo.APROVADO)
        .order_by('pk')
        .values('pk', 'data_atualizacao')
    )
    return render(
        request,
        'web/sitemap.xml',
        {
            'base': request.build_absolute_uri('/').rstrip('/'),
            'paginas': [reverse(nome) for nome in ('web:inicio', 'web:sobre', 'web:equipe', 'web:referencias')],
            'verbetes': verbetes,
        },
        content_type='application/xml',
    )


@require_GET
def robots(request):
    return render(
        request,
        'web/robots.txt',
        {'sitemap': request.build_absolute_uri(reverse('web:sitemap'))},
        content_type='text/plain',
    )
