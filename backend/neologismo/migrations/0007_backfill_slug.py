from django.db import migrations
from django.utils.text import slugify


def preencher_slugs(apps, schema_editor):
    """Gera o slug dos verbetes que já existiam antes do campo."""
    Neologismo = apps.get_model('neologismo', 'Neologismo')
    pendentes = Neologismo.objects.filter(slug='').only('id', 'titulo')
    atualizar = []
    for neologismo in pendentes.iterator():
        neologismo.slug = slugify(neologismo.titulo)[:70]
        atualizar.append(neologismo)
    if atualizar:
        Neologismo.objects.bulk_update(atualizar, ['slug'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('neologismo', '0006_alter_contexto_options_alter_neologismo_options_and_more'),
    ]

    operations = [
        # O slug é derivado do título, então a reversão não precisa fazer nada.
        migrations.RunPython(preencher_slugs, migrations.RunPython.noop),
    ]
