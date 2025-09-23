from django.core.management.base import BaseCommand
from products.models import Product
from products.services.image_downloader import ProductImageDownloader


class Command(BaseCommand):
    help = 'Baixa imagens faltantes para produtos existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Número máximo de produtos para processar'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        
        # Produtos sem imagem principal
        products_without_images = Product.objects.filter(
            main_image__isnull=True,
            status__in=[1, 2]  # Apenas ativos
        )[:limit]
        
        downloader = ProductImageDownloader()
        processed = 0
        
        for product in products_without_images:
            try:
                self.stdout.write(f'Processando: {product.name}')
                
                downloaded_images = downloader.download_product_images(
                    product=product,
                    max_images=5
                )
                
                if downloaded_images:
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Baixadas {len(downloaded_images)} imagens')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠️  Nenhuma imagem encontrada')
                    )
                
                processed += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erro: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'🎉 Processados {processed} produtos')
        )
