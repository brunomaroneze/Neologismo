import re
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from config.emails import enviar_email

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


class SemThrottleMixin:
    """Zera o cache de throttle antes de cada teste.

    Duas armadilhas justificam este mixin:

    1. O histórico do throttle vive no cache, que o Django NÃO limpa entre
       métodos de teste. Sem isto, uma suíte que chama a mesma rota várias
       vezes passa isolada e falha em conjunto, com 429.
    2. `override_settings(REST_FRAMEWORK=...)` não desliga throttle nenhum:
       o DRF liga `SimpleRateThrottle.THROTTLE_RATES` ao dicionário de
       settings **no import**, então a troca do setting em teste não chega
       nas views. Limpar o cache é o que de fato funciona.

    Quem sobrescrever `setUp` numa subclasse precisa chamar `super().setUp()`.
    """

    def setUp(self):
        cache.clear()
        super().setUp()


@SEM_THROTTLE
class CadastroTests(SemThrottleMixin, APITestCase):
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
class LoginTests(SemThrottleMixin, APITestCase):
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
class SessaoTests(SemThrottleMixin, APITestCase):
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


class UsuarioModelTests(SemThrottleMixin, APITestCase):
    def test_is_admin_promove_a_staff(self):
        usuario = Usuario.objects.create_user(
            'chefe', password='SenhaBemForte123', is_admin=True
        )
        self.assertTrue(usuario.is_staff)


