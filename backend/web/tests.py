from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from neologismo.models import Contexto, Neologismo

Usuario = get_user_model()
SENHA = 'SenhaBemForte123'


def criar_verbete(autor, titulo, status=Neologismo.APROVADO, **extra):
    dados = {
        'classe_gramatical': 'SUBSTANTIVO FEMININO',
        'definicao': f'Definição de {titulo} com tamanho suficiente.',
        'tags': ['Internetês'],
    }
    dados.update(extra)
    return Neologismo.objects.create(autor=autor, titulo=titulo, status=status, **dados)


class BaseWeb(TestCase):
    def setUp(self):
        # Limites e facetas vivem no cache; cada teste começa do zero.
        cache.clear()
        self.autor = Usuario.objects.create_user('autora', email='autora@exemplo.com', password=SENHA)
        self.equipe = Usuario.objects.create_user('moderadora', email='mod@exemplo.com', password=SENHA, is_staff=True)


class ConsultaTests(BaseWeb):
    def test_inicio_mostra_so_aprovados(self):
        criar_verbete(self.autor, 'Biscoitar')
        criar_verbete(self.autor, 'Escondido', Neologismo.PENDENTE)

        resposta = self.client.get(reverse('web:inicio'))

        self.assertContains(resposta, 'Biscoitar')
        self.assertNotContains(resposta, 'Escondido')

    def test_busca_ignora_acento(self):
        criar_verbete(self.autor, 'Você-mesmo')
        criar_verbete(self.autor, 'Outro')

        resposta = self.client.get(reverse('web:inicio'), {'q': 'voce'})

        self.assertContains(resposta, 'você-mesmo')
        self.assertNotContains(resposta, '>outro<')

    def test_filtro_por_tag_e_carregar_mais_parcial(self):
        criar_verbete(self.autor, 'Comtag', tags=['Gíria'])
        criar_verbete(self.autor, 'Semtag', tags=['Outra'])

        resposta = self.client.get(reverse('web:inicio'), {'tag': 'giria', 'parcial': '1'})

        self.assertContains(resposta, 'comtag')
        self.assertNotContains(resposta, 'semtag')
        self.assertNotContains(resposta, '<html')

    def test_pagina_do_verbete_tem_citacoes_e_previa_de_link(self):
        verbete = criar_verbete(self.autor, 'Cringe')
        Contexto.objects.create(neologismo=verbete, citacao='Foi muito cringe.', fonte='Jornal X')

        resposta = self.client.get(reverse('web:verbete', args=[verbete.pk]))

        self.assertContains(resposta, 'Foi muito cringe.')
        self.assertContains(resposta, 'Jornal X')
        self.assertContains(resposta, 'Citação registrada')
        self.assertContains(resposta, 'property="og:title"')

    def test_verbete_pendente_e_404_para_o_publico_e_visivel_ao_autor(self):
        verbete = criar_verbete(self.autor, 'Rascunho', Neologismo.PENDENTE)
        url = reverse('web:verbete', args=[verbete.pk])

        self.assertEqual(self.client.get(url).status_code, 404)

        self.client.login(username='autora', password=SENHA)
        resposta = self.client.get(url)
        self.assertContains(resposta, 'Em moderação.')
        self.assertContains(resposta, 'noindex')

    def test_sitemap_lista_so_aprovados(self):
        publicado = criar_verbete(self.autor, 'Publicado')
        pendente = criar_verbete(self.autor, 'Pendente', Neologismo.PENDENTE)

        resposta = self.client.get(reverse('web:sitemap'))

        self.assertEqual(resposta['Content-Type'], 'application/xml')
        self.assertContains(resposta, f'/neologismo/{publicado.pk}<')
        self.assertNotContains(resposta, f'/neologismo/{pendente.pk}<')

    def test_paginas_institucionais(self):
        for nome in ('web:sobre', 'web:equipe', 'web:referencias', 'web:robots'):
            with self.subTest(nome=nome):
                self.assertEqual(self.client.get(reverse(nome)).status_code, 200)


