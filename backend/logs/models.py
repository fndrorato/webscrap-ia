from django.db import models
from products.models import Product


class LogEntry(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    status = models.CharField(max_length=50)
    related_product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True, related_name='logs')

    def __str__(self):
        return f"[{self.timestamp}] {self.related_product}: {self.message[:50]}..."