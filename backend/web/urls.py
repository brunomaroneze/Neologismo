# Os endereços repetem os do frontend antigo (Next.js): links já
# compartilhados e os enviados nos e-mails continuam funcionando.
from django.urls import path

from . import painel, views

app_name = 'web'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('neologismo/<int:pk>', views.verbete, name='verbete'),
    path('neologismo/<int:pk>/curtir', views.curtir, name='curtir'),

    path('enviar', views.enviar, name='enviar'),
    path('minhas-palavras', views.meus_envios, name='meus_envios'),
    path('perfil', views.perfil, name='perfil'),

    # Painel do administrador (web/painel.py).
    path('admin-painel', painel.inicio, name='moderacao'),
    path('admin-painel/verbetes', painel.verbetes, name='painel_verbetes'),
    path('admin-painel/verbetes/lote', painel.lote, name='painel_lote'),
    path('admin-painel/verbetes/<int:pk>/editar', painel.editar_verbete,
         name='painel_editar_verbete'),
    path('admin-painel/<int:pk>/<str:acao>', painel.moderar, name='moderar'),
    path('admin-painel/detector', painel.detector, name='painel_detector'),
    path('admin-painel/detector/ignorar', painel.detector_ignorar, name='painel_detector_ignorar'),
    path('admin-painel/detector/registrar', painel.detector_registrar,
         name='painel_detector_registrar'),
    path('admin-painel/leituras', painel.leituras, name='painel_leituras'),
    path('admin-painel/leituras/nova', painel.referencia, name='painel_referencia_nova'),
    path('admin-painel/leituras/<int:pk>', painel.referencia, name='painel_referencia'),
    path('admin-painel/leituras/<int:pk>/remover', painel.referencia_remover,
         name='painel_referencia_remover'),
    path('admin-painel/leituras/areas', painel.area_adicionar, name='painel_area_adicionar'),
    path('admin-painel/leituras/areas/<int:pk>/remover', painel.area_remover,
         name='painel_area_remover'),
    path('admin-painel/usuarios', painel.usuarios, name='painel_usuarios'),
    path('admin-painel/usuarios/<int:pk>/<str:acao>', painel.usuario_acao,
         name='painel_usuario_acao'),
    path('admin-painel/equipe', painel.equipe, name='painel_equipe'),
    path('admin-painel/equipe/novo', painel.membro, name='painel_membro_novo'),
    path('admin-painel/equipe/<int:pk>', painel.membro, name='painel_membro'),
    path('admin-painel/equipe/<int:pk>/remover', painel.membro_remover,
         name='painel_membro_remover'),
    path('admin-painel/equipe/<int:pk>/grupo', painel.membro_grupo,
         name='painel_membro_grupo'),
    path('admin-painel/equipe/<int:pk>/<str:direcao>', painel.membro_mover,
         name='painel_membro_mover'),

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
