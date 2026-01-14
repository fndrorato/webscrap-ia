from rest_framework import serializers
from configurations.models import Configuration
from sites.models import Site
from products.models import Product, ProductImage

class ConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Configuration
        fields = '__all__'

class SiteSerializer(serializers.ModelSerializer):
    configuration_name = serializers.CharField(source='configuration.name', read_only=True)
    
    class Meta:
        model = Site
        fields = '__all__'

class IntelligentSearchSerializer(serializers.Serializer):
    query = serializers.CharField(max_length=200, help_text="Termo de busca")
    site_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="IDs dos sites para buscar (opcional)"
    )
    max_results = serializers.IntegerField(default=10, min_value=1, max_value=50)
    use_ai_analysis = serializers.BooleanField(default=True, help_text="Usar análise inteligente com Agno")

class SiteAnalysisSerializer(serializers.Serializer):
    site_id = serializers.IntegerField(help_text="ID do site para analisar")

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    def get_image_url(self, obj):
        if obj.image:
            # request = self.context.get('request')
            # if request:
            #     return request.build_absolute_uri(obj.image.url)
            # ✅ RETORNA URL RELATIVA (sem build_absolute_uri)
            return obj.image.url  # Retorna /media/products/gallery/...
        return None
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 'is_main', 'alt_text', 'order', 'original_url']

class ProductSerializer(serializers.ModelSerializer):
    site_name = serializers.CharField(source='site.name', read_only=True)
    site_url = serializers.CharField(source='site.url', read_only=True)
    main_image_url = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    def get_main_image_url(self, obj):
        if obj.main_image:
            # request = self.context.get('request')
            # if request:
            #     return request.build_absolute_uri(obj.main_image.url)
            # return obj.main_image.url
            # ✅ RETORNA URL RELATIVA (sem build_absolute_uri)
            return obj.main_image.url  # Retorna /media/products/main_...            
        return None
    
    class Meta:
        model = Product
        fields = '__all__'
