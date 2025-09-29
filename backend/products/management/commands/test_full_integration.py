# Caminho: products/management/commands/test_full_integration.py

import time
from typing import List, Optional
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand
from django.conf import settings

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from sites.models import Site
from configurations.models import Configuration
from products.models import Product, ProductImage

# AJUSTAR ESTE IMPORT
try:
    from products.services.ai_nissei_scraper import AISeleniumNisseiScraper
except ImportError:
    try:
        from scrapers.ai_selenium_nissei_scraper import AISeleniumNisseiScraper
    except ImportError:
        AISeleniumNisseiScraper = None


class Command(BaseCommand):
    help = 'Teste COMPLETO: extração + download + salvamento de imagens'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            default='https://nissei.com/py/apple-iphone-16-pro-a3083-1',
            help='URL do produto para testar'
        )
        parser.add_argument(
            '--site-name',
            type=str,
            help='Nome do Site para usar'
        )
        parser.add_argument(
            '--create-site',
            action='store_true',
            help='Criar Site se não existir'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Remover produto teste após execução'
        )

    def handle(self, *args, **options):
        test_url = options['url']
        site_name = options['site_name']
        create_site = options['create_site']
        cleanup = options['cleanup']
        
        self.stdout.write(
            self.style.SUCCESS('🔥 TESTE COMPLETO: Extração + Download + Salvamento')
        )
        self.stdout.write(f'URL: {test_url}')
        self.stdout.write('=' * 70)

        if AISeleniumNisseiScraper is None:
            self.stdout.write(self.style.ERROR('❌ Classe AISeleniumNisseiScraper não encontrada'))
            return

        try:
            # PASSO 1: Configurar Site e Configuration
            site, config = self.setup_test_environment(site_name, create_site)
            if not site or not config:
                return

            # PASSO 2: Executar teste completo
            success, product_id = self.run_full_test(site, config, test_url)
            
            # PASSO 3: Verificar resultado
            if success and product_id:
                self.verify_saved_data(product_id)
                
                if cleanup:
                    self.cleanup_test_data(product_id)
                
                self.stdout.write(
                    self.style.SUCCESS('\n🎉 TESTE COMPLETO BEM-SUCEDIDO!')
                )
                self.stdout.write('✅ Extração funcionou')
                self.stdout.write('✅ Download funcionou') 
                self.stdout.write('✅ Salvamento funcionou')
                
            else:
                self.stdout.write(
                    self.style.ERROR('\n❌ TESTE COMPLETO FALHOU')
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())

    def setup_test_environment(self, site_name: str, create_site: bool):
        """Configura ambiente de teste"""
        
        # Site
        sites = Site.objects.all()
        if site_name:
            try:
                site = sites.get(name__icontains=site_name)
            except Site.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Site "{site_name}" não encontrado'))
                return None, None
        elif sites.exists():
            site = sites.first()
        elif create_site:
            site = Site.objects.create(
                name="Teste Nissei",
                url="https://nissei.com",
                description="Site de teste"
            )
        else:
            self.stdout.write(self.style.ERROR('Nenhum Site disponível'))
            return None, None
        
        # Configuration
        configs = Configuration.objects.all()
        if configs.exists():
            config = configs.first()
        else:
            config = Configuration.objects.create(
                name="Teste Config",
                model_integration="teste",
                token="teste"
            )
        
        self.stdout.write(f'✅ Site: {site.name}')
        self.stdout.write(f'✅ Config: {config.name}')
        
        return site, config

    def run_full_test(self, site: Site, config: Configuration, test_url: str):
        """Executa teste completo incluindo salvamento"""
        
        self.stdout.write('\n🚀 Iniciando teste completo...')
        
        # Criar scraper
        scraper = AISeleniumNisseiScraper(site, config)
        
        try:
            # TESTE 1: Extração completa de produto
            self.stdout.write('\n📋 FASE 1: Extração completa de produto')
            
            # Simular produto básico
            basic_product = {
                'name': 'iPhone 16 Pro - Teste Completo',
                'url': test_url,
                'search_query': 'teste_completo'
            }
            
            # Extrair produto com detalhes
            detailed_product = scraper._extract_product_intelligent_enhanced(basic_product)
            
            if not detailed_product:
                self.stdout.write(self.style.ERROR('❌ Falha na extração do produto'))
                return False, None
            
            # Verificar se tem imagens
            image_urls = detailed_product.get('image_urls', [])
            if not image_urls:
                self.stdout.write(self.style.ERROR('❌ Nenhuma imagem extraída'))
                return False, None
            
            self.stdout.write(f'✅ Produto extraído')
            self.stdout.write(f'   Nome: {detailed_product.get("name", "")[:50]}...')
            self.stdout.write(f'   Preço: {detailed_product.get("price")}')
            self.stdout.write(f'   Imagens: {len(image_urls)}')
            self.stdout.write(f'   Método: {detailed_product.get("extraction_method")}')
            
            # TESTE 2: Download de imagens
            self.stdout.write(f'\n📥 FASE 2: Download de {len(image_urls)} imagens')
            
            download_count = scraper._download_product_images(detailed_product)
            
            if download_count == 0:
                self.stdout.write(self.style.ERROR('❌ Falha no download das imagens'))
                return False, None
            
            self.stdout.write(f'✅ {download_count} imagens baixadas e processadas')
            
            # Verificar se imagens foram processadas
            processed_images = detailed_product.get('processed_images', [])
            if not processed_images:
                self.stdout.write(self.style.ERROR('❌ Imagens não foram processadas'))
                return False, None
            
            self.stdout.write(f'✅ {len(processed_images)} imagens processadas')
            
            # TESTE 3: Salvamento no banco
            self.stdout.write('\n💾 FASE 3: Salvamento no banco de dados')
            
            saved_count = scraper._save_products_enhanced([detailed_product])
            
            if saved_count == 0:
                self.stdout.write(self.style.ERROR('❌ Falha ao salvar no banco'))
                return False, None
            
            self.stdout.write(f'✅ {saved_count} produto salvo no banco')
            
            # Encontrar produto salvo
            product = Product.objects.filter(
                url=test_url,
                site=site
            ).first()
            
            if not product:
                self.stdout.write(self.style.ERROR('❌ Produto não encontrado no banco'))
                return False, None
            
            self.stdout.write(f'✅ Produto encontrado no banco (ID: {product.id})')
            
            return True, product.id
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro no teste completo: {e}'))
            return False, None
        finally:
            scraper.close()

    def verify_saved_data(self, product_id: int):
        """Verifica dados salvos no banco"""
        
        self.stdout.write(f'\n🔍 VERIFICAÇÃO: Dados salvos no banco')
        
        try:
            # Buscar produto
            product = Product.objects.get(id=product_id)
            
            self.stdout.write(f'📦 PRODUTO:')
            self.stdout.write(f'   ID: {product.id}')
            self.stdout.write(f'   Nome: {product.name[:50]}...')
            self.stdout.write(f'   Preço: {product.price}')
            self.stdout.write(f'   SKU: {product.sku_code or "N/A"}')
            self.stdout.write(f'   Descrição: {len(product.description)} caracteres')
            
            # Buscar imagens
            images = ProductImage.objects.filter(product=product)
            
            self.stdout.write(f'\n🖼️ IMAGENS ({images.count()}).')
            
            if images.exists():
                for i, img in enumerate(images, 1):
                    try:
                        # Verificar se arquivo existe
                        file_exists = img.image and img.image.name
                        file_size = img.image.size if file_exists else 0
                        
                        self.stdout.write(f'   {i}. {"✅" if file_exists else "❌"} '
                                        f'{img.image.name if file_exists else "Sem arquivo"} '
                                        f'({file_size} bytes)')
                        
                        if img.is_main:
                            self.stdout.write(f'      🌟 Imagem principal')
                            
                    except Exception as e:
                        self.stdout.write(f'   {i}. ❌ Erro: {e}')
            else:
                self.stdout.write('   ❌ Nenhuma imagem salva')
            
            # Verificar imagem principal do produto
            if product.main_image:
                self.stdout.write(f'\n🌟 IMAGEM PRINCIPAL: {product.main_image.name}')
            else:
                self.stdout.write(f'\n⚠️ Produto sem imagem principal definida')
                
        except Product.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Produto {product_id} não encontrado'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro na verificação: {e}'))

    def cleanup_test_data(self, product_id: int):
        """Remove dados de teste"""
        
        self.stdout.write(f'\n🧹 Limpeza: Removendo dados de teste...')
        
        try:
            product = Product.objects.get(id=product_id)
            
            # Remover imagens
            images_count = ProductImage.objects.filter(product=product).count()
            ProductImage.objects.filter(product=product).delete()
            
            # Remover produto
            product.delete()
            
            self.stdout.write(f'✅ Removido: 1 produto + {images_count} imagens')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro na limpeza: {e}'))