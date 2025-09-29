from django.db import models


class Configuration(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    model_integration = models.CharField(max_length=100)
    token = models.CharField(max_length=255)
    parameters = models.JSONField(default=dict, blank=True, null=True)
    max_results = models.IntegerField(default=10, null=True, blank=True)
    max_detailed = models.IntegerField(default=10, null=True, blank=True)
    max_images = models.IntegerField(default=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
        