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
