from django.contrib.auth import authenticate, get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import (
    LoginSerializer,
    RegistroSerializer,
    SessaoSerializer,
    UsuarioSerializer,
)

Usuario = get_user_model()


def dados_sessao(user, token):
    return {
        'token': token.key,
        'user_id': user.id,
        'username': user.username,
        'email': user.email or '',
        'is_admin': user.is_admin,
    }


class RegistroView(generics.CreateAPIView):
    """Cria um Usuario e já devolve o token de autenticação."""

    serializer_class = RegistroSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'cadastro'

    @extend_schema(responses={201: SessaoSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            dados_sessao(user, token),
            status=status.HTTP_201_CREATED,
        )


class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    # Escopo próprio: evita que a rota de login seja usada para força bruta
    # dentro do limite genérico de 120/min.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    @extend_schema(responses={200: SessaoSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['username'].strip(),
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response(
                {'detail': 'Usuário ou senha inválidos.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {'detail': 'Esta conta está desativada.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response(dados_sessao(user, token))


class MeView(generics.RetrieveAPIView):
    serializer_class = UsuarioSerializer
    # Sem isto, a permissão padrão (IsAuthenticatedOrReadOnly) deixava um GET
    # anônimo passar e o serializer estourava 500 no AnonymousUser.
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class LogoutView(APIView):
    """Invalida o token atual no servidor.

    Apagar o token do localStorage não o revoga: até aqui, um token vazado
    seguia válido para sempre.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
