import uuid
from django.db import models
from django.core.files.base import ContentFile
from django.utils.text import slugify
from sites.models import Site


class Product(models.Model):
    STATUS_CHOICES = [
        (1, 'Aguardando Sincronização'),
        (2, 'Aprovado'),
        (0, 'Produto Removido'),
    ]
    
    name = models.CharField(max_length=300)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    original_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    url = models.URLField()
    sku_code = models.CharField(max_length=100, blank=True, null=True)
    
    # Campo para múltiplas imagens
    main_image = models.ImageField(upload_to='products/images/', null=True, blank=True)
    
    availability = models.CharField(max_length=100, blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    review_count = models.IntegerField(null=True, blank=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE)
    search_query = models.CharField(max_length=200, db_index=True)
    scraped_data = models.JSONField(default=dict, blank=True, null=True)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['url', 'site']
        indexes = [
            models.Index(fields=['search_query', 'created_at']),
            models.Index(fields=['site', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_safe_filename(self, original_url: str) -> str:
        """Gera um nome de arquivo seguro baseado no nome do produto"""
        name_slug = slugify(self.name)[:50]  # Limita o tamanho
        unique_id = str(uuid.uuid4())[:8]
        extension = original_url.split('.')[-1].lower()
        
        # Garantir que a extensão seja válida
        valid_extensions = ['jpg', 'jpeg', 'png', 'webp', 'gif']
        if extension not in valid_extensions:
            extension = 'jpg'
            
        return f"{name_slug}_{unique_id}.{extension}"

class ProductImage(models.Model):
    """Modelo para armazenar múltiplas imagens de um produto"""
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/')
    is_main = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    original_url = models.URLField(blank=True, null=True)  # Para referência
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['product', 'is_main']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - Imagem {self.id}"
