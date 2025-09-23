from django.core.management.base import BaseCommand
from products.models import Site, Configuration
from products.services.nissei_scraper import NisseiSpecializedScraper

class Command(BaseCommand):
    help = 'Testa o scraping específico do Nissei.com'

    def add_arguments(self, parser):
        parser.add_argument('--query', type=str, default='smartphone', help='Termo de busca')
        parser.add_argument('--max-results', type=int, default=10, help='Máximo de resultados')

    def handle(self, *args, **options):
        query = options['query']
        max_results = options['max_results']
        
        try:
            # Buscar ou criar configuração para Nissei
            config, created = Configuration.objects.get_or_create(
                name="Nissei Paraguai Scraper",
                defaults={
                    "description": "Configuração específica para nissei.com",
                    "model_integration": "gpt-4o-mini",
                    "token": "test_key",
                    "parameters": {"temperature": 0.1}
                }
            )
            
            # Buscar ou criar site Nissei
            site, created = Site.objects.get_or_create(
                url="https://nissei.com",
                defaults={
                    "name": "Casa Nissei Paraguay",
                    "description": "Loja de eletrônicos do Paraguai",
                    "configuration": config
                }
            )
            
            self.stdout.write(f"🔍 Testando busca por '{query}' no Nissei.com...")
            
            # Criar scraper especializado
            scraper = NisseiSpecializedScraper(site)
            
            # Realizar busca
            products = scraper.scrape_products(query, max_results)
            
            if products:
                self.stdout.write(f"✅ Encontrados {len(products)} produtos:")
                for i, product in enumerate(products[:5], 1):
                    self.stdout.write(f"{i}. {product['name']}")
                    self.stdout.write(f"   Preço: {product['currency']} {product['price']}")
                    if product.get('original_price'):
                        self.stdout.write(f"   Preço original: {product['currency']} {product['original_price']}")
                    self.stdout.write(f"   URL: {product['url']}")
                    if product.get('brand'):
                        self.stdout.write(f"   Marca: {product['brand']}")
                    self.stdout.write(f"   Disponibilidade: {product['availability']}")
                    self.stdout.write("")
            else:
                self.stdout.write("❌ Nenhum produto encontrado")
                
        except Exception as e:
            self.stdout.write(f"❌ Erro: {str(e)}")
