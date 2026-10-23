"""Cria o registro de e-mail do allauth para as contas anteriores a ele.

Com a confirmação de e-mail obrigatória, o allauth só deixa entrar quem tem um
EmailAddress verificado. Contas da equipe (staff) entram como verificadas, para
a moderação não ficar trancada no primeiro deploy; as demais recebem o link de
confirmação automaticamente na próxima tentativa de login.

Contas sem e-mail não ganham registro: precisam cadastrar um e confirmar.
"""

from django.db import migrations


def criar_enderecos(apps, schema_editor):
    Usuario = apps.get_model('usuario', 'Usuario')
    EmailAddress = apps.get_model('account', 'EmailAddress')

    vistos = set()
    for usuario in Usuario.objects.exclude(email='').exclude(email__isnull=True).order_by('id'):
        email = usuario.email.strip()
        # Bases antigas podem ter o mesmo e-mail em mais de uma conta; o
        # allauth exige e-mail único, então só a conta mais antiga fica com ele.
        if email.lower() in vistos or EmailAddress.objects.filter(email__iexact=email).exists():
            continue
        vistos.add(email.lower())
        EmailAddress.objects.create(
            user=usuario,
            email=email,
            primary=True,
            verified=usuario.is_staff,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('usuario', '0002_usuario_is_admin'),
        ('account', '0009_emailaddress_unique_primary_email'),
    ]

    operations = [
        migrations.RunPython(criar_enderecos, migrations.RunPython.noop),
    ]
