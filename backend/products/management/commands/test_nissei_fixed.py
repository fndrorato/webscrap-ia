from django.core.management.base import BaseCommand
from products.models import Site
from products.services.nissei_scraper_fixed import NisseiScraper


class Command(BaseCommand):
    help = 'Testa a versão corrigida do scraper do Nissei'

    def add_arguments(self, parser):
        parser.add_argument('--query', type=str, default='smartphone', help='Termo de busca')
        parser.add_argument('--max-results', type=int, default=8, help='Máximo de resultados')

    def handle(self, *args, **options):
        query = options['query']
        max_results = options['max_results']
        
        self.stdout.write(f"🧪 TESTE DO NISSEI SCRAPER - VERSÃO CORRIGIDA")
        self.stdout.write("=" * 50)
        
        try:
            # Buscar ou criar site
            site, created = Site.objects.get_or_create(
                url="https://nissei.com",
                defaults={
                    'name': 'Casa Nissei Paraguay',
                    'description': 'Loja de eletrônicos do Paraguai',
                    'active': True
                }
            )
            
            if created:
                self.stdout.write("✅ Site Nissei criado")
            
            # Inicializar scraper
            scraper = NisseiScraper(site)
            
            # Executar scraping
            self.stdout.write(f"🔍 Buscando por: '{query}'")
            products = scraper.scrape_products(query, max_results)
            
            # Mostrar resultados
            if products:
                self.stdout.write(f"\n🎉 RESULTADOS ({len(products)} produtos):")
                self.stdout.write("-" * 40)
                
                for i, product in enumerate(products, 1):
                    self.stdout.write(f"\n{i}. {product['name']}")
                    
                    if product.get('price'):
                        price_display = f"Gs. {product['price']:,.0f}"
                        if product.get('original_price'):
                            discount = ((product['original_price'] - product['price']) / product['original_price'] * 100)
                            price_display += f" (era: Gs. {product['original_price']:,.0f} - {discount:.0f}% OFF)"
                        self.stdout.write(f"   💰 {price_display}")
                    
                    if product.get('brand'):
                        self.stdout.write(f"   🏷️  {product['brand']}")
                    
                    self.stdout.write(f"   🌐 {product['url']}")
                    self.stdout.write(f"   📦 {product['availability']}")
            
            else:
                self.stdout.write("❌ Nenhum produto encontrado")
                
        except Exception as e:
            self.stdout.write(f"❌ ERRO: {str(e)}")
            import traceback
            self.stdout.write(traceback.format_exc())
