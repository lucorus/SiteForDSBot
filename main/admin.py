from django.contrib import admin
from . import models


class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['pk', 'username', 'email', 'slug', 'token', 'discord_server_id', 'is_authorized', 'is_banned']
    #fields = ['username', 'email', 'slug', 'token', 'is_banned']
    search_fields = ['username', 'slug', 'email', 'discord_server_id']
    prepopulated_fields = {'slug': ('username',)}


admin.site.register(models.CustomUser, CustomUserAdmin)
