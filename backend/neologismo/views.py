from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import Neologismo
from .serializers import NeologismoSerializer


class NeologismoViewSet(viewsets.ModelViewSet):
    queryset = Neologismo.objects.all().order_by('-data_criacao')
    serializer_class = NeologismoSerializer

    def get_queryset(self):
        qs = Neologismo.objects.all().order_by('-data_criacao')
        # Filtro opcional por status (?status=pendente). Usado pela Home
        # (status=aprovado) e pelo Painel Admin (status=pendente).
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        # Filtro opcional por tag (?tag=Anglicismo).
        tag_param = self.request.query_params.get('tag')
        if tag_param:
            qs = qs.filter(tags__contains=[tag_param])

        # Busca opcional por texto (?search=termo), usada pela Home.
        search_param = self.request.query_params.get('search')
        if search_param:
            qs = qs.filter(
                Q(titulo__icontains=search_param) | Q(definicao__icontains=search_param)
            )
        return qs

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)

    @action(detail=True, methods=['post'])
    def dar_like(self, request, pk=None):
        neologismo = self.get_object()
        user = request.user

        with transaction.atomic():
            # Se ele já deu DESLIKE, remove o deslike antes
            if neologismo.deslikes.filter(id=user.id).exists():
                neologismo.deslikes.remove(user)

            # dois cliques para remover
            if neologismo.likes.filter(id=user.id).exists():
                neologismo.likes.remove(user)
                msg = "Like removido"
            else:
                # Se não tinha like, adiciona agora
                neologismo.likes.add(user)
                msg = "Like adicionado"

        return Response({
            'status': msg,
            'likes': neologismo.total_likes,
            'deslikes': neologismo.total_deslikes
        })

    @action(detail=True, methods=['post'])
    def dar_deslike(self, request, pk=None):
        neologismo = self.get_object()
        user = request.user

        with transaction.atomic():
            # Se o usuário já deu LIKE, remove o like
            if neologismo.likes.filter(id=user.id).exists():
                neologismo.likes.remove(user)

            if neologismo.deslikes.filter(id=user.id).exists():
                # Se ele já tinha dado deslike, ele está "desmarcando"
                neologismo.deslikes.remove(user)
                status_msg = "Deslike removido"
            else:
                # Se não tinha marca
                neologismo.deslikes.add(user)
                status_msg = "Deslike adicionado"

        return Response({
            'status': status_msg,
            'likes': neologismo.total_likes,
            'deslikes': neologismo.total_deslikes
        })

    # --- Ações de moderação (somente staff/admin) ---

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def aprovar(self, request, pk=None):
        neologismo = self.get_object()
        neologismo.status = 'aprovado'
        neologismo.motivo_rejeicao = None
        neologismo.save()
        return Response({'id': neologismo.id, 'status': neologismo.status})

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def rejeitar(self, request, pk=None):
        neologismo = self.get_object()
        neologismo.status = 'rejeitado'
        neologismo.motivo_rejeicao = request.data.get('motivo_rejeicao', '')
        neologismo.save()
        return Response({
            'id': neologismo.id,
            'status': neologismo.status,
            'motivo_rejeicao': neologismo.motivo_rejeicao,
        })

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def reativar(self, request, pk=None):
        neologismo = self.get_object()
        neologismo.status = 'aprovado'
        neologismo.reativado_em = timezone.now()
        neologismo.motivo_rejeicao = None
        neologismo.save()
        return Response({
            'id': neologismo.id,
            'status': neologismo.status,
            'reativado_em': neologismo.reativado_em,
        })
