from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

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

    def test_filtro_por_tag_aceita_sem_acento(self):
        criar_verbete(self.autor, 'Comtag', tags=['Gíria'])
        criar_verbete(self.autor, 'Semtag', tags=['Outra'])

        resposta = self.client.get(reverse('web:inicio'), {'tag': 'giria'})

        self.assertContains(resposta, 'comtag')
        self.assertNotContains(resposta, 'semtag')

    def test_inicio_mostra_12_e_carregar_mais(self):
        for i in range(30):
            criar_verbete(self.autor, f'Palavra{i:02d}')

        resposta = self.client.get(reverse('web:inicio'))

        self.assertEqual(len(resposta.context['pagina'].object_list), 12)
        self.assertContains(resposta, 'href="?pagina=2#explorar" data-carregar-mais')
        self.assertContains(resposta, 'data-ver-menos hidden')

    def test_carregar_mais_parcial_traz_so_os_cards(self):
        for i in range(30):
            criar_verbete(self.autor, f'Palavra{i:02d}', tags=['Gíria'])

        resposta = self.client.get(reverse('web:inicio'), {'tag': 'Gíria', 'pagina': 2, 'parcial': '1'})

        self.assertNotContains(resposta, '<html')
        self.assertEqual(resposta.content.decode().count('class="card"'), 12)
        self.assertContains(resposta, 'data-proxima="?tag=G%C3%ADria&amp;pagina=3"')

    def test_paginacao_numerada_em_minhas_palavras(self):
        for i in range(25):
            criar_verbete(self.autor, f'Meu{i:02d}', Neologismo.PENDENTE)
        self.client.login(username='autora', password=SENHA)

        resposta = self.client.get(reverse('web:meus_envios'))

        self.assertContains(resposta, 'Página 1 de 2')
        self.assertContains(resposta, 'aria-label="Próxima página"')

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

        self.assertRedirects(resposta, f"{reverse('account_login')}?next={reverse('web:curtir', args=[verbete.pk])}", fetch_redirect_response=False)
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
        self.assertRedirects(resposta, f"{reverse('account_login')}?next={reverse('web:enviar')}", fetch_redirect_response=False)
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
        self.assertEqual(self.client.get(reverse('web:painel_verbetes')).status_code, 403)

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
    """Contas pelo django-allauth: confirmação de e-mail obrigatória."""

    def setUp(self):
        super().setUp()
        # Contas criadas direto no banco (fora do fluxo do allauth) já entram
        # com o e-mail confirmado, para os demais testes poderem logar.
        for usuario in (self.autor, self.equipe):
            EmailAddress.objects.create(user=usuario, email=usuario.email, primary=True, verified=True)

    def cadastrar(self, **extra):
        dados = {
            'username': 'nova', 'email': 'nova@exemplo.com',
            'password1': SENHA, 'password2': SENHA,
        }
        dados.update(extra)
        return self.client.post(reverse('account_signup'), dados)

    def test_cadastro_envia_confirmacao_e_nao_entra_antes(self):
        resposta = self.cadastrar()

        self.assertRedirects(resposta, reverse('account_email_verification_sent'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('nova@exemplo.com', mail.outbox[0].to)

        # Tentar entrar antes de confirmar reenvia a confirmação e não loga.
        self.client.post(reverse('account_login'), {'login': 'nova', 'password': SENHA})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_confirmar_email_libera_a_conta(self):
        self.cadastrar()
        endereco = EmailAddress.objects.get(email='nova@exemplo.com')
        chave = EmailConfirmationHMAC(endereco).key

        # O GET só mostra o botão de confirmar (antivírus abrem links sozinhos).
        self.client.get(reverse('account_confirm_email', args=[chave]))
        endereco.refresh_from_db()
        self.assertFalse(endereco.verified)

        self.client.post(reverse('account_confirm_email', args=[chave]))
        endereco.refresh_from_db()
        self.assertTrue(endereco.verified)

    def test_login_por_usuario_ou_email_e_logout(self):
        for identificador in ('autora', 'autora@exemplo.com'):
            with self.subTest(identificador=identificador):
                self.client.logout()
                resposta = self.client.post(reverse('account_login'), {'login': identificador, 'password': SENHA})
                self.assertRedirects(resposta, '/', fetch_redirect_response=False)
                self.assertIn('_auth_user_id', self.client.session)

        self.client.post(reverse('account_logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cadastro_com_email_existente_nao_revela_nem_duplica(self):
        """Quem tenta cadastrar um e-mail alheio vê a mesma tela de sempre;
        o dono do e-mail recebe um aviso. A página não serve para descobrir
        quem tem conta."""
        resposta = self.cadastrar(username='outra', email='AUTORA@exemplo.com')

        self.assertRedirects(resposta, reverse('account_email_verification_sent'), fetch_redirect_response=False)
        self.assertFalse(Usuario.objects.filter(username='outra').exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('autora@exemplo.com', [e.lower() for e in mail.outbox[0].to])

    def test_enderecos_antigos_redirecionam(self):
        for antigo, novo in (
            ('/login?next=/enviar', '/conta/login/?next=%2Fenviar'),
            ('/cadastro', '/conta/signup/'),
            ('/recuperar-senha', '/conta/password/reset/'),
            ('/redefinir-senha/abc/def', '/conta/password/reset/'),
        ):
            with self.subTest(antigo=antigo):
                self.assertRedirects(self.client.get(antigo), novo, fetch_redirect_response=False)

    def test_botoes_sociais_so_com_credenciais(self):
        with override_settings(SOCIALACCOUNT_PROVIDERS={}):
            self.assertNotContains(self.client.get(reverse('account_login')), 'Continuar com')
        com_google = {'google': {'APPS': [{'client_id': 'x', 'secret': 'y'}]}}
        with override_settings(SOCIALACCOUNT_PROVIDERS=com_google):
            resposta = self.client.get(reverse('account_login'))
            self.assertContains(resposta, 'Continuar com Google')
            self.assertNotContains(resposta, 'Continuar com Facebook')

    def test_recuperar_senha_nao_revela_se_o_email_existe(self):
        existe = self.client.post(reverse('account_reset_password'), {'email': 'autora@exemplo.com'})
        nao_existe = self.client.post(reverse('account_reset_password'), {'email': 'ninguem@exemplo.com'})

        self.assertRedirects(existe, reverse('account_reset_password_done'), fetch_redirect_response=False)
        self.assertRedirects(nao_existe, reverse('account_reset_password_done'), fetch_redirect_response=False)


class PainelTests(BaseWeb):
    """Painel do administrador: moderação, usuários e equipe."""

    def setUp(self):
        super().setUp()
        self.admin = Usuario.objects.create_user('chefe', email='chefe@exemplo.com', password=SENHA, is_admin=True)

    def test_moderador_ve_verbetes_mas_nao_usuarios_nem_equipe(self):
        self.client.login(username='moderadora', password=SENHA)
        self.assertEqual(self.client.get(reverse('web:moderacao')).status_code, 200)
        self.assertEqual(self.client.get(reverse('web:painel_verbetes')).status_code, 200)
        self.assertEqual(self.client.get(reverse('web:painel_usuarios')).status_code, 403)
        self.assertEqual(self.client.get(reverse('web:painel_equipe')).status_code, 403)

    def test_aprovar_em_lote(self):
        a = criar_verbete(self.autor, 'Um', Neologismo.PENDENTE)
        b = criar_verbete(self.autor, 'Dois', Neologismo.PENDENTE)
        c = criar_verbete(self.autor, 'Tres', Neologismo.PENDENTE)
        self.client.login(username='moderadora', password=SENHA)

        self.client.post(reverse('web:painel_lote'), {'acao': 'aprovar', 'ids': [a.pk, b.pk]})

        self.assertEqual(
            dict(Neologismo.objects.values_list('titulo', 'status')),
            {'Um': 'aprovado', 'Dois': 'aprovado', 'Tres': 'pendente'},
        )
        self.assertEqual(len(mail.outbox), 2)

    def test_rejeitar_em_lote_exige_motivo(self):
        a = criar_verbete(self.autor, 'Um', Neologismo.PENDENTE)
        self.client.login(username='moderadora', password=SENHA)

        self.client.post(reverse('web:painel_lote'), {'acao': 'rejeitar', 'ids': [a.pk], 'motivo': ''})
        a.refresh_from_db()
        self.assertEqual(a.status, Neologismo.PENDENTE)

        self.client.post(reverse('web:painel_lote'), {'acao': 'rejeitar', 'ids': [a.pk], 'motivo': 'Falta abonação com fonte.'})
        a.refresh_from_db()
        self.assertEqual(a.status, Neologismo.REJEITADO)
        self.assertEqual(a.motivo_rejeicao, 'Falta abonação com fonte.')

    def test_editar_e_aprovar(self):
        verbete = criar_verbete(self.autor, 'Biscoiter', Neologismo.PENDENTE)
        self.client.login(username='moderadora', password=SENHA)

        resposta = self.client.post(reverse('web:painel_editar_verbete', args=[verbete.pk]), {
            'titulo': 'Biscoitar', 'classe_gramatical': 'Verbo intransitivo', 'tipologia': 'derivação sufixal',
            'definicao': 'Buscar elogios nas redes sociais.', 'contexto_uso': '', 'elaborado_por': '',
            'tags': 'Internetês, Gíria', 'aprovar': '1',
        })

        self.assertEqual(resposta.status_code, 302)
        verbete.refresh_from_db()
        self.assertEqual(verbete.titulo, 'Biscoitar')
        self.assertEqual(verbete.tags, ['Internetês', 'Gíria'])
        self.assertEqual(verbete.status, Neologismo.APROVADO)

    def test_editar_valida_como_o_envio(self):
        verbete = criar_verbete(self.autor, 'Algo', Neologismo.PENDENTE)
        self.client.login(username='moderadora', password=SENHA)

        resposta = self.client.post(reverse('web:painel_editar_verbete', args=[verbete.pk]), {
            'titulo': 'Algo', 'classe_gramatical': 'Verbo', 'definicao': 'curta', 'tags': '',
        })

        self.assertContains(resposta, 'Descreva o significado com ao menos 10 caracteres.')

    def test_admin_muda_papel_e_nao_mexe_na_propria_conta(self):
        self.client.login(username='chefe', password=SENHA)

        self.client.post(reverse('web:painel_usuario_acao', args=[self.autor.pk, 'papel']), {'papel': 'moderador'})
        self.autor.refresh_from_db()
        self.assertTrue(self.autor.is_staff)
        self.assertFalse(self.autor.is_admin)

        self.client.post(reverse('web:painel_usuario_acao', args=[self.admin.pk, 'papel']), {'papel': 'leitor'})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_admin)

    def test_rebaixar_administrador_tira_o_acesso_de_moderacao(self):
        outro = Usuario.objects.create_user('outro', password=SENHA, is_admin=True)
        self.client.login(username='chefe', password=SENHA)

        self.client.post(reverse('web:painel_usuario_acao', args=[outro.pk, 'papel']), {'papel': 'leitor'})

        outro.refresh_from_db()
        self.assertFalse(outro.is_admin)
        self.assertFalse(outro.is_staff)

    def test_desativar_e_confirmar_email(self):
        self.client.login(username='chefe', password=SENHA)

        self.client.post(reverse('web:painel_usuario_acao', args=[self.autor.pk, 'confirmar-email']))
        self.assertTrue(EmailAddress.objects.filter(user=self.autor, verified=True).exists())

        self.client.post(reverse('web:painel_usuario_acao', args=[self.autor.pk, 'desativar']))
        self.autor.refresh_from_db()
        self.assertFalse(self.autor.is_active)

    def test_adicionar_membro_com_foto_reduz_para_400(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        from .models import MembroEquipe

        bruta = BytesIO()
        Image.new('RGB', (1200, 800), (102, 0, 102)).save(bruta, 'PNG')
        foto = SimpleUploadedFile('retrato.png', bruta.getvalue(), content_type='image/png')
        self.client.login(username='chefe', password=SENHA)

        resposta = self.client.post(reverse('web:painel_membro_novo'), {
            'nome': 'Nova Pesquisadora', 'funcao': 'Graduanda em Letras', 'bio': '', 'ativo': 'on', 'foto': foto,
        })

        self.assertRedirects(resposta, reverse('web:painel_equipe'), fetch_redirect_response=False)
        membro = MembroEquipe.objects.get(nome='Nova Pesquisadora')
        try:
            with Image.open(membro.foto.path) as salva:
                self.assertEqual(salva.size, (400, 400))
                self.assertEqual(salva.format, 'JPEG')
            self.assertContains(self.client.get(reverse('web:equipe')), 'Nova Pesquisadora')
        finally:
            membro.foto.delete(save=False)

    def test_foto_que_nao_e_imagem_e_recusada(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        from .models import MembroEquipe

        falsa = SimpleUploadedFile('foto.jpg', b'<?php echo 1; ?>', content_type='image/jpeg')
        self.client.login(username='chefe', password=SENHA)

        resposta = self.client.post(reverse('web:painel_membro_novo'), {
            'nome': 'Teste', 'funcao': 'Teste', 'ativo': 'on', 'foto': falsa,
        })

        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(MembroEquipe.objects.filter(nome='Teste').exists())

    def test_reordenar_e_remover_membro(self):
        from .models import MembroEquipe

        MembroEquipe.objects.all().delete()
        a = MembroEquipe.objects.create(nome='Ana', funcao='x', ordem=10)
        b = MembroEquipe.objects.create(nome='Bia', funcao='x', ordem=20)
        self.client.login(username='chefe', password=SENHA)

        self.client.post(reverse('web:painel_membro_mover', args=[b.pk, 'subir']))
        self.assertEqual(list(MembroEquipe.objects.values_list('nome', flat=True)), ['Bia', 'Ana'])

        self.client.post(reverse('web:painel_membro_remover', args=[a.pk]))
        self.assertEqual(list(MembroEquipe.objects.values_list('nome', flat=True)), ['Bia'])
