from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Neologismo

Usuario = get_user_model()

# Os testes batem nos endpoints muitas vezes; sem desligar o throttle o
# limite de 120/min derruba a suíte.
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


def criar_neologismo(autor, titulo='Teste', status_verbete=Neologismo.APROVADO, **extra):
    return Neologismo.objects.create(
        titulo=titulo,
        definicao='Uma definição suficientemente longa para passar.',
        contexto_uso='Exemplo de uso.',
        classe_gramatical='Substantivo',
        autor=autor,
        status=status_verbete,
        **extra,
    )


@SEM_THROTTLE
class VisibilidadeTests(SemThrottleMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Usuario.objects.create_user('autor', password='SenhaForte123')
        cls.outro = Usuario.objects.create_user('outro', password='SenhaForte123')
        cls.staff = Usuario.objects.create_user(
            'chefe', password='SenhaForte123', is_staff=True
        )
        cls.aprovado = criar_neologismo(cls.autor, 'Aprovado')
        cls.pendente = criar_neologismo(cls.autor, 'Pendente', Neologismo.PENDENTE)
        cls.rejeitado = criar_neologismo(cls.autor, 'Rejeitado', Neologismo.REJEITADO)

    def test_listagem_publica_traz_somente_aprovados(self):
        resposta = self.client.get('/api/neologismos/')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        titulos = [n['titulo'] for n in resposta.data['results']]
        self.assertEqual(titulos, ['Aprovado'])

    def test_anonimo_nao_ve_pendentes_pedindo_por_status(self):
        """Regressão: ?status=pendente expunha a fila de moderação.

        O parâmetro é ignorado para quem não é staff: a listagem continua
        devolvendo só os aprovados.
        """
        resposta = self.client.get('/api/neologismos/?status=pendente')
        titulos = [n['titulo'] for n in resposta.data['results']]
        self.assertEqual(titulos, ['Aprovado'])

    def test_usuario_comum_nao_ve_pendentes_de_outros(self):
        self.client.force_authenticate(self.outro)
        resposta = self.client.get('/api/neologismos/?status=pendente')
        titulos = [n['titulo'] for n in resposta.data['results']]
        self.assertNotIn('Pendente', titulos)
        self.assertNotIn('Rejeitado', titulos)

    def test_detalhe_do_proprio_rascunho_e_acessivel_ao_autor(self):
        self.client.force_authenticate(self.autor)
        resposta = self.client.get(f'/api/neologismos/{self.pendente.pk}/')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_detalhe_de_rascunho_alheio_e_404(self):
        self.client.force_authenticate(self.outro)
        resposta = self.client.get(f'/api/neologismos/{self.pendente.pk}/')
        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_ve_a_fila_de_moderacao(self):
        self.client.force_authenticate(self.staff)
        resposta = self.client.get('/api/neologismos/?status=pendente')
        titulos = [n['titulo'] for n in resposta.data['results']]
        self.assertEqual(titulos, ['Pendente'])

    def test_detalhe_de_pendente_e_404_para_anonimo(self):
        resposta = self.client.get(f'/api/neologismos/{self.pendente.pk}/')
        self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    def test_campos_da_planilha_importada_estao_na_api(self):
        """Os verbetes vindos do CSV trazem tipologia, elaborado_por e
        data_registro. Se o serializer deixar de expor esses campos, os 139
        verbetes importados perdem informação na interface sem nenhum erro."""
        resposta = self.client.get('/api/neologismos/')
        verbete = resposta.data['results'][0]
        for campo in ('tipologia', 'elaborado_por', 'data_registro'):
            self.assertIn(campo, verbete)

    def test_resposta_publica_nao_expoe_ids_de_quem_curtiu(self):
        resposta = self.client.get('/api/neologismos/')
        verbete = resposta.data['results'][0]
        self.assertNotIn('likes', verbete)
        self.assertNotIn('deslikes', verbete)
        self.assertIn('total_likes', verbete)
        self.assertIn('curtido_por_mim', verbete)


@SEM_THROTTLE
class PermissaoDeEscritaTests(SemThrottleMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Usuario.objects.create_user('autor', password='SenhaForte123')
        cls.invasor = Usuario.objects.create_user('invasor', password='SenhaForte123')
        cls.staff = Usuario.objects.create_user(
            'chefe', password='SenhaForte123', is_staff=True
        )

    def test_terceiro_nao_edita_verbete_de_outro(self):
        """Regressão: qualquer logado podia dar PUT/DELETE em verbete alheio."""
        verbete = criar_neologismo(self.autor, 'Meu')
        self.client.force_authenticate(self.invasor)

        resposta = self.client.patch(
            f'/api/neologismos/{verbete.pk}/', {'titulo': 'Roubado'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

        resposta = self.client.delete(f'/api/neologismos/{verbete.pk}/')
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

        verbete.refresh_from_db()
        self.assertEqual(verbete.titulo, 'Meu')

    def test_autor_edita_enquanto_pendente(self):
        verbete = criar_neologismo(self.autor, 'Rascunho', Neologismo.PENDENTE)
        self.client.force_authenticate(self.autor)
        resposta = self.client.patch(
            f'/api/neologismos/{verbete.pk}/', {'titulo': 'Revisado'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_autor_nao_edita_depois_de_aprovado(self):
        verbete = criar_neologismo(self.autor, 'Publicado')
        self.client.force_authenticate(self.autor)
        resposta = self.client.patch(
            f'/api/neologismos/{verbete.pk}/', {'titulo': 'Alterado'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_edita_qualquer_verbete(self):
        verbete = criar_neologismo(self.autor, 'Publicado')
        self.client.force_authenticate(self.staff)
        resposta = self.client.patch(
            f'/api/neologismos/{verbete.pk}/', {'titulo': 'Corrigido'}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

    def test_status_nao_pode_ser_definido_pelo_cliente(self):
        self.client.force_authenticate(self.autor)
        resposta = self.client.post('/api/neologismos/', {
            'titulo': 'Autoaprovado',
            'definicao': 'Tentando burlar a moderação com um POST.',
            'classe_gramatical': 'Substantivo',
            'contexto_uso': 'Exemplo.',
            'tags': [],
            'status': 'aprovado',
        }, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Neologismo.objects.get(titulo='Autoaprovado').status,
            Neologismo.PENDENTE,
        )


@SEM_THROTTLE
class CurtidaTests(SemThrottleMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Usuario.objects.create_user('autor', password='SenhaForte123')
        cls.leitor = Usuario.objects.create_user('leitor', password='SenhaForte123')

    def setUp(self):
        super().setUp()
        self.verbete = criar_neologismo(self.autor, 'Curtível')
        self.url = f'/api/neologismos/{self.verbete.pk}/curtir/'

    def test_anonimo_recebe_401(self):
        resposta = self.client.post(self.url)
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.verbete.likes.count(), 0)

    def test_curtir_e_descurtir_alterna(self):
        self.client.force_authenticate(self.leitor)

        resposta = self.client.post(self.url)
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertTrue(resposta.data['curtido_por_mim'])
        self.assertEqual(resposta.data['total_likes'], 1)

        resposta = self.client.post(self.url)
        self.assertFalse(resposta.data['curtido_por_mim'])
        self.assertEqual(resposta.data['total_likes'], 0)

    def test_curtido_por_mim_reflete_o_usuario_da_requisicao(self):
        self.verbete.likes.add(self.leitor)

        self.client.force_authenticate(self.leitor)
        resposta = self.client.get(f'/api/neologismos/{self.verbete.pk}/')
        self.assertTrue(resposta.data['curtido_por_mim'])

        self.client.force_authenticate(self.autor)
        resposta = self.client.get(f'/api/neologismos/{self.verbete.pk}/')
        self.assertFalse(resposta.data['curtido_por_mim'])

    def test_anonimo_recebe_curtido_por_mim_falso(self):
        self.verbete.likes.add(self.leitor)
        resposta = self.client.get(f'/api/neologismos/{self.verbete.pk}/')
        self.assertFalse(resposta.data['curtido_por_mim'])

    def test_endpoint_antigo_dar_like_continua_funcionando(self):
        self.client.force_authenticate(self.leitor)
        resposta = self.client.post(
            f'/api/neologismos/{self.verbete.pk}/dar_like/'
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data['total_likes'], 1)


@SEM_THROTTLE
class ModeracaoTests(SemThrottleMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Usuario.objects.create_user('autor', password='SenhaForte123')
        cls.staff = Usuario.objects.create_user(
            'chefe', password='SenhaForte123', is_staff=True
        )

    def setUp(self):
        super().setUp()
        self.verbete = criar_neologismo(self.autor, 'Fila', Neologismo.PENDENTE)

    def test_usuario_comum_nao_aprova(self):
        self.client.force_authenticate(self.autor)
        resposta = self.client.post(f'/api/neologismos/{self.verbete.pk}/aprovar/')
        self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_aprova_e_registra_quem_moderou(self):
        self.client.force_authenticate(self.staff)
        resposta = self.client.post(f'/api/neologismos/{self.verbete.pk}/aprovar/')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)

        self.verbete.refresh_from_db()
        self.assertEqual(self.verbete.status, Neologismo.APROVADO)
        self.assertEqual(self.verbete.moderado_por, self.staff)
        self.assertIsNotNone(self.verbete.moderado_em)

    def test_rejeicao_exige_motivo(self):
        self.client.force_authenticate(self.staff)
        resposta = self.client.post(
            f'/api/neologismos/{self.verbete.pk}/rejeitar/', {}, format='json'
        )
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

        self.verbete.refresh_from_db()
        self.assertEqual(self.verbete.status, Neologismo.PENDENTE)

    def test_rejeitar_e_reativar(self):
        self.client.force_authenticate(self.staff)

        resposta = self.client.post(
            f'/api/neologismos/{self.verbete.pk}/rejeitar/',
            {'motivo_rejeicao': 'Já existe um verbete igual.'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.verbete.refresh_from_db()
        self.assertEqual(self.verbete.status, Neologismo.REJEITADO)
        self.assertEqual(self.verbete.motivo_rejeicao, 'Já existe um verbete igual.')

        resposta = self.client.post(f'/api/neologismos/{self.verbete.pk}/reativar/')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.verbete.refresh_from_db()
        self.assertEqual(self.verbete.status, Neologismo.APROVADO)
        self.assertIsNone(self.verbete.motivo_rejeicao)
        self.assertIsNotNone(self.verbete.reativado_em)

    def test_resumo_conta_por_status(self):
        criar_neologismo(self.autor, 'Ok')
        self.client.force_authenticate(self.staff)
        resposta = self.client.get('/api/neologismos/resumo/')
        self.assertEqual(resposta.data['pendente'], 1)
        self.assertEqual(resposta.data['aprovado'], 1)
        self.assertEqual(resposta.data['total'], 2)


@SEM_THROTTLE
class BuscaEFiltroTests(SemThrottleMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Usuario.objects.create_user('autor', password='SenhaForte123')
        criar_neologismo(cls.autor, 'Biscoitar', tags=['Internetês'])
        criar_neologismo(cls.autor, 'Cringe', tags=['Anglicismo'])
        criar_neologismo(cls.autor, 'Tankar', tags=['Gíria', 'Anglicismo'])

    def test_busca_por_titulo(self):
        resposta = self.client.get('/api/neologismos/?search=cring')
        titulos = [n['titulo'] for n in resposta.data['results']]
        self.assertEqual(titulos, ['Cringe'])

    def test_filtro_por_tag(self):
        resposta = self.client.get('/api/neologismos/?tag=Anglicismo')
        titulos = sorted(n['titulo'] for n in resposta.data['results'])
        self.assertEqual(titulos, ['Cringe', 'Tankar'])

    def test_ordenacao_alfabetica(self):
        resposta = self.client.get('/api/neologismos/?ordering=alfabetica')
        titulos = [n['titulo'] for n in resposta.data['results']]
        self.assertEqual(titulos, ['Biscoitar', 'Cringe', 'Tankar'])

    def test_resposta_e_paginada(self):
        resposta = self.client.get('/api/neologismos/')
        for chave in ('count', 'page', 'total_pages', 'results'):
            self.assertIn(chave, resposta.data)

    def test_facetas_lista_tags_com_contagem(self):
        resposta = self.client.get('/api/neologismos/facetas/')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        tags = {t['nome']: t['total'] for t in resposta.data['tags']}
        self.assertEqual(tags['Anglicismo'], 2)
        self.assertEqual(tags['Internetês'], 1)


@SEM_THROTTLE
class MeusVerbetesTests(SemThrottleMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Usuario.objects.create_user('autor', password='SenhaForte123')
        cls.outro = Usuario.objects.create_user('outro', password='SenhaForte123')
        criar_neologismo(cls.autor, 'Meu aprovado')
        criar_neologismo(cls.autor, 'Meu pendente', Neologismo.PENDENTE)
        criar_neologismo(cls.outro, 'Do outro')

    def test_anonimo_recebe_401(self):
        resposta = self.client.get('/api/neologismos/meus/')
        self.assertEqual(resposta.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_autor_ve_os_proprios_em_qualquer_status(self):
        self.client.force_authenticate(self.autor)
        resposta = self.client.get('/api/neologismos/meus/')
        titulos = sorted(n['titulo'] for n in resposta.data['results'])
        self.assertEqual(titulos, ['Meu aprovado', 'Meu pendente'])


@SEM_THROTTLE
class ValidacaoTests(SemThrottleMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Usuario.objects.create_user('autor', password='SenhaForte123')

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.autor)

    def _post(self, **campos):
        corpo = {
            'titulo': 'Palavra',
            'definicao': 'Uma definição suficientemente longa.',
            'classe_gramatical': 'Substantivo',
            'contexto_uso': 'Exemplo.',
            'tags': [],
        }
        corpo.update(campos)
        return self.client.post('/api/neologismos/', corpo, format='json')

    def test_definicao_curta_e_rejeitada(self):
        resposta = self._post(definicao='curta')
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('definicao', resposta.data)

    def test_tags_sao_deduplicadas_e_normalizadas(self):
        resposta = self._post(tags=['Gíria', ' gíria ', 'Anglicismo', ''])
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.data['tags'], ['Gíria', 'Anglicismo'])

    def test_limite_de_tags(self):
        resposta = self._post(tags=[f'tag{i}' for i in range(20)])
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

    def test_slug_e_gerado_a_partir_do_titulo(self):
        resposta = self._post(titulo='Mó Treta')
        self.assertEqual(resposta.data['slug'], 'mo-treta')

    def test_citacoes_vazias_sao_descartadas(self):
        resposta = self._post(contextos=[
            {'citacao': 'Uma citação real.', 'fonte': '@alguem', 'link': ''},
            {'citacao': '   ', 'fonte': '', 'link': ''},
        ])
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(resposta.data['contextos']), 1)


@SEM_THROTTLE
@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SITE_URL='https://neoscopio.test',
)
class AvisoDeModeracaoTests(SemThrottleMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.autor = Usuario.objects.create_user(
            'autor', email='autor@exemplo.com', password='SenhaForte123'
        )
        cls.sem_email = Usuario.objects.create_user(
            'anonimo', password='SenhaForte123'
        )
        cls.staff = Usuario.objects.create_user(
            'chefe', email='chefe@exemplo.com', password='SenhaForte123', is_staff=True
        )

    def setUp(self):
        super().setUp()
        mail.outbox = []
        self.client.force_authenticate(self.staff)

    def test_aprovar_avisa_o_autor_com_link(self):
        verbete = criar_neologismo(self.autor, 'Aprovável', Neologismo.PENDENTE)
        self.client.post(f'/api/neologismos/{verbete.pk}/aprovar/')

        self.assertEqual(len(mail.outbox), 1)
        mensagem = mail.outbox[0]
        self.assertIn('autor@exemplo.com', mensagem.to)
        self.assertIn(f'https://neoscopio.test/neologismo/{verbete.pk}', mensagem.body)

    def test_rejeitar_avisa_o_autor_com_o_motivo(self):
        verbete = criar_neologismo(self.autor, 'Rejeitável', Neologismo.PENDENTE)
        self.client.post(
            f'/api/neologismos/{verbete.pk}/rejeitar/',
            {'motivo_rejeicao': 'Falta uma citação com fonte real.'},
            format='json',
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Falta uma citação com fonte real.', mail.outbox[0].body)

    def test_reativar_avisa_o_autor(self):
        verbete = criar_neologismo(self.autor, 'Reativável', Neologismo.REJEITADO)
        self.client.post(f'/api/neologismos/{verbete.pk}/reativar/')
        self.assertEqual(len(mail.outbox), 1)

    def test_autor_sem_email_nao_gera_envio(self):
        verbete = criar_neologismo(self.sem_email, 'Sem contato', Neologismo.PENDENTE)
        resposta = self.client.post(f'/api/neologismos/{verbete.pk}/aprovar/')

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_falha_no_email_nao_impede_a_moderacao(self):
        """Regressão: SMTP fora do ar não pode travar a fila de moderação."""
        verbete = criar_neologismo(self.autor, 'Resiliente', Neologismo.PENDENTE)

        with patch(
            'config.emails.EmailMultiAlternatives.send',
            side_effect=SMTPException('servidor fora'),
        ):
            resposta = self.client.post(f'/api/neologismos/{verbete.pk}/aprovar/')

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        verbete.refresh_from_db()
        self.assertEqual(verbete.status, Neologismo.APROVADO)