class CurtirTests(BaseWeb):
    def test_curtir_exige_login(self):
        verbete = criar_verbete(self.autor, 'Tankar')

        resposta = self.client.post(reverse('web:curtir', args=[verbete.pk]))

        self.assertRedirects(resposta, f"{reverse('web:login')}?next={reverse('web:curtir', args=[verbete.pk])}", fetch_redirect_response=False)
        self.assertEqual(verbete.likes.count(), 0)

    def test_curtir_alterna_e_responde_json(self):
        verbete = criar_verbete(self.autor, 'Tankar')
        self.client.login(username='autora', password=SENHA)
        url = reverse('web:curtir', args=[verbete.pk])

        primeira = self.client.post(url, HTTP_ACCEPT='application/json')
        segunda = self.client.post(url, HTTP_ACCEPT='application/json')

        self.assertEqual(primeira.json(), {'curtido': True, 'total': 1})
        self.assertEqual(segunda.json(), {'curtido': False, 'total': 0})

    def test_curtir_sem_javascript_volta_para_a_pagina(self):
        verbete = criar_verbete(self.autor, 'Tankar')
        self.client.login(username='autora', password=SENHA)

        resposta = self.client.post(reverse('web:curtir', args=[verbete.pk]), {'next': '/?q=tankar'})

        self.assertRedirects(resposta, '/?q=tankar', fetch_redirect_response=False)

    def test_next_externo_e_ignorado(self):
        verbete = criar_verbete(self.autor, 'Tankar')
        self.client.login(username='autora', password=SENHA)

        resposta = self.client.post(reverse('web:curtir', args=[verbete.pk]), {'next': 'https://malicioso.example/'})

        self.assertRedirects(resposta, reverse('web:inicio'), fetch_redirect_response=False)


class EnvioTests(BaseWeb):
    def test_envio_valido_fica_pendente_com_abonacoes(self):
        self.client.login(username='autora', password=SENHA)

        resposta = self.client.post(reverse('web:enviar'), {
            'titulo': '  Desver  ',
            'classe_gramatical': 'Verbo transitivo direto',
            'definicao': 'Fazer de conta que não viu algo constrangedor.',
            'contexto_uso': '',
            'tags': 'Internetês, internetês ,Gíria',
            'citacao': ['Vou desver essa cena.', ''],
            'fonte': ['Perfil no X', ''],
            'link': ['https://exemplo.com/a', ''],
        })

        self.assertRedirects(resposta, f"{reverse('web:enviar')}?enviado=1", fetch_redirect_response=False)
        verbete = Neologismo.objects.get(titulo='Desver')
        self.assertEqual(verbete.status, Neologismo.PENDENTE)
        self.assertEqual(verbete.autor, self.autor)
        self.assertEqual(verbete.tags, ['Internetês', 'Gíria'])
        self.assertEqual(list(verbete.contextos.values_list('citacao', flat=True)), ['Vou desver essa cena.'])

    def test_envio_invalido_mostra_erros_e_preserva_valores(self):
        self.client.login(username='autora', password=SENHA)

        resposta = self.client.post(reverse('web:enviar'), {
            'titulo': 'Ok',
            'classe_gramatical': 'Verbo',
            'definicao': 'curta',
            'tags': '',
            'citacao': [''], 'fonte': [''], 'link': [''],
        })

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Descreva o significado com pelo menos 10 caracteres.')
        self.assertContains(resposta, 'Revise os campos destacados abaixo.')
        self.assertContains(resposta, 'value="Ok"')
        self.assertFalse(Neologismo.objects.exists())

    def test_envio_exige_login(self):
        self.assertContains(self.client.get(reverse('web:enviar')), 'Entre para enviar')

        resposta = self.client.post(reverse('web:enviar'), {'titulo': 'X'})
        self.assertRedirects(resposta, f"{reverse('web:login')}?next={reverse('web:enviar')}", fetch_redirect_response=False)
        self.assertFalse(Neologismo.objects.exists())

    def test_meus_envios_mostra_motivo_da_rejeicao(self):
        criar_verbete(self.autor, 'Recusado', Neologismo.REJEITADO, motivo_rejeicao='Falta fonte verificável.')
        self.client.login(username='autora', password=SENHA)

        resposta = self.client.get(reverse('web:meus_envios'), {'status': 'rejeitado'})

        self.assertContains(resposta, 'Falta fonte verificável.')


