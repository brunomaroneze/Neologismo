"""Cria (ou promove) uma conta de administrador sem definir senha.

    python manage.py criar_admin bruno bruno@exemplo.com --nome "Bruno Maroneze"

A conta nasce sem senha utilizável e com o e-mail já confirmado. O comando
imprime um link para a própria pessoa criar a senha: ninguém além dela
conhece a senha, nem quem rodou o comando. O link vale pelo tempo de
PASSWORD_RESET_TIMEOUT e deixa de funcionar depois de usado.
"""

from allauth.account.forms import default_token_generator
from allauth.account.models import EmailAddress
from allauth.account.utils import user_pk_to_url_str
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.urls import reverse


class Command(BaseCommand):
    help = 'Cria ou promove um administrador e mostra o link para ele definir a senha.'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('email')
        parser.add_argument('--nome', default='', help='Nome completo, ex.: "Ana Maria Ribeiro"')

    @transaction.atomic
    def handle(self, *args, username, email, nome, **options):
        Usuario = get_user_model()
        email = email.strip().lower()

        dono_do_email = (
            Usuario.objects.filter(email__iexact=email).exclude(username=username).first()
        )
        if dono_do_email:
            raise CommandError(f'O e-mail {email} já pertence à conta "{dono_do_email.username}".')

        usuario, criado = Usuario.objects.get_or_create(
            username=username, defaults={'email': email},
        )
        if criado:
            usuario.set_unusable_password()
        usuario.email = email
        if nome:
            primeiro, _, resto = nome.strip().partition(' ')
            usuario.first_name, usuario.last_name = primeiro, resto
        usuario.is_admin = True  # o save() do modelo também liga is_staff
        usuario.is_active = True
        usuario.save()

        EmailAddress.objects.filter(user=usuario).exclude(email__iexact=email).update(primary=False)
        endereco, _ = EmailAddress.objects.get_or_create(
            user=usuario, email__iexact=email, defaults={'email': email},
        )
        endereco.primary = True
        endereco.verified = True
        endereco.save()

        caminho = reverse('account_reset_password_from_key', kwargs={
            'uidb36': user_pk_to_url_str(usuario),
            'key': default_token_generator.make_token(usuario),
        })
        horas = round(settings.PASSWORD_RESET_TIMEOUT / 3600)

        self.stdout.write(self.style.SUCCESS(
            f'{"Criado" if criado else "Atualizado"}: {usuario.username} <{email}>, administrador.'
        ))
        self.stdout.write(
            f'Link para definir a senha (vale {horas} h e só uma vez; envie só para essa pessoa):\n'
            f'{settings.SITE_URL}{caminho}'
        )
