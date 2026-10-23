from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Liga a extensão `unaccent` do Postgres.

    É o que permite a busca ignorar acentos. `CREATE EXTENSION` exige um
    usuário com permissão para instalar extensões — nas imagens oficiais do
    Postgres o usuário do POSTGRES_USER já tem. Em Postgres gerenciado
    (RDS, Cloud SQL) a extensão costuma estar na lista de permitidas, mas
    pode precisar ser habilitada pelo painel antes do migrate.
    """

    dependencies = [
        ('neologismo', '0007_backfill_slug'),
    ]

    operations = [
        UnaccentExtension(),
    ]
