from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from config.emails import avisar_verbete_aprovado, avisar_verbete_rejeitado

from .models import Neologismo
from .permissions import DonoOuStaff
from .serializers import (
    CurtidaRespostaSerializer,
    NeologismoModeracaoSerializer,
    NeologismoSerializer,
    RejeicaoSerializer,
)

ORDENACOES = {
    'recentes': ['-data_criacao'],
    'antigos': ['data_criacao'],
    'populares': ['-likes_count', '-data_criacao'],
    'alfabetica': ['titulo'],
}


class NeologismoViewSet(viewsets.ModelViewSet):
    queryset = Neologismo.objects.all()
    serializer_class = NeologismoSerializer
    permission_classes = [DonoOuStaff]

    def get_serializer_class(self):
        # O painel admin precisa dos campos internos; o público, não.
        if self.request.user.is_staff and self.action in (
            'list', 'retrieve', 'aprovar', 'rejeitar', 'reativar'
        ):
            return NeologismoModeracaoSerializer
        return self.serializer_class

    def get_throttles(self):
        if self.action == 'create':
            self.throttle_scope = 'envio'
        elif self.action == 'curtir':
            self.throttle_scope = 'curtida'
        return super().get_throttles()

    # --- Queryset ---

    def _base_queryset(self):
        """Queryset com as anotações que o serializer consome.

        As contagens vêm anotadas em vez de `obj.likes.count()` para não
        disparar uma query por card renderizado na Home.
        """
        usuario = self.request.user

        qs = (
            Neologismo.objects
            .select_related('autor', 'moderado_por')
            .prefetch_related('contextos')
            .annotate(
                likes_count=Count('likes', distinct=True),
                deslikes_count=Count('deslikes', distinct=True),
            )
            # Ordem explícita: sem ela a paginação pode repetir ou pular itens
            # entre páginas, e o DRF emite UnorderedObjectListWarning.
            .order_by('-data_criacao', '-id')
        )

        if usuario.is_authenticated:
            qs = qs.annotate(
                curtido_por_mim=Exists(
                    get_user_model().objects.filter(
                        pk=usuario.pk,
                        neologismos_curtidos=OuterRef('pk'),
                    )
                )
            )

        return qs

    def get_queryset(self):
        qs = self._base_queryset()
        usuario = self.request.user
        params = self.request.query_params

        status_param = params.get('status')

        if usuario.is_staff:
            # A moderação enxerga tudo e escolhe o que quer ver.
            if status_param:
                qs = qs.filter(status=status_param)
        elif self.action in ('retrieve', 'update', 'partial_update', 'destroy'):
            # No acesso a um verbete específico o autor alcança o próprio
            # rascunho (para acompanhar e corrigir); os demais, só o aprovado.
            visivel = Q(status=Neologismo.APROVADO)
            if usuario.is_authenticated:
                visivel |= Q(autor=usuario)
            qs = qs.filter(visivel)
        else:
            # Listagem pública: apenas aprovados. Antes bastava pedir
            # ?status=pendente para ler a fila de moderação inteira.
            qs = qs.filter(status=Neologismo.APROVADO)

        busca = (params.get('search') or '').strip()
        if busca:
            qs = qs.filter(
                Q(titulo__icontains=busca)
                | Q(definicao__icontains=busca)
                | Q(contexto_uso__icontains=busca)
                | Q(tags__icontains=busca)
            )

        tag = (params.get('tag') or '').strip()
        if tag and tag.lower() != 'all':
            qs = qs.filter(tags__contains=[tag])

        classe = (params.get('classe') or '').strip()
        if classe:
            qs = qs.filter(classe_gramatical__icontains=classe)

        ordering = ORDENACOES.get(params.get('ordering', ''), None)
        if ordering:
            qs = qs.order_by(*ordering)

        return qs

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)

    # --- Metadados para os filtros da interface ---

    @extend_schema(
        responses={200: dict},
        description='Tags e classes gramaticais em uso, com contagem, para '
                    'montar os filtros sem hard-code no frontend.',
    )
    @action(detail=False, methods=['get'], permission_classes=[])
    def facetas(self, request):
        aprovados = Neologismo.objects.filter(status=Neologismo.APROVADO)

        contagem_tags = {}
        for tags in aprovados.values_list('tags', flat=True):
            for tag in tags or []:
                contagem_tags[tag] = contagem_tags.get(tag, 0) + 1

        classes = (
            aprovados
            .values('classe_gramatical')
            .annotate(total=Count('id'))
            .order_by('-total')
        )

        return Response({
            'total': aprovados.count(),
            'tags': [
                {'nome': nome, 'total': total}
                for nome, total in sorted(
                    contagem_tags.items(), key=lambda item: (-item[1], item[0])
                )
            ],
            'classes': [
                {'nome': c['classe_gramatical'], 'total': c['total']}
                for c in classes
                if c['classe_gramatical']
            ],
        })

    @extend_schema(
        parameters=[
            OpenApiParameter('search', str, description='Busca por título, definição, exemplo ou tag.'),
            OpenApiParameter('tag', str, description='Filtra por uma tag exata.'),
            OpenApiParameter('classe', str, description='Filtra por classe gramatical.'),
            OpenApiParameter(
                'ordering', str,
                description='recentes | antigos | populares | alfabetica',
            ),
        ]
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def meus(self, request):
        """Verbetes enviados pelo usuário logado, em qualquer status.

        Sem isto quem envia um verbete nunca descobre se ele foi aprovado.
        """
        qs = self._base_queryset().filter(autor=request.user)

        status_param = (request.query_params.get('status') or '').strip()
        if status_param in dict(Neologismo.STATUS_CHOICES):
            qs = qs.filter(status=status_param)

        pagina = self.paginate_queryset(qs)
        serializer = NeologismoSerializer(
            pagina, many=True, context=self.get_serializer_context()
        )
        return self.get_paginated_response(serializer.data)

    # --- Curtidas ---

    @extend_schema(
        request=None,
        responses={200: CurtidaRespostaSerializer},
        description='Alterna a curtida do usuário logado neste verbete.',
    )
    @action(
        detail=True,
        methods=['post'],
        url_path='curtir',
        permission_classes=[IsAuthenticated],
    )
    def curtir(self, request, pk=None):
        neologismo = self.get_object()
        usuario = request.user

        with transaction.atomic():
            # Bloqueia a linha para dois cliques rápidos não se atropelarem.
            neologismo = (
                Neologismo.objects.select_for_update().get(pk=neologismo.pk)
            )

            if neologismo.likes.filter(pk=usuario.pk).exists():
                neologismo.likes.remove(usuario)
                curtido = False
            else:
                neologismo.likes.add(usuario)
                curtido = True

        return Response({
            'id': neologismo.pk,
            'curtido_por_mim': curtido,
            'total_likes': neologismo.likes.count(),
        })

    # Nome antigo do endpoint, mantido para não quebrar clientes já publicados.
    @extend_schema(exclude=True)
    @action(
        detail=True,
        methods=['post'],
        url_path='dar_like',
        permission_classes=[IsAuthenticated],
    )
    def dar_like(self, request, pk=None):
        return self.curtir(request, pk=pk)

    # --- Moderação (somente staff) ---

    def _registrar_moderacao(self, neologismo, request, avisar=None, **campos):
        for campo, valor in campos.items():
            setattr(neologismo, campo, valor)
        neologismo.moderado_em = timezone.now()
        neologismo.moderado_por = request.user
        neologismo.save()

        # O aviso ao autor é best-effort: `enviar_email` engole a exceção e
        # loga, então o SMTP fora do ar não impede a moderação de acontecer.
        if avisar is not None:
            avisar(neologismo)

        serializer = self.get_serializer(neologismo)
        return Response(serializer.data)

    @extend_schema(request=None, responses={200: NeologismoModeracaoSerializer})
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def aprovar(self, request, pk=None):
        neologismo = self.get_object()
        return self._registrar_moderacao(
            neologismo, request,
            avisar=avisar_verbete_aprovado,
            status=Neologismo.APROVADO,
            motivo_rejeicao=None,
        )

    @extend_schema(
        request=RejeicaoSerializer,
        responses={200: NeologismoModeracaoSerializer},
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def rejeitar(self, request, pk=None):
        entrada = RejeicaoSerializer(data=request.data)
        if not entrada.is_valid():
            raise ValidationError(entrada.errors)

        neologismo = self.get_object()
        return self._registrar_moderacao(
            neologismo, request,
            avisar=avisar_verbete_rejeitado,
            status=Neologismo.REJEITADO,
            motivo_rejeicao=entrada.validated_data['motivo_rejeicao'].strip(),
        )

    @extend_schema(request=None, responses={200: NeologismoModeracaoSerializer})
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reativar(self, request, pk=None):
        """Volta um verbete rejeitado para aprovado."""
        neologismo = self.get_object()
        return self._registrar_moderacao(
            neologismo, request,
            avisar=avisar_verbete_aprovado,
            status=Neologismo.APROVADO,
            motivo_rejeicao=None,
            reativado_em=timezone.now(),
        )

    @extend_schema(
        request=None,
        responses={200: dict},
        description='Contadores por status, para os cabeçalhos do painel admin.',
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def resumo(self, request):
        contagens = {
            linha['status']: linha['total']
            for linha in Neologismo.objects.values('status').annotate(
                total=Count('id')
            )
        }
        return Response({
            'pendente': contagens.get(Neologismo.PENDENTE, 0),
            'aprovado': contagens.get(Neologismo.APROVADO, 0),
            'rejeitado': contagens.get(Neologismo.REJEITADO, 0),
            'total': sum(contagens.values()),
        }, status=http_status.HTTP_200_OK)