@SEM_THROTTLE
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SITE_URL='https://neoscopio.test',
)
class RecuperacaoDeSenhaTests(SemThrottleMixin, APITestCase):
    url_pedir = '/api/senha/recuperar/'
    url_redefinir = '/api/senha/redefinir/'

    def setUp(self):
        super().setUp()
        mail.outbox = []
        self.usuario = Usuario.objects.create_user(
            'leitor', email='leitor@exemplo.com', password='SenhaAntiga123'
        )

    def _pedir_link(self, email='leitor@exemplo.com'):
        """Faz o pedido e devolve (uid, token) extraídos do e-mail enviado."""
        resposta = self.client.post(self.url_pedir, {'email': email}, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        encontrado = re.search(
            r'/redefinir-senha/([^/\s"]+)/([^/\s"<]+)', mail.outbox[0].body
        )
        self.assertIsNotNone(encontrado, 'O e-mail não trouxe o link de redefinição.')
        return encontrado.group(1), encontrado.group(2)

    def test_pedido_envia_email_com_link(self):
        uid, token = self._pedir_link()
        self.assertTrue(uid and token)
        self.assertIn('leitor@exemplo.com', mail.outbox[0].to)
        self.assertIn('https://neoscopio.test', mail.outbox[0].body)

    def test_email_desconhecido_responde_200_e_nao_envia(self):
        """A rota não pode revelar quais e-mails têm conta."""
        resposta = self.client.post(
            self.url_pedir, {'email': 'ninguem@exemplo.com'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_conta_inativa_nao_recebe_link(self):
        self.usuario.is_active = False
        self.usuario.save()
        resposta = self.client.post(
            self.url_pedir, {'email': 'leitor@exemplo.com'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_redefinicao_troca_a_senha(self):
        uid, token = self._pedir_link()

        resposta = self.client.post(self.url_redefinir, {
            'uid': uid,
            'token': token,
            'password': 'SenhaNovaMuitoBoa123',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertIn('token', resposta.data)

        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('SenhaNovaMuitoBoa123'))
        self.assertFalse(self.usuario.check_password('SenhaAntiga123'))

    def test_token_nao_serve_duas_vezes(self):
        uid, token = self._pedir_link()
        corpo = {'uid': uid, 'token': token, 'password': 'SenhaNovaMuitoBoa123'}

        self.assertEqual(
            self.client.post(self.url_redefinir, corpo, format='json').status_code,
            status.HTTP_200_OK,
        )
        # A senha mudou, então o hash que alimenta o token mudou com ela.
        self.assertEqual(
            self.client.post(self.url_redefinir, corpo, format='json').status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_token_invalido_e_rejeitado(self):
        uid, _ = self._pedir_link()
        resposta = self.client.post(self.url_redefinir, {
            'uid': uid,
            'token': 'aaaaaa-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
            'password': 'SenhaNovaMuitoBoa123',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('SenhaAntiga123'))

    def test_uid_invalido_e_rejeitado(self):
        _, token = self._pedir_link()
        resposta = self.client.post(self.url_redefinir, {
            'uid': 'lixo!!',
            'token': token,
            'password': 'SenhaNovaMuitoBoa123',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_senha_fraca_e_rejeitada_na_redefinicao(self):
        uid, token = self._pedir_link()
        resposta = self.client.post(self.url_redefinir, {
            'uid': uid,
            'token': token,
            'password': '123456',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', resposta.data)

    def test_redefinir_revoga_os_tokens_antigos(self):
        """Quem já estava logado na conta é expulso ao redefinir a senha."""
        antigo = Token.objects.create(user=self.usuario)
        uid, token = self._pedir_link()

        self.client.post(self.url_redefinir, {
            'uid': uid,
            'token': token,
            'password': 'SenhaNovaMuitoBoa123',
        }, format='json')

        self.assertFalse(Token.objects.filter(key=antigo.key).exists())

    def test_email_e_case_insensitive(self):
        resposta = self.client.post(
            self.url_pedir, {'email': 'Leitor@Exemplo.COM'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EnvioDeEmailTests(SemThrottleMixin, APITestCase):
    def setUp(self):
        super().setUp()
        mail.outbox = []

    def test_destinatario_vazio_nao_envia(self):
        """Usuário sem e-mail cadastrado não deve gerar envio."""
        self.assertFalse(
            enviar_email('Assunto', 'emails/recuperar_senha.html', {}, [''])
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_email_tem_versao_texto_e_html(self):
        usuario = Usuario.objects.create_user(
            'alguem', email='a@exemplo.com', password='SenhaBemForte123'
        )
        self.assertTrue(
            enviar_email(
                'Assunto',
                'emails/recuperar_senha.html',
                {'usuario': usuario, 'url_redefinicao': 'https://x/y', 'validade_horas': 2},
                ['a@exemplo.com'],
            )
        )
        mensagem = mail.outbox[0]
        self.assertTrue(mensagem.body)
        self.assertEqual(mensagem.alternatives[0][1], 'text/html')

    def test_falha_no_envio_nao_propaga_excecao(self):
        """Regressão: o SMTP fora do ar não pode derrubar a ação do usuário."""
        usuario = Usuario.objects.create_user(
            'alguem', email='a@exemplo.com', password='SenhaBemForte123'
        )
        with patch(
            'config.emails.EmailMultiAlternatives.send',
            side_effect=SMTPException('servidor fora'),
        ):
            enviou = enviar_email(
                'Assunto',
                'emails/recuperar_senha.html',
                {'usuario': usuario, 'url_redefinicao': 'https://x/y', 'validade_horas': 2},
                ['a@exemplo.com'],
            )
        self.assertFalse(enviou)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SITE_URL='https://neoscopio.test',
)
class ThrottleDeSenhaTests(SemThrottleMixin, APITestCase):
    """Os limites de "pedir link" e "concluir troca" são independentes.

    Sem escopos separados, quem pedisse o e-mail 5 vezes ficava sem conseguir
    usar o token que recebeu — a redefinição respondia 429 por uma hora.
    Note que esta classe NÃO usa @SEM_THROTTLE: o throttle precisa estar ativo.
    """

    def setUp(self):
        super().setUp()
        mail.outbox = []
        self.usuario = Usuario.objects.create_user(
            'leitor', email='leitor@exemplo.com', password='SenhaAntiga123'
        )

    def test_estourar_o_pedido_nao_bloqueia_a_redefinicao(self):
        # Primeiro pedido: guarda o link que chegou.
        self.client.post(
            '/api/senha/recuperar/', {'email': 'leitor@exemplo.com'}, format='json'
        )
        achado = re.search(
            r'/redefinir-senha/([^/\s"]+)/([^/\s"<]+)', mail.outbox[0].body
        )
        uid, token = achado.group(1), achado.group(2)

        # Esgota o limite de pedidos de link (5/hora).
        for _ in range(6):
            self.client.post(
                '/api/senha/recuperar/',
                {'email': 'leitor@exemplo.com'},
                format='json',
            )

        ultimo = self.client.post(
            '/api/senha/recuperar/', {'email': 'leitor@exemplo.com'}, format='json'
        )
        self.assertEqual(
            ultimo.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
            'O pedido de link deveria estar limitado neste ponto.',
        )

        # Mesmo assim, concluir a troca com o token válido precisa funcionar.
        resposta = self.client.post('/api/senha/redefinir/', {
            'uid': uid,
            'token': token,
            'password': 'SenhaNovaMuitoBoa123',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password('SenhaNovaMuitoBoa123'))