class ModeracaoTests(BaseWeb):
    def test_usuario_comum_recebe_403(self):
        self.client.login(username='autora', password=SENHA)
        self.assertEqual(self.client.get(reverse('web:moderacao')).status_code, 403)

    def test_aprovar_publica_e_avisa_o_autor(self):
        verbete = criar_verbete(self.autor, 'Novo', Neologismo.PENDENTE)
        self.client.login(username='moderadora', password=SENHA)

        resposta = self.client.post(
            reverse('web:moderar', args=[verbete.pk, 'aprovar']),
            {'voltar': '/admin-painel?status=pendente'},
        )

        self.assertRedirects(resposta, '/admin-painel?status=pendente', fetch_redirect_response=False)
        verbete.refresh_from_db()
        self.assertEqual(verbete.status, Neologismo.APROVADO)
        self.assertEqual(verbete.moderado_por, self.equipe)
        self.assertEqual(len(mail.outbox), 1)

    def test_rejeitar_exige_motivo(self):
        verbete = criar_verbete(self.autor, 'Novo', Neologismo.PENDENTE)
        self.client.login(username='moderadora', password=SENHA)
        url = reverse('web:moderar', args=[verbete.pk, 'rejeitar'])

        self.client.post(url, {'motivo': 'não'})
        verbete.refresh_from_db()
        self.assertEqual(verbete.status, Neologismo.PENDENTE)

        self.client.post(url, {'motivo': 'Já existe um verbete equivalente.'})
        verbete.refresh_from_db()
        self.assertEqual(verbete.status, Neologismo.REJEITADO)
        self.assertEqual(verbete.motivo_rejeicao, 'Já existe um verbete equivalente.')

    def test_moderacao_por_get_nao_altera_nada(self):
        verbete = criar_verbete(self.autor, 'Novo', Neologismo.PENDENTE)
        self.client.login(username='moderadora', password=SENHA)

        resposta = self.client.get(reverse('web:moderar', args=[verbete.pk, 'aprovar']))

        self.assertEqual(resposta.status_code, 405)
        verbete.refresh_from_db()
        self.assertEqual(verbete.status, Neologismo.PENDENTE)


class ContaTests(BaseWeb):
    def test_login_e_logout(self):
        resposta = self.client.post(reverse('web:login'), {'username': 'autora', 'password': SENHA, 'next': '/enviar'})
        self.assertRedirects(resposta, '/enviar', fetch_redirect_response=False)

        self.client.post(reverse('web:logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_errado_nao_diz_qual_campo_falhou(self):
        resposta = self.client.post(reverse('web:login'), {'username': 'autora', 'password': 'errada'})
        self.assertContains(resposta, 'Usuário ou senha inválidos.')

    def test_login_bloqueia_forca_bruta(self):
        for _ in range(10):
            self.client.post(reverse('web:login'), {'username': 'autora', 'password': 'errada'})

        resposta = self.client.post(reverse('web:login'), {'username': 'autora', 'password': SENHA})

        self.assertContains(resposta, 'Muitas tentativas')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cadastro_cria_conta_e_entra(self):
        resposta = self.client.post(reverse('web:cadastro'), {
            'username': 'nova', 'email': 'nova@exemplo.com',
            'password': SENHA, 'password_confirmacao': SENHA,
        })

        self.assertRedirects(resposta, reverse('web:inicio'), fetch_redirect_response=False)
        self.assertTrue(Usuario.objects.filter(username='nova').exists())
        self.assertIn('_auth_user_id', self.client.session)

    def test_cadastro_rejeita_usuario_repetido_sem_diferenciar_caixa(self):
        resposta = self.client.post(reverse('web:cadastro'), {
            'username': 'AUTORA', 'email': '', 'password': SENHA, 'password_confirmacao': SENHA,
        })
        self.assertContains(resposta, 'já está em uso')

    def test_recuperar_senha_nao_revela_se_o_email_existe(self):
        existe = self.client.post(reverse('web:recuperar_senha'), {'email': 'autora@exemplo.com'})
        nao_existe = self.client.post(reverse('web:recuperar_senha'), {'email': 'ninguem@exemplo.com'})

        self.assertContains(existe, 'Se existe uma conta')
        self.assertContains(nao_existe, 'Se existe uma conta')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('/redefinir-senha/', mail.outbox[0].body)

    def test_redefinir_senha_pelo_link(self):
        uid = urlsafe_base64_encode(force_bytes(self.autor.pk))
        token = default_token_generator.make_token(self.autor)
        url = reverse('web:redefinir_senha', args=[uid, token])
        nova = 'OutraSenhaForte456'

        resposta = self.client.post(url, {'password': nova, 'password_confirmacao': nova})

        self.assertRedirects(resposta, reverse('web:inicio'), fetch_redirect_response=False)
        self.autor.refresh_from_db()
        self.assertTrue(self.autor.check_password(nova))
        # O link é de uso único.
        self.assertContains(self.client.get(url), 'Este link já foi usado ou passou da validade.')
