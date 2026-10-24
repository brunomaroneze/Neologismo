from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from neologismo.models import Neologismo

from .analise import analisar, formas_para_conferir
from .classificador import classificador
from .models import PalavraIgnorada, PalavraLexico

Usuario = get_user_model()
SENHA = 'SenhaBemForte123'

# Léxico mínimo: as palavras comuns do texto de teste (o real tem 480 mil).
LEXICO = [
    'a', 'o', 'conversa', 'conversas', 'preocupar', 'preocupa', 'linguista', 'linguistas',
    'tarde', 'passar', 'chefe', 'escrita', 'virar', 'tema', 'governo', 'anunciar',
    'medida', 'medidas', 'influenciador', 'influenciadores', 'falar', 'público', 'precoce',
    'dizer', 'ir', 'fazer', 'amanhã', 'casal', 'famoso', 'mania', 'jovem', 'jovens',
    'ecológico', 'luto', 'mundo',
]
TEXTO = (
    'A emojificação das conversas preocupa linguistas. Maria passou a tarde no Instagram '
    'enquanto o João, em Vitória, tankava o chefe. A chatgptização da escrita virou tema. '
    'Os influenciadores falaram em desinfluenciar o público e em adultização precoce. '
    'Ela disse que ia fazê-lo amanhã às 9h30, com 25 casais famosos.'
)


class FormasTests(TestCase):
    def test_pronome_encliticos_e_trema(self):
        self.assertIn('fazer', formas_para_conferir('fazê-lo', 'fazê-lo'))
        self.assertIn('vender', formas_para_conferir('vendê-los', 'vendê-los'))
        self.assertIn('linguista', formas_para_conferir('lingüista', 'lingüista'))


class ClassificadorTests(TestCase):
    def test_sugere_processo_com_confianca(self):
        sugestoes = classificador.sugerir(['microcefalia', 'hipermercado'])

        self.assertEqual(len(sugestoes), 2)
        for processo, confianca in sugestoes:
            self.assertTrue(processo)
            self.assertGreater(confianca, 0)
            self.assertLessEqual(confianca, 1)
        self.assertEqual(sugestoes[0][0], 'composição neoclássica')


class AnaliseTests(TestCase):
    def setUp(self):
        PalavraLexico.objects.bulk_create(PalavraLexico(palavra=p) for p in LEXICO)

    def test_encontra_neologismos_e_ignora_o_resto(self):
        resultado = analisar(TEXTO)
        palavras = {c.palavra for c in resultado.candidatos}

        self.assertTrue({'emojificação', 'chatgptização', 'desinfluenciar', 'adultização', 'tankava'} <= palavras)
        # Nomes próprios, números, horas e palavras do léxico ficam de fora.
        self.assertFalse(palavras & {'maria', 'instagram', 'joão', 'vitória', '9h30', '25',
                                     'conversas', 'linguistas', 'fazê-lo'})

    def test_marca_os_candidatos_no_texto(self):
        resultado = analisar(TEXTO)
        marcados = {chave for _, chave in resultado.trechos if chave}
        texto_refeito = ''.join(trecho for trecho, _ in resultado.trechos)

        self.assertIn('emojificação', marcados)
        self.assertEqual(texto_refeito, TEXTO)

    def test_palavra_ignorada_some(self):
        PalavraIgnorada.objects.create(palavra='tankava')

        palavras = {c.palavra for c in analisar(TEXTO).candidatos}

        self.assertNotIn('tankava', palavras)

    def test_indica_o_que_ja_esta_no_banco(self):
        autor = Usuario.objects.create_user('autora', password=SENHA)
        existente = Neologismo.objects.create(
            titulo='Emojificação', definicao='Uso crescente de emojis na escrita.',
            classe_gramatical='Substantivo', autor=autor, status=Neologismo.APROVADO,
        )

        candidatos = {c.palavra: c for c in analisar(TEXTO).candidatos}

        self.assertEqual(candidatos['emojificação'].registrado, existente)
        self.assertIsNone(candidatos['chatgptização'].registrado)


class PainelDetectorTests(TestCase):
    def setUp(self):
        cache.clear()
        PalavraLexico.objects.bulk_create(PalavraLexico(palavra=p) for p in LEXICO)
        self.moderadora = Usuario.objects.create_user('moderadora', password=SENHA, is_staff=True)
        self.leitora = Usuario.objects.create_user('leitora', password=SENHA)

    def test_so_a_equipe_usa(self):
        self.client.login(username='leitora', password=SENHA)
        self.assertEqual(self.client.get(reverse('web:painel_detector')).status_code, 403)

    def test_analisar_e_ver_candidatos(self):
        self.client.login(username='moderadora', password=SENHA)

        resposta = self.client.post(reverse('web:painel_detector'), {'texto': TEXTO, 'fonte': 'Jornal X'}, follow=True)

        self.assertContains(resposta, 'chatgptização')
        self.assertContains(resposta, 'Processo sugerido')
        self.assertContains(resposta, '<mark class="detector__marca"', html=False)

    def test_marcar_como_nao_neologismo(self):
        self.client.login(username='moderadora', password=SENHA)
        self.client.post(reverse('web:painel_detector'), {'texto': TEXTO})

        self.client.post(reverse('web:painel_detector_ignorar'), {'palavra': 'tankava'})

        self.assertTrue(PalavraIgnorada.objects.filter(palavra='tankava', marcada_por=self.moderadora).exists())

    def test_registrar_cria_neologismo_com_abonacao(self):
        self.client.login(username='moderadora', password=SENHA)

        self.client.post(reverse('web:painel_detector_registrar'), {
            'titulo': 'chatgptização', 'classe_gramatical': 'Substantivo',
            'tipologia': 'derivação sufixal', 'definicao': 'Uso do ChatGPT na produção de textos.',
            'contexto_uso': '', 'elaborado_por': '', 'tags': '',
            'citacao': 'A chatgptização da escrita virou tema.', 'fonte': 'Jornal X', 'aprovar': '1',
        })

        novo = Neologismo.objects.get(titulo='chatgptização')
        self.assertEqual(novo.status, Neologismo.APROVADO)
        self.assertEqual(novo.autor, self.moderadora)
        self.assertEqual(novo.contextos.get().fonte, 'Jornal X')
