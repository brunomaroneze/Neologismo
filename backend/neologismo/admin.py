from django.contrib import admin, messages
from django.utils import timezone

from .models import Contexto, Neologismo


class ContextoInline(admin.TabularInline):
    model = Contexto
    extra = 1


@admin.register(Neologismo)
class NeologismoAdmin(admin.ModelAdmin):
    list_display = (
        'titulo', 'classe_gramatical', 'status',
        'autor', 'total_likes', 'data_criacao',
    )
    list_filter = ('status', 'classe_gramatical', 'data_criacao')
    search_fields = ('titulo', 'definicao', 'autor__username')
    readonly_fields = (
        'data_criacao', 'data_atualizacao', 'moderado_em',
        'moderado_por', 'reativado_em', 'slug',
    )
    autocomplete_fields = ('autor',)
    filter_horizontal = ('likes', 'deslikes')
    date_hierarchy = 'data_criacao'
    inlines = [ContextoInline]
    actions = ['aprovar_selecionados', 'rejeitar_selecionados']

    def get_queryset(self, request):
        # Evita uma query por linha para montar a coluna de autor.
        return super().get_queryset(request).select_related('autor')

    @admin.display(description='Curtidas')
    def total_likes(self, obj):
        return obj.likes.count()

    @admin.action(description='Aprovar neologismos selecionados')
    def aprovar_selecionados(self, request, queryset):
        atualizados = queryset.update(
            status=Neologismo.APROVADO,
            motivo_rejeicao=None,
            moderado_em=timezone.now(),
            moderado_por=request.user,
        )
        self.message_user(
            request, f'{atualizados} verbete(s) aprovado(s).', messages.SUCCESS
        )

    @admin.action(description='Rejeitar neologismos selecionados')
    def rejeitar_selecionados(self, request, queryset):
        atualizados = queryset.update(
            status=Neologismo.REJEITADO,
            moderado_em=timezone.now(),
            moderado_por=request.user,
        )
        self.message_user(
            request,
            f'{atualizados} verbete(s) rejeitado(s). Edite cada um para '
            f'registrar o motivo.',
            messages.WARNING,
        )


@admin.register(Contexto)
class ContextoAdmin(admin.ModelAdmin):
    list_display = ('neologismo', 'fonte', 'data_criacao')
    search_fields = ('citacao', 'fonte', 'neologismo__titulo')
    list_select_related = ('neologismo',)
