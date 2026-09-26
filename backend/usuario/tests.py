from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

Usuario = get_user_model()

SEM_THROTTLE = override_settings(
    REST_FRAMEWORK={
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'rest_framework.authentication.TokenAuthentication',
            'rest_framework.authentication.SessionAuthentication',
        ],
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.IsAuthenticatedOrReadOnly',
        ],
        'DEFAULT_PAGINATION_CLASS': 'config.pagination.PaginacaoPadrao',
        'PAGE_SIZE': 24,
        'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    }
)


@SEM_THROTTLE
class CadastroTests(APITestCase):
    url = '/api/cadastro/'

    def test_cadastro_devolve_token(self):
        resposta = self.client.post(self.url, {
            'username': 'novato',
            'email': 'novato@exemplo.com',
            'password': 'SenhaBemForte123',
        }, format='json')

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', resposta.data)
        self.assertFalse(resposta.data['is_admin'])
        self.assertTrue(Token.objects.filter(key=resposta.data['token']).exists())

    def test_senha_fraca_e_rejeitada(self):
        """Regressão: antes bastava ter 6 caracteres, então "123456" passava."""
        resposta = self.client.post(self.url, {
            'username': 'novato',
            'password': '123456',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', resposta.data)

    def test_username_duplicado_ignorando_caixa(self):
        Usuario.objects.create_user('Joao', password='SenhaBemForte123')
        resposta = self.client.post(self.url, {
            'username': 'joao',
            'password': 'SenhaBemForte123',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', resposta.data)

    def test_email_duplicado(self):
        Usuario.objects.create_user(
            'alguem', email='a@exemplo.com', password='SenhaBemForte123'
        )
        resposta = self.client.post(self.url, {
            'username': 'outro',
            'email': 'A@Exemplo.com',
            'password': 'SenhaBemForte123',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', resposta.data)

    def test_cliente_nao_se_torna_admin(self):
        resposta = self.client.post(self.url, {
            'username': 'espertinho',
            'password': 'SenhaBemForte123',
            'is_admin': True,
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        usuario = Usuario.objects.get(username='espertinho')
        self.assertFalse(usuario.is_admin)
        self.assertFalse(usuario.is_staff)


@SEM_THROTTLE
class LoginTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            'leitor', email='l@exemplo.com', password='SenhaBemForte123'
        )

    def test_login_valido(self):
        resposta = self.client.post('/api/login/', {
            'username': 'leitor',
            'password': 'SenhaBemForte123',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn('token', resposta.data)

    def test_senha_errada(self):
        resposta = self.client.post('/api/login/', {
            'username': 'leitor',
            'password': 'errada',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_campos_faltando(self):
        resposta = self.client.post('/api/login/', {}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_conta_inativa(self):
        self.usuario.is_active = False
        self.usuario.save()
        resposta = self.client.post('/api/login/', {
            'username': 'leitor',
            'password': 'SenhaBemForte123',
        }, format='json')
        self.assertIn(
            resposta.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )


@SEM_THROTTLE
class SessaoTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = Usuario.objects.create_user(
            'leitor', password='SenhaBemForte123'
        )

    def test_me_anonimo_devolve_401_e_nao_500(self):
        """Regressão: sem permissão explícita o serializer estourava no
        AnonymousUser e devolvia 500."""
        resposta = self.client.get('/api/me/')
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_autenticado(self):
        self.client.force_authenticate(self.usuario)
        resposta = self.client.get('/api/me/')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data['username'], 'leitor')
        self.assertEqual(resposta.data['total_enviados'], 0)

    def test_logout_revoga_o_token(self):
        token = Token.objects.create(user=self.usuario)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        resposta = self.client.post('/api/logout/')
        self.assertEqual(resposta.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

        resposta = self.client.get('/api/me/')
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)


class UsuarioModelTests(APITestCase):
    def test_is_admin_promove_a_staff(self):
        usuario = Usuario.objects.create_user(
            'chefe', password='SenhaBemForte123', is_admin=True
        )
        self.assertTrue(usuario.is_staff)
