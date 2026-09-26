"""Envio de e-mail do projeto.

Regra que vale para tudo aqui: **e-mail nunca derruba a ação do usuário**.
Se o SMTP estiver fora, aprovar um verbete ou pedir recuperação de senha
continua funcionando — a falha vai para o log (e para o Sentry), não para a
cara de quem clicou.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def enviar_email(assunto, template, contexto, destinatarios):
    """Renderiza um template e envia. Devolve True se saiu, False se falhou.

    `template` é o nome do arquivo HTML; o par em `.txt` é usado como versão
    em texto puro. Todo e-mail sai nas duas versões: só-HTML cai em spam com
    muito mais facilidade, e `strip_tags` sobre o HTML não serve como texto —
    ele descarta os `href`, então o e-mail chegaria com "clique aqui" e
    nenhum endereço visível.
    """
    destinatarios = [e for e in destinatarios if e]
    if not destinatarios:
        return False

    contexto = {**contexto, 'site_url': settings.SITE_URL}

    try:
        corpo_html = render_to_string(template, contexto)
        corpo_texto = render_to_string(
            template.rsplit('.', 1)[0] + '.txt', contexto
        )

        mensagem = EmailMultiAlternatives(
            subject=assunto,
            body=corpo_texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=destinatarios,
        )
        mensagem.attach_alternative(corpo_html, 'text/html')
        mensagem.send(fail_silently=False)
        return True
    except Exception:
        # `exception` já inclui o traceback e a integração de logging do
        # Sentry captura ERROR como evento.
        logger.exception(
            'Falha ao enviar e-mail "%s" para %s', assunto, destinatarios
        )
        return False


def avisar_verbete_aprovado(neologismo):
    return enviar_email(
        assunto=f'Seu verbete "{neologismo.titulo}" foi publicado',
        template='emails/verbete_aprovado.html',
        contexto={
            'neologismo': neologismo,
            'url_verbete': f'{settings.SITE_URL}/neologismo/{neologismo.pk}',
        },
        destinatarios=[neologismo.autor.email],
    )


def avisar_verbete_rejeitado(neologismo):
    return enviar_email(
        assunto=f'Sobre o verbete "{neologismo.titulo}"',
        template='emails/verbete_rejeitado.html',
        contexto={
            'neologismo': neologismo,
            'url_meus_envios': f'{settings.SITE_URL}/minhas-palavras',
            'url_enviar': f'{settings.SITE_URL}/enviar',
        },
        destinatarios=[neologismo.autor.email],
    )


def enviar_recuperacao_senha(usuario, uid, token):
    return enviar_email(
        assunto='Redefinir sua senha no Neoscópio',
        template='emails/recuperar_senha.html',
        contexto={
            'usuario': usuario,
            'url_redefinicao': f'{settings.SITE_URL}/redefinir-senha/{uid}/{token}',
            'validade_horas': round(settings.PASSWORD_RESET_TIMEOUT / 3600),
        },
        destinatarios=[usuario.email],
    )
