from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.emails import enviar_recuperacao_senha

from .serializers import (
    LoginSerializer,
    RecuperarSenhaSerializer,
    RedefinirSenhaSerializer,
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


class RecuperarSenhaView(generics.GenericAPIView):
    """Dispara o e-mail com o link de redefinição.

    Responde 200 mesmo quando o e-mail não existe na base. Confirmar quais
    e-mails têm conta transformaria esta rota em um verificador de cadastro
    para quem estiver varrendo uma lista de endereços.
    """

    serializer_class = RecuperarSenhaSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'recuperar_senha'

    @extend_schema(responses={200: OpenApiResponse(description='Pedido registrado.')})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        # Pode haver mais de uma conta com o mesmo e-mail em bases antigas,
        # antes da checagem de unicidade no cadastro.
        for usuario in Usuario.objects.filter(email__iexact=email, is_active=True):
            enviar_recuperacao_senha(
                usuario,
                uid=urlsafe_base64_encode(force_bytes(usuario.pk)),
                token=default_token_generator.make_token(usuario),
            )

        return Response({
            'detail': 'Se existe uma conta com esse e-mail, o link de '
                      'redefinição já está a caminho.'
        })


class RedefinirSenhaView(generics.GenericAPIView):
    """Conclui a redefinição usando o uid e o token do link."""

    serializer_class = RedefinirSenhaSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    # Escopo próprio, separado do pedido do link: quem pediu o e-mail algumas
    # vezes precisa conseguir concluir a troca de senha.
    throttle_scope = 'redefinir_senha'

    @extend_schema(responses={200: SessaoSerializer})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = serializer.validated_data['usuario']
        usuario.set_password(serializer.validated_data['password'])
        usuario.save()

        # Trocar a senha invalida os tokens antigos: se a conta foi acessada
        # por outra pessoa, redefinir a senha precisa expulsá-la de fato.
        Token.objects.filter(user=usuario).delete()
        token = Token.objects.create(user=usuario)

        return Response(dados_sessao(usuario, token))
