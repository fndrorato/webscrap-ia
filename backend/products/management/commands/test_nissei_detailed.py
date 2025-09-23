from django.core.management.base import BaseCommand
from products.models import Site
from products.services.nissei_detailed_scraper import NisseiDetailedScraper

class Command(BaseCommand):
    help = 'Testa scraping com limite personalizado de imagens'

    def add_arguments(self, parser):
        parser.add_argument('--query', type=str, default='iphone', help='Termo de busca')
        parser.add_argument('--max-results', type=int, default=2, help='Máximo de produtos')
        parser.add_argument('--max-images', type=int, default=3, help='Máximo de imagens por produto')  # ✅ NOVO

    def handle(self, *args, **options):
        query = options['query']
        max_results = options['max_results']
        max_images = options['max_images']  # ✅ NOVO
        
        self.stdout.write(f"🚀 TESTE COM LIMITE DE {max_images} IMAGENS")
        self.stdout.write("=" * 50)
        
        try:
            # Buscar/criar site
            site, created = Site.objects.get_or_create(
                url="https://nissei.com",
                defaults={
                    'name': 'Casa Nissei Paraguay',
                    'description': 'Loja de eletrônicos do Paraguai'
                }
            )
            
            # Scraper com limite personalizado
            scraper = NisseiDetailedScraper(site)
            scraper.max_images_per_product = max_images  # ✅ APLICAR LIMITE PERSONALIZADO
            
            # Executar scraping
            products = scraper.scrape_products_detailed(query, max_results)
            
            # Resumo final
            self.stdout.write(f"\n🎯 RESUMO FINAL:")
            self.stdout.write(f"Query: {query}")
            self.stdout.write(f"Limite de imagens: {max_images}")
            self.stdout.write(f"Produtos processados: {len(products)}")
            
            for i, product in enumerate(products, 1):
                image_count = len(product.get('processed_images', []))
                self.stdout.write(f"\n{i}. {product['name'][:60]}")
                self.stdout.write(f"   📸 Imagens baixadas: {image_count}/{max_images}")
                
                # Mostrar URLs das imagens
                if 'processed_images' in product:
                    for j, img in enumerate(product['processed_images'], 1):
                        self.stdout.write(f"     {j}. {img['filename']} ({img['width']}x{img['height']})")
            
        except Exception as e:
            self.stdout.write(f"❌ ERRO: {str(e)}")
