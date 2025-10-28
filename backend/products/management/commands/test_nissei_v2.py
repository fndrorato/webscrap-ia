# products/management/commands/test_nissei_v2.py

from django.core.management.base import BaseCommand
from sites.models import Site
from configurations.models import Configuration
from products.models import Product


class Command(BaseCommand):
    help = 'Testa o NisseiExtractorV2 (versão ultra otimizada)'

    def add_arguments(self, parser):
        parser.add_argument('--query', type=str, default='iphone', help='Termo de busca')
        parser.add_argument('--max-results', type=int, default=10, help='Max produtos listagem')
        parser.add_argument('--max-detailed', type=int, default=3, help='Max produtos detalhes')
        parser.add_argument('--use-ai', action='store_true', help='Usar filtro IA')
        parser.add_argument('--cleanup', action='store_true', help='Remover produtos após teste')

    def handle(self, *args, **options):
        query = options['query']
        max_results = options['max_results']
        max_detailed = options['max_detailed']
        use_ai = options['use_ai']
        cleanup = options['cleanup']

        print("\n" + "=" * 70)
        print("🚀 TESTE DO NISSEI EXTRACTOR V2")
        print("=" * 70)

        # 1. Setup Site
        site, created = Site.objects.get_or_create(
            url='https://nissei.com',
            defaults={'name': 'Casa Nissei Paraguay'}
        )
        
        if created:
            print(f"✅ Site criado: {site.name}")
        else:
            print(f"✅ Site encontrado: {site.name} (ID: {site.id})")

        # 2. Setup Configuration
        if use_ai:
            print("\n⚠️  MODO IA ATIVADO")
            print("Configure seu token de IA antes de usar:")
            print("1. Crie uma Configuration no Django Admin")
            print("2. Configure model_integration e token")
            
            config = Configuration.objects.filter(
                model_integration__isnull=False,
                token__isnull=False
            ).first()
            
            if not config:
                print("\n❌ Nenhuma configuração de IA encontrada!")
                print("Criando configuração de teste (sem IA)...")
                config, _ = Configuration.objects.get_or_create(
                    name='Test Config (No AI)',
                    defaults={
                        'model_integration': None,
                        'token': None
                    }
                )
        else:
            config, _ = Configuration.objects.get_or_create(
                name='Test Config (No AI)',
                defaults={
                    'model_integration': None,
                    'token': None
                }
            )

        print(f"✅ Configuração: {config.name}")

        # 3. Importar e inicializar extrator
        try:
            from extractors.nissei_extractor_v2 import NisseiExtractorV2
            
            print("\n" + "=" * 70)
            print("🔧 Inicializando extrator...")
            print("=" * 70)
            
            extractor = NisseiExtractorV2(site, config)
            
            # 4. Executar scraping
            print("\n")
            products = extractor.scrape_products_intelligent(
                query=query,
                max_results=max_results,
                max_detailed=max_detailed
            )

            # 5. Mostrar resumo detalhado
            print("\n" + "=" * 70)
            print("📊 RESUMO DETALHADO")
            print("=" * 70)
            
            if products:
                print(f"\n✅ {len(products)} produtos processados:\n")
                
                for i, product in enumerate(products, 1):
                    print(f"{i}. {product.get('name', 'Sem nome')[:70]}")
                    print(f"   URL: {product.get('url', '')[:80]}")
                    print(f"   Preço: {product.get('price', 0)} {extractor.currency}")
                    if product.get('old_price', 0) > 0:
                        print(f"   Preço antigo: {product.get('old_price', 0)} {extractor.currency}")
                    print(f"   SKU: {product.get('sku', 'N/A')}")
                    print(f"   Marca: {product.get('brand', 'N/A')}")
                    print(f"   Imagens: {len(product.get('images', []))}")
                    
                    specs = product.get('specifications', {})
                    if specs:
                        print(f"   Especificações: {len(specs)} items")
                    
                    print()
                
                # 6. Verificar no banco
                print("\n" + "=" * 70)
                print("💾 PRODUTOS NO BANCO DE DADOS")
                print("=" * 70)
                
                saved_products = Product.objects.filter(site=site, search_query=query)
                print(f"\n✅ {saved_products.count()} produtos salvos com query '{query}':\n")
                
                for product in saved_products:
                    img_count = product.images.count()
                    print(f"• ID {product.id}: {product.name[:60]}")
                    print(f"  Preço: {product.price} | Imagens: {img_count}")
                    if product.main_image:
                        print(f"  Imagem principal: ✅")
                    print()
                
                # 7. Cleanup (opcional)
                if cleanup:
                    print("\n" + "=" * 70)
                    print("🧹 LIMPEZA")
                    print("=" * 70)
                    
                    count = saved_products.count()
                    # Deletar imagens primeiro
                    for product in saved_products:
                        product.images.all().delete()
                    # Deletar produtos
                    saved_products.delete()
                    
                    print(f"✅ {count} produtos removidos do banco")
            
            else:
                print("❌ Nenhum produto foi processado")
            
            # 8. Cleanup do extrator
            extractor.close()
            
            print("\n" + "=" * 70)
            print("✅ TESTE CONCLUÍDO!")
            print("=" * 70)

        except ImportError:
            print("\n" + "=" * 70)
            print("❌ ERRO DE IMPORTAÇÃO")
            print("=" * 70)
            print("\nNão foi possível importar NisseiExtractorV2")
            print("\nVerifique se o arquivo está em:")
            print("  backend/extractors/nissei_extractor_v2.py")
            print("\nCertifique-se de que a pasta extractors tem __init__.py")
            
        except Exception as e:
            print("\n" + "=" * 70)
            print("❌ ERRO NO TESTE")
            print("=" * 70)
            print(f"\nErro: {e}\n")
            import traceback
            traceback.print_exc()