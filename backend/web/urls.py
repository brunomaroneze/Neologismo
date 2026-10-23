# Os endereços repetem os do frontend antigo (Next.js): links já
# compartilhados e os enviados nos e-mails continuam funcionando.
from django.urls import path

from . import views

app_name = 'web'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('neologismo/<int:pk>', views.verbete, name='verbete'),
    path('neologismo/<int:pk>/curtir', views.curtir, name='curtir'),

    path('enviar', views.enviar, name='enviar'),
    path('minhas-palavras', views.meus_envios, name='meus_envios'),

    path('admin-painel', views.moderacao_painel, name='moderacao'),
    path('admin-painel/<int:pk>/<str:acao>', views.moderar, name='moderar'),

    # Endereços antigos das telas de conta, agora servidas pelo allauth em
    # /conta/. Mantidos como redirecionamento para links salvos e e-mails já
    # enviados (o link de redefinição antigo leva a pedir um novo).
    path('login', views.redirecionar('account_login'), name='login'),
    path('cadastro', views.redirecionar('account_signup'), name='cadastro'),
    path('recuperar-senha', views.redirecionar('account_reset_password'), name='recuperar_senha'),
    path('redefinir-senha/<str:uid>/<str:token>', views.redirecionar('account_reset_password')),

    path('sobre', views.sobre, name='sobre'),
    path('equipe', views.equipe, name='equipe'),
    path('indicacoes-de-leitura', views.referencias, name='referencias'),

    path('sitemap.xml', views.sitemap, name='sitemap'),
    path('robots.txt', views.robots, name='robots'),
]
