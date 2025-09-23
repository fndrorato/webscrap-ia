from django.contrib import admin
from sites.models import Site


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'url', 'active', 'created_at', 'updated_at')
    list_filter = ('name', 'active')
    search_fields = ('name', 'url')
    ordering = ('-created_at',)
