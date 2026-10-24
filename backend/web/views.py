"""Páginas do site.

As regras de negócio (o que é público, como se busca, como se modera, o que
um verbete precisa ter para ser aceito) não moram aqui: vêm de
`neologismo.consultas`, `neologismo.moderacao` e dos serializers da API. Estas
views só traduzem formulário e querystring para essas peças, para o site e a
API nunca divergirem.
"""


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST

from neologismo import consultas
from neologismo import facetas as indice_facetas
from neologismo.models import Neologismo
from neologismo.serializers import NeologismoSerializer

from . import conteudo
from .forms import PerfilForm
from .limites import excedeu
from .models import MembroEquipe

POR_PAGINA = 20
# Na página inicial os cards ficam em 3 colunas: 12 dá 4 linhas cheias.
POR_PAGINA_INICIO = 12

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
            return JsonResponse(
                {'detail': 'Muitas curtidas seguidas. Aguarde um minuto.'}, status=429
            )
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
            return redirect(f"{reverse('account_login')}?next={reverse('web:enviar')}")
        return render(request, 'web/enviar.html', {'precisa_entrar': True})

    if request.GET.get('enviado'):
        return render(request, 'web/enviar.html', {'enviado': True})

    valores = dict.fromkeys(
        ('titulo', 'classe_gramatical', 'definicao', 'contexto_uso', 'tags'), ''
    )
    citacoes = []
    erros = {}

    if request.method == 'POST':
        valores = {campo: request.POST.get(campo, '') for campo in valores}
        citacoes = [
            {'citacao': citacao, 'fonte': fonte, 'link': link}
            # strict=False: um POST montado à mão com listas desiguais não
            # derruba o envio, só perde as citações incompletas.
            for citacao, fonte, link in zip(
                request.POST.getlist('citacao'),
                request.POST.getlist('fonte'),
                request.POST.getlist('link'),
                strict=False,
            )
        ]

        erros = _validar_envio(valores)
        if not erros and excedeu(request, 'envio'):
            erros['geral'] = (
                'Você enviou muitos verbetes na última hora. Tente novamente mais tarde.'
            )
        if not erros:
            dados = {
                **{
                    campo: valores[campo]
                    for campo in ('titulo', 'classe_gramatical', 'definicao', 'contexto_uso')
                },
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


# --- Conta ----------------------------------------------------------------------

def redirecionar(nome):
    """View que leva ao endereço novo preservando a querystring (?next=...)."""
    def view(request, *args, **kwargs):
        destino = reverse(nome)
        if request.GET:
            destino = f'{destino}?{request.GET.urlencode()}'
        return redirect(_destino_seguro(request, destino))
    return view


@login_required
def perfil(request):
    usuario = request.user
    form = PerfilForm(request.POST or None, instance=usuario)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Perfil atualizado.')
        return redirect('web:perfil')

    meus = Neologismo.objects.filter(autor=usuario)
    curtidos = (
        consultas.anotados(usuario)
        .filter(status=Neologismo.APROVADO, likes=usuario)
        .order_by('titulo')
    )
    return render(request, 'web/perfil.html', {
        'form': form,
        'enviados': meus.count(),
        'publicados': meus.filter(status=Neologismo.APROVADO).count(),
        'curtidas_recebidas': Neologismo.likes.through.objects.filter(
            neologismo__autor=usuario, neologismo__status=Neologismo.APROVADO,
        ).count(),
        'curtidos': curtidos[:30],
        'total_curtidos': curtidos.count(),
    })


# --- Institucional --------------------------------------------------------------

@require_GET
def sobre(request):
    return render(request, 'web/sobre.html', {
        'passos': conteudo.PASSOS,
        'objetivos': conteudo.OBJETIVOS,
    })


@require_GET
def equipe(request):
    return render(request, 'web/equipe.html', {
        'equipe': MembroEquipe.objects.filter(ativo=True),
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
            'paginas': [
                reverse(nome)
                for nome in ('web:inicio', 'web:sobre', 'web:equipe', 'web:referencias')
            ],
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
