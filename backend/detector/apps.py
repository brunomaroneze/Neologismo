from django.apps import AppConfig


class DetectorConfig(AppConfig):
    """Detecção automática de neologismos em textos (adaptado de
    github.com/brunomaroneze/neologism_detector)."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'detector'
    verbose_name = 'Detector de neologismos'
