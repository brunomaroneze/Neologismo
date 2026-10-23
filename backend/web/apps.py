from django.apps import AppConfig


class WebConfig(AppConfig):
    """Páginas do site, renderizadas pelo próprio Django."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'web'
