"""Rotas do projeto Neoscópio."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from config.views import HealthView
from neologismo.views import NeologismoViewSet
from usuario.views import (
    LoginView,
    LogoutView,
    MeView,
    RecuperarSenhaView,
    RedefinirSenhaView,
    RegistroView,
)

router = DefaultRouter()
router.register(r'neologismos', NeologismoViewSet, basename='neologismo')

urlpatterns = [
    path('', RedirectView.as_view(url='/api/docs/', permanent=False)),
    path('admin/', admin.site.urls),

    # Usado pelo healthcheck do Docker e pelo proxy antes de mandar tráfego.
    path('api/health/', HealthView.as_view(), name='api_health'),

    path('api/', include(router.urls)),
    path('api/login/', LoginView.as_view(), name='api_login'),
    path('api/logout/', LogoutView.as_view(), name='api_logout'),
    path('api/cadastro/', RegistroView.as_view(), name='api_cadastro'),
    path('api/me/', MeView.as_view(), name='api_me'),
    path(
        'api/senha/recuperar/',
        RecuperarSenhaView.as_view(),
        name='api_recuperar_senha',
    ),
    path(
        'api/senha/redefinir/',
        RedefinirSenhaView.as_view(),
        name='api_redefinir_senha',
    ),

    # Documentação (OpenAPI + Swagger UI)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
