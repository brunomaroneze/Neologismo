import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase


class ConfiguracaoTests(SimpleTestCase):
    """Protege configurações que um merge pode sabotar em silêncio."""

    def test_paginacao_customizada_esta_ativa(self):
        """Regressão: um merge trouxe um segundo DEFAULT_PAGINATION_CLASS para
        dentro de REST_FRAMEWORK. Chave duplicada em dict Python não dá erro —
        a última vence — e a paginação com `page`/`total_pages` era descartada
        sem nenhum aviso."""
        self.assertEqual(
            settings.REST_FRAMEWORK['DEFAULT_PAGINATION_CLASS'],
            'config.pagination.PaginacaoPadrao',
        )

    def test_escopos_de_throttle_declarados(self):
        """Um ScopedRateThrottle com escopo ausente levanta
        ImproperlyConfigured só quando a rota é chamada."""
        taxas = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        for escopo in ('login', 'cadastro', 'envio', 'curtida'):
            self.assertIn(escopo, taxas)

    def _carregar_settings(self, chave):
        """Importa o settings num processo novo: ele é avaliado no import."""
        ambiente = {
            **os.environ,
            'DJANGO_SETTINGS_MODULE': 'config.settings',
            'DEBUG': 'False',
            'SECRET_KEY': chave,
            'ALLOWED_HOSTS': 'neoscopio.exemplo.com',
        }
        return subprocess.run(
            [sys.executable, '-c', 'import django; django.setup()'],
            env=ambiente, cwd=settings.BASE_DIR, capture_output=True, text=True,
        )

    def test_producao_recusa_secret_key_de_exemplo(self):
        for chave in ('chave-de-desenvolvimento-nao-use-em-producao', 'curta'):
            with self.subTest(chave=chave):
                resultado = self._carregar_settings(chave)
                self.assertNotEqual(resultado.returncode, 0)
                self.assertIn('SECRET_KEY fraca', resultado.stderr)

    def test_producao_aceita_secret_key_forte(self):
        resultado = self._carregar_settings('k8Jd2-' * 12)
        self.assertEqual(resultado.returncode, 0, resultado.stderr)
