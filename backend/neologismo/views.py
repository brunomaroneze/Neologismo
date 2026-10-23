from django.db import transaction
from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status as http_status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from . import consultas, moderacao
from . import facetas as indice_facetas
from .models import Neologismo
from .permissions import DonoOuStaff
from .serializers import (
    CurtidaRespostaSerializer,
    NeologismoModeracaoSerializer,
    NeologismoSerializer,
    RejeicaoSerializer,
)


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
        """Queryset com as anotações que o serializer consome."""
        return consultas.anotados(self.request.user)

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

        qs = consultas.filtrar(
            qs,
            busca=params.get('search'),
            tag=params.get('tag'),
            classe=params.get('classe'),
            letra=params.get('letra'),
            ordem=params.get('ordering'),
        )

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
        # Vem do cache: contar as tags exige varrer todos os aprovados em
        # Python (ver neologismo/facetas.py). O sinal de post_save derruba a
        # chave, então publicar ou moderar um verbete aparece no filtro na
        # requisição seguinte, sem esperar o TTL.
        return Response(indice_facetas.obter())

    @extend_schema(
        parameters=[
            OpenApiParameter(
                'search', str,
                description='Busca por título, definição, exemplo ou tag. '
                            'Ignora acento e caixa.',
            ),
            OpenApiParameter(
                'tag', str,
                description='Filtra por uma tag. Aceita a tag sem acento: '
                            '"internetes" casa com "Internetês".',
            ),
            OpenApiParameter(
                'classe', str,
                description='Filtra por classe gramatical. Ignora acento e caixa.',
            ),
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

    def _responder(self, neologismo):
        return Response(self.get_serializer(neologismo).data)

    @extend_schema(request=None, responses={200: NeologismoModeracaoSerializer})
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def aprovar(self, request, pk=None):
        neologismo = moderacao.aprovar(self.get_object(), request.user)
        return self._responder(neologismo)

    @extend_schema(
        request=RejeicaoSerializer,
        responses={200: NeologismoModeracaoSerializer},
    )
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def rejeitar(self, request, pk=None):
        entrada = RejeicaoSerializer(data=request.data)
        if not entrada.is_valid():
            raise ValidationError(entrada.errors)

        neologismo = moderacao.rejeitar(
            self.get_object(), request.user,
            entrada.validated_data['motivo_rejeicao'],
        )
        return self._responder(neologismo)

    @extend_schema(request=None, responses={200: NeologismoModeracaoSerializer})
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reativar(self, request, pk=None):
        """Volta um verbete rejeitado para aprovado."""
        neologismo = moderacao.reativar(self.get_object(), request.user)
        return self._responder(neologismo)

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
