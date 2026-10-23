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

    path('login', views.login_view, name='login'),
    path('sair', views.logout_view, name='logout'),
    path('cadastro', views.cadastro, name='cadastro'),
    path('recuperar-senha', views.recuperar_senha, name='recuperar_senha'),
    path('redefinir-senha/<str:uid>/<str:token>', views.redefinir_senha, name='redefinir_senha'),

    path('sobre', views.sobre, name='sobre'),
    path('equipe', views.equipe, name='equipe'),
    path('indicacoes-de-leitura', views.referencias, name='referencias'),

    path('sitemap.xml', views.sitemap, name='sitemap'),
    path('robots.txt', views.robots, name='robots'),
]
