from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_admin', 'is_staff', 'date_joined')
    list_filter = ('is_admin', 'is_staff', 'is_superuser', 'is_active')
    # Necessário para o autocomplete_fields de NeologismoAdmin.autor.
    search_fields = ('username', 'email')
    ordering = ('-date_joined',)

    # Acrescenta is_admin aos fieldsets herdados do UserAdmin em vez de
    # redeclarar tudo, para não perder campos em upgrades do Django.
    fieldsets = UserAdmin.fieldsets + (
        ('Neoscópio', {'fields': ('is_admin',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Neoscópio', {'fields': ('email', 'is_admin')}),
    )
