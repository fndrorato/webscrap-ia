from django.db import models
from configurations.models import Configuration


class Site(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField(unique=True)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
class Site(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField(unique=True)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)
    
    # ADICIONE ESTA LINHA - Este é o campo que estava faltando!
    configuration = models.ForeignKey(
        Configuration, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='sites',
        help_text='Configuração de IA para scraping deste site'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name    

    def __str__(self):
        return self.name
