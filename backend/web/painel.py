"""Painel do administrador: moderação de verbetes, usuários e equipe.

Dois níveis de acesso:
- moderação (is_staff): visão geral e fila de verbetes;
- administração (is_admin ou superusuário): também usuários e equipe.
"""

from datetime import timedelta
from functools import wraps

from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Exists, Max, OuterRef, Q
from django.db.models.functions import TruncMonth
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from neologismo import consultas, moderacao
from neologismo.models import Neologismo

from .forms import MembroEquipeForm, VerbeteForm
from .models import MembroEquipe
from .views import POR_PAGINA, _destino_seguro

Usuario = get_user_model()

MESES_GRAFICO = 6
MOTIVO_MIN, MOTIVO_MAX = 5, 1000


# --- Permissões -----------------------------------------------------------------

def e_administrador(usuario):
    return usuario.is_authenticated and (usuario.is_superuser or usuario.is_admin)


def _exigir(teste):
    def decorador(view):
        @wraps(view)
        def envolvida(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{reverse('account_login')}?next={request.get_full_path()}")
            if not teste(request.user):
                return render(request, 'web/sem_permissao.html', status=403)
            return view(request, *args, **kwargs)
        return envolvida
    return decorador


equipe_required = _exigir(lambda u: u.is_staff)
admin_required = _exigir(e_administrador)


def _contexto(request, aba, **extra):
    return {'aba': aba, 'pode_administrar': e_administrador(request.user), **extra}


# --- Visão geral ------------------------------------------------------------------

def _serie_mensal(qs, campo):
    """Contagem por mês dos últimos MESES_GRAFICO meses, com os meses vazios."""
    hoje = timezone.localdate()
    meses = []
    ano, mes = hoje.year, hoje.month
    for _ in range(MESES_GRAFICO):
        meses.append((ano, mes))
        ano, mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    meses.reverse()

    inicio = timezone.make_aware(timezone.datetime(meses[0][0], meses[0][1], 1))
    contagem = {
        (linha['mes'].year, linha['mes'].month): linha['total']
        for linha in qs.filter(**{f'{campo}__gte': inicio})
        .annotate(mes=TruncMonth(campo))
        .values('mes')
        .annotate(total=Count('id'))
    }
    serie = [
        {'data': timezone.datetime(a, m, 1).date(), 'total': contagem.get((a, m), 0)}
        for a, m in meses
    ]
    maior = max((p['total'] for p in serie), default=0)
    for ponto in serie:
        ponto['altura'] = round(ponto['total'] / maior * 100) if maior else 0
        # Rótulo só no maior valor e no mês atual: um número em cada barra
        # vira ruído (o resto está na dica e na tabela).
        ponto['rotular'] = ponto['total'] and (ponto['total'] == maior or ponto is serie[-1])
    return serie


@equipe_required
@require_GET
def inicio(request):
    contagens = dict(Neologismo.objects.values_list('status').annotate(total=Count('id')))
    pendente_mais_antigo = (
        Neologismo.objects.filter(status=Neologismo.PENDENTE)
        .order_by('data_criacao').values_list('data_criacao', flat=True).first()
    )
    trinta_dias = timezone.now() - timedelta(days=30)

    return render(request, 'web/painel/inicio.html', _contexto(
        request, 'inicio',
        pendentes=contagens.get(Neologismo.PENDENTE, 0),
        publicados=contagens.get(Neologismo.APROVADO, 0),
        rejeitados=contagens.get(Neologismo.REJEITADO, 0),
        dias_espera=(timezone.now() - pendente_mais_antigo).days if pendente_mais_antigo else None,
        usuarios=Usuario.objects.filter(is_active=True).count(),
        usuarios_novos=Usuario.objects.filter(date_joined__gte=trinta_dias).count(),
        serie_envios=_serie_mensal(Neologismo.objects.all(), 'data_criacao'),
        fila=Neologismo.objects.filter(status=Neologismo.PENDENTE)
            .select_related('autor').order_by('data_criacao')[:5],
        mais_curtidos=Neologismo.objects.filter(status=Neologismo.APROVADO)
            .annotate(total=Count('likes')).filter(total__gt=0).order_by('-total', 'titulo')[:5],
    ))


# --- Verbetes -----------------------------------------------------------------------

@equipe_required
@require_GET
def verbetes(request):
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

    return render(request, 'web/painel/verbetes.html', _contexto(
        request, 'verbetes',
        pagina=Paginator(qs, POR_PAGINA).get_page(request.GET.get('pagina')),
        status=status,
        busca=request.GET.get('q', ''),
        abas=[
            (Neologismo.PENDENTE, 'Pendentes', contagens.get(Neologismo.PENDENTE, 0)),
            (Neologismo.APROVADO, 'Publicados', contagens.get(Neologismo.APROVADO, 0)),
            (Neologismo.REJEITADO, 'Rejeitados', contagens.get(Neologismo.REJEITADO, 0)),
        ],
    ))


@equipe_required
@require_POST
def moderar(request, pk, acao):
    neologismo = get_object_or_404(Neologismo, pk=pk)
    voltar = _destino_seguro(request, request.POST.get('voltar'), 'web:painel_verbetes')

    if acao == 'aprovar':
        moderacao.aprovar(neologismo, request.user)
        messages.success(request, f'"{neologismo.titulo}" foi publicado.')
    elif acao == 'reativar':
        moderacao.reativar(neologismo, request.user)
        messages.success(request, f'"{neologismo.titulo}" voltou para o banco.')
    elif acao == 'rejeitar':
        motivo = request.POST.get('motivo', '').strip()
        if not MOTIVO_MIN <= len(motivo) <= MOTIVO_MAX:
            messages.info(request, 'Escreva um motivo com pelo menos 5 caracteres.')
        else:
            moderacao.rejeitar(neologismo, request.user, motivo)
            messages.success(request, f'"{neologismo.titulo}" foi rejeitado.')
    else:
        raise Http404

    return redirect(voltar)


@equipe_required
@require_POST
def lote(request):
    voltar = _destino_seguro(request, request.POST.get('voltar'), 'web:painel_verbetes')
    acao = request.POST.get('acao')
    ids = [i for i in request.POST.getlist('ids') if i.isdigit()]
    selecionados = list(Neologismo.objects.filter(pk__in=ids))

    if not selecionados:
        messages.info(request, 'Marque ao menos um verbete.')
        return redirect(voltar)

    if acao == 'aprovar':
        # Só faz sentido aprovar o que ainda não está publicado.
        alvos = [n for n in selecionados if n.status != Neologismo.APROVADO]
        for neologismo in alvos:
            moderacao.aprovar(neologismo, request.user)
        messages.success(request, f'{len(alvos)} verbete(s) publicado(s).')
    elif acao == 'rejeitar':
        motivo = request.POST.get('motivo', '').strip()
        if not MOTIVO_MIN <= len(motivo) <= MOTIVO_MAX:
            messages.info(request, 'Escreva um motivo com pelo menos 5 caracteres; ele vai para todos os autores.')
            return redirect(voltar)
        alvos = [n for n in selecionados if n.status != Neologismo.REJEITADO]
        for neologismo in alvos:
            moderacao.rejeitar(neologismo, request.user, motivo)
        messages.success(request, f'{len(alvos)} verbete(s) rejeitado(s).')
    else:
        raise Http404

    return redirect(voltar)


@equipe_required
def editar_verbete(request, pk):
    neologismo = get_object_or_404(Neologismo.objects.select_related('autor'), pk=pk)
    voltar = _destino_seguro(request, request.POST.get('voltar') or request.GET.get('voltar'), 'web:painel_verbetes')
    form = VerbeteForm(request.POST or None, instance=neologismo)

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()
            if 'aprovar' in request.POST and neologismo.status != Neologismo.APROVADO:
                moderacao.aprovar(neologismo, request.user)
                messages.success(request, f'"{neologismo.titulo}" foi corrigido e publicado.')
            else:
                messages.success(request, f'"{neologismo.titulo}" foi atualizado.')
        return redirect(voltar)

    return render(request, 'web/painel/editar_verbete.html', _contexto(
        request, 'verbetes', form=form, verbete=neologismo, voltar=voltar,
    ))


# --- Usuários ----------------------------------------------------------------------

PAPEIS = {
    'leitor': 'Leitor',
    'moderador': 'Moderador',
    'administrador': 'Administrador',
}


def papel_de(usuario):
    if usuario.is_superuser or usuario.is_admin:
        return 'administrador'
    if usuario.is_staff:
        return 'moderador'
    return 'leitor'


@admin_required
@require_GET
def usuarios(request):
    busca = request.GET.get('q', '').strip()
    papel = request.GET.get('papel', '')

    qs = (
        Usuario.objects
        .annotate(
            envios=Count('meus_neologismos', distinct=True),
            email_ok=Exists(EmailAddress.objects.filter(user=OuterRef('pk'), verified=True)),
        )
        .order_by('-date_joined')
    )
    if busca:
        qs = qs.filter(Q(username__icontains=busca) | Q(email__icontains=busca))
    if papel == 'administrador':
        qs = qs.filter(Q(is_superuser=True) | Q(is_admin=True))
    elif papel == 'moderador':
        qs = qs.filter(is_staff=True, is_superuser=False, is_admin=False)
    elif papel == 'leitor':
        qs = qs.filter(is_staff=False)
    elif papel == 'inativos':
        qs = qs.filter(is_active=False)

    pagina = Paginator(qs, POR_PAGINA).get_page(request.GET.get('pagina'))
    for usuario in pagina.object_list:
        usuario.papel = papel_de(usuario)

    return render(request, 'web/painel/usuarios.html', _contexto(
        request, 'usuarios',
        pagina=pagina, busca=busca, papel=papel, papeis=PAPEIS,
    ))


@admin_required
@require_POST
def usuario_acao(request, pk, acao):
    alvo = get_object_or_404(Usuario, pk=pk)
    voltar = _destino_seguro(request, request.POST.get('voltar'), 'web:painel_usuarios')

    # Ninguém mexe no próprio acesso (evita se trancar fora do painel) e só
    # um superusuário mexe em outro superusuário.
    if alvo == request.user:
        messages.info(request, 'Você não pode alterar o seu próprio acesso.')
        return redirect(voltar)
    if alvo.is_superuser and not request.user.is_superuser:
        messages.info(request, f'{alvo.username} é superusuário; só outro superusuário altera essa conta.')
        return redirect(voltar)

    if acao == 'papel':
        novo = request.POST.get('papel')
        if novo not in PAPEIS:
            raise Http404
        alvo.is_admin = novo == 'administrador'
        alvo.is_staff = novo in ('moderador', 'administrador')
        alvo.save(update_fields=['is_admin', 'is_staff'])
        messages.success(request, f'{alvo.username} agora é {PAPEIS[novo].lower()}.')
    elif acao == 'desativar':
        alvo.is_active = False
        alvo.save(update_fields=['is_active'])
        messages.success(request, f'A conta de {alvo.username} foi desativada.')
    elif acao == 'reativar':
        alvo.is_active = True
        alvo.save(update_fields=['is_active'])
        messages.success(request, f'A conta de {alvo.username} foi reativada.')
    elif acao == 'confirmar-email':
        if not alvo.email:
            messages.info(request, f'{alvo.username} não tem e-mail cadastrado.')
        else:
            endereco, _ = EmailAddress.objects.get_or_create(
                user=alvo, email__iexact=alvo.email,
                defaults={'email': alvo.email, 'primary': True},
            )
            endereco.verified = True
            endereco.save(update_fields=['verified'])
            messages.success(request, f'O e-mail de {alvo.username} foi marcado como confirmado.')
    else:
        raise Http404

    return redirect(voltar)


# --- Equipe ------------------------------------------------------------------------

@admin_required
@require_GET
def equipe(request):
    return render(request, 'web/painel/equipe.html', _contexto(
        request, 'equipe', membros=MembroEquipe.objects.all(),
    ))


@admin_required
def membro(request, pk=None):
    instancia = get_object_or_404(MembroEquipe, pk=pk) if pk else None
    form = MembroEquipeForm(request.POST or None, request.FILES or None, instance=instancia)

    if request.method == 'POST' and form.is_valid():
        novo = instancia is None
        membro_salvo = form.save(commit=False)
        if novo:
            # Novos membros entram no fim da lista.
            maior = MembroEquipe.objects.aggregate(m=Max('ordem'))['m'] or 0
            membro_salvo.ordem = maior + 10
        membro_salvo.save()
        messages.success(request, f'{membro_salvo.nome} foi {"adicionado(a) à" if novo else "atualizado(a) na"} equipe.')
        return redirect('web:painel_equipe')

    return render(request, 'web/painel/membro.html', _contexto(
        request, 'equipe', form=form, membro=instancia,
    ))


@admin_required
@require_POST
def membro_remover(request, pk):
    membro_alvo = get_object_or_404(MembroEquipe, pk=pk)
    nome = membro_alvo.nome
    if membro_alvo.foto:
        membro_alvo.foto.delete(save=False)
    membro_alvo.delete()
    messages.success(request, f'{nome} foi removido(a) da equipe.')
    return redirect('web:painel_equipe')


@admin_required
@require_POST
def membro_mover(request, pk, direcao):
    if direcao not in ('subir', 'descer'):
        raise Http404
    membros = list(MembroEquipe.objects.all())
    indice = next((i for i, m in enumerate(membros) if m.pk == pk), None)
    if indice is None:
        raise Http404
    vizinho = indice - 1 if direcao == 'subir' else indice + 1
    if 0 <= vizinho < len(membros):
        membros[indice], membros[vizinho] = membros[vizinho], membros[indice]
        # Renumera a lista inteira: evita empates de ordem herdados.
        with transaction.atomic():
            for posicao, item in enumerate(membros, start=1):
                MembroEquipe.objects.filter(pk=item.pk).update(ordem=posicao * 10)
    return redirect(f"{reverse('web:painel_equipe')}#membro-{pk}")
