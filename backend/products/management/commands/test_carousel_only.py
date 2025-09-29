# Caminho: products/management/commands/test_carousel_save.py

import time
import os
import requests
import base64
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.base import ContentFile
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from sites.models import Site
from configurations.models import Configuration
from products.models import Product, ProductImage

# AJUSTAR IMPORT
try:
    from products.services.ai_nissei_scraper import AISeleniumNisseiScraper
except ImportError:
    AISeleniumNisseiScraper = None


class Command(BaseCommand):
    help = 'Testa carrossel e SALVA as imagens no banco + disco'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            default='https://nissei.com/py/apple-iphone-16-pro-a3083-1',
            help='URL do produto para testar'
        )
        parser.add_argument(
            '--max-images',
            type=int,
            default=8,
            help='Máximo de imagens do carrossel para extrair'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Remover produto de teste após execução'
        )

    def handle(self, *args, **options):
        test_url = options['url']
        max_images = options['max_images']
        cleanup = options['cleanup']
        
        self.stdout.write(
            self.style.SUCCESS('🎠💾 TESTE: Carrossel + Salvamento de Imagens')
        )
        self.stdout.write(f'URL: {test_url}')
        self.stdout.write(f'Máximo imagens: {max_images}')
        self.stdout.write('=' * 60)

        if not AISeleniumNisseiScraper:
            self.stdout.write(self.style.ERROR('❌ Classe AISeleniumNisseiScraper não encontrada'))
            return

        try:
            # Configurar ambiente
            site, config = self.setup_environment()
            if not site or not config:
                return

            # Executar teste completo
            product_id = self.run_carousel_test_with_save(site, config, test_url, max_images)
            
            if product_id:
                # Verificar resultado
                self.verify_saved_carousel_images(product_id)
                
                if cleanup:
                    self.cleanup_test_product(product_id)
                
                self.stdout.write(
                    self.style.SUCCESS('\n🎉 TESTE CARROSSEL + SALVAMENTO CONCLUÍDO!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('\n❌ TESTE FALHOU')
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())

    def setup_environment(self):
        """Configura ambiente de teste"""
        
        # Site
        site = Site.objects.first()
        if not site:
            site = Site.objects.create(
                name="Teste Carrossel",
                url="https://nissei.com",
                description="Site para teste do carrossel"
            )
            self.stdout.write(f'✅ Site criado: {site.name}')
        else:
            self.stdout.write(f'✅ Site: {site.name}')
        
        # Configuration
        config = Configuration.objects.first()
        if not config:
            config = Configuration.objects.create(
                name="Teste Carrossel Config",
                model_integration="teste",
                token="teste_token"
            )
            self.stdout.write(f'✅ Config criada: {config.name}')
        else:
            self.stdout.write(f'✅ Config: {config.name}')
        
        return site, config

    def run_carousel_test_with_save(self, site: Site, config: Configuration, test_url: str, max_images: int) -> int:
        """Executa teste completo do carrossel com salvamento"""
        
        # Criar scraper
        scraper = AISeleniumNisseiScraper(site, config)
        
        # AJUSTAR max_images_per_product temporariamente
        original_max = scraper.max_images_per_product
        scraper.max_images_per_product = max_images
        
        try:
            # FASE 1: Extrair apenas imagens do carrossel
            self.stdout.write('\n🎠 FASE 1: Extração do carrossel (sem limitação)')
            
            carousel_images = self.extract_carousel_unlimited(scraper, test_url, max_images)
            
            if not carousel_images:
                self.stdout.write(self.style.ERROR('❌ Nenhuma imagem extraída do carrossel'))
                return None
            
            self.stdout.write(f'✅ {len(carousel_images)} imagens extraídas do carrossel')
            
            # FASE 2: Criar produto de teste
            self.stdout.write('\n📦 FASE 2: Criando produto de teste')
            
            product = self.create_test_product(site, test_url, carousel_images)
            if not product:
                return None
            
            self.stdout.write(f'✅ Produto criado (ID: {product.id})')
            
            # FASE 3: Baixar e salvar imagens
            self.stdout.write(f'\n📥 FASE 3: Baixando e salvando {len(carousel_images)} imagens')
            
            saved_count = self.download_and_save_carousel_images(product, carousel_images)
            
            self.stdout.write(f'✅ {saved_count} imagens salvas com sucesso')
            
            return product.id
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro no teste: {e}'))
            return None
        finally:
            # Restaurar configuração original
            scraper.max_images_per_product = original_max
            scraper.close()

    def extract_carousel_unlimited(self, scraper, url: str, max_images: int) -> list:
        """Extrai imagens do carrossel SEM limitação do max_images_per_product"""
        
        try:
            # Configurar Selenium
            scraper.setup_selenium()
            if not scraper.driver:
                self.stdout.write('❌ Selenium falhou')
                return []
            
            # Acessar página
            scraper.driver.get(url)
            WebDriverWait(scraper.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)
            
            # Extrair com método específico SEM limitação
            soup = BeautifulSoup(scraper.driver.page_source, 'html.parser')
            
            # Chamar método direto do carrossel
            all_images = []
            
            # PASSO 1: Aguardar carrossel carregar
            carousel_loaded = scraper._wait_for_carousel_loading(scraper.driver)
            if not carousel_loaded:
                self.stdout.write('⚠️ Carrossel não detectado')
                return []
            
            # PASSO 2: Capturar imagem inicial
            initial_image = scraper._get_current_carousel_image_test_version(scraper.driver)
            if initial_image:
                all_images.append(initial_image)
                self.stdout.write(f'📸 Inicial: {initial_image[:50]}...')
            
            # PASSO 3: Encontrar botões de navegação
            next_buttons = scraper._find_next_buttons_test_version(scraper.driver)
            if not next_buttons:
                self.stdout.write('⚠️ Nenhum botão de navegação encontrado')
                return all_images
            
            # PASSO 4: Navegar coletando TODAS as imagens
            self.stdout.write(f'🔄 Navegando por até {max_images} imagens...')
            
            navigation_images = self.navigate_carousel_unlimited(scraper, next_buttons[0], max_images)
            
            # Adicionar imagens únicas
            for img in navigation_images:
                if img and img not in all_images:
                    all_images.append(img)
            
            # RETORNAR TODAS (sem limitação)
            return all_images[:max_images]  # Apenas limitar pelo parâmetro do comando
            
        except Exception as e:
            self.stdout.write(f'❌ Erro na extração: {e}')
            return []

    def navigate_carousel_unlimited(self, scraper, next_button, max_images: int) -> list:
        """Navega pelo carrossel coletando todas as imagens possíveis"""
        
        navigation_images = []
        consecutive_failures = 0
        max_failures = 3
        
        for click_num in range(max_images):
            try:
                if not next_button.is_displayed() or not next_button.is_enabled():
                    self.stdout.write(f'   Botão indisponível no clique {click_num + 1}')
                    break
                
                # Capturar imagem antes
                image_before = scraper._get_current_carousel_image_test_version(scraper.driver)
                
                # Clicar
                scraper.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(1)
                
                clicked = scraper._click_button_robust_test_version(scraper.driver, next_button)
                if not clicked:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        break
                    continue
                
                # Aguardar transição
                time.sleep(2)
                
                # Capturar nova imagem
                image_after = scraper._get_current_carousel_image_test_version(scraper.driver)
                
                if image_after and image_after != image_before:
                    if image_after not in navigation_images:
                        navigation_images.append(image_after)
                        self.stdout.write(f'   ✅ Clique {click_num + 1}: nova imagem')
                        consecutive_failures = 0
                    else:
                        self.stdout.write(f'   ⚠️ Clique {click_num + 1}: imagem duplicada')
                        consecutive_failures += 1
                elif image_after == image_before:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        self.stdout.write(f'   Parou: {max_failures} cliques sem mudança')
                        break
                
            except Exception as e:
                self.stdout.write(f'   ❌ Erro no clique {click_num + 1}: {str(e)[:50]}')
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    break
        
        return navigation_images

    def create_test_product(self, site: Site, url: str, carousel_images: list) -> Product:
        """Cria produto de teste"""
        
        try:
            # Remover produto anterior se existir
            Product.objects.filter(url=url, site=site).delete()
            
            product = Product.objects.create(
                name=f"Teste Carrossel - {len(carousel_images)} imagens",
                url=url,
                site=site,
                description=f"Produto de teste com {len(carousel_images)} imagens do carrossel",
                price=1000000,  # Preço fictício
                search_query="teste_carrossel",
                status=1
            )
            
            return product
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro ao criar produto: {e}'))
            return None

    def download_and_save_carousel_images(self, product: Product, image_urls: list) -> int:
        """Baixa e salva imagens do carrossel"""
        
        saved_count = 0
        
        # Remover imagens antigas
        ProductImage.objects.filter(product=product).delete()
        
        for i, img_url in enumerate(image_urls):
            try:
                self.stdout.write(f'📥 Baixando {i+1}/{len(image_urls)}: {img_url[:50]}...')
                
                # Baixar imagem
                response = requests.get(img_url, timeout=30, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()
                
                # Processar imagem
                image_content = response.content
                processed_image = self.process_image(image_content)
                
                if not processed_image:
                    self.stdout.write(f'   ❌ Falha ao processar imagem {i+1}')
                    continue
                
                # Gerar nome do arquivo
                filename = f"carousel_test_{i+1}_{product.id}.jpg"
                
                # Criar arquivo Django
                image_file = ContentFile(processed_image['content'], name=filename)
                
                # Criar registro ProductImage
                product_image = ProductImage.objects.create(
                    product=product,
                    image=image_file,
                    is_main=(i == 0),
                    alt_text=f"Imagem {i+1} do carrossel",
                    order=i,
                    original_url=img_url
                )
                
                # Definir primeira como principal
                if i == 0:
                    product.main_image = product_image.image
                    product.save()
                
                saved_count += 1
                file_size = product_image.image.size
                self.stdout.write(f'   ✅ Salva: {filename} ({file_size} bytes)')
                
            except Exception as e:
                self.stdout.write(f'   ❌ Erro na imagem {i+1}: {str(e)[:50]}')
                continue
        
        return saved_count

    def process_image(self, image_content: bytes) -> dict:
        """Processa imagem (redimensiona e otimiza)"""
        
        try:
            # Validar conteúdo
            if not image_content or len(image_content) < 1000:
                return None
            
            # Abrir com PIL
            image_buffer = BytesIO(image_content)
            img = Image.open(image_buffer)
            img.verify()
            
            # Reabrir para processamento
            image_buffer.seek(0)
            img = Image.open(image_buffer)
            
            # Converter para RGB se necessário
            if img.mode not in ['RGB', 'L']:
                if img.mode == 'RGBA':
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1])
                    img = rgb_img
                else:
                    img = img.convert('RGB')
            
            # Redimensionar se muito grande
            max_dimension = 1200
            if img.width > max_dimension or img.height > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            # Salvar otimizado
            output_buffer = BytesIO()
            img.save(output_buffer, format='JPEG', quality=85, optimize=True)
            processed_content = output_buffer.getvalue()
            
            return {
                'content': processed_content,
                'width': img.width,
                'height': img.height,
                'format': 'JPEG'
            }
            
        except Exception as e:
            return None

    def verify_saved_carousel_images(self, product_id: int):
        """Verifica imagens salvas do carrossel"""
        
        self.stdout.write(f'\n🔍 VERIFICAÇÃO: Imagens do carrossel salvas')
        
        try:
            product = Product.objects.get(id=product_id)
            images = ProductImage.objects.filter(product=product).order_by('order')
            
            self.stdout.write(f'📦 PRODUTO: {product.name}')
            self.stdout.write(f'🖼️ IMAGENS DO CARROSSEL ({images.count()}):')
            
            total_size = 0
            for img in images:
                try:
                    file_exists = img.image and img.image.name
                    if file_exists:
                        file_size = img.image.size
                        total_size += file_size
                        status = "✅"
                        size_info = f"({file_size} bytes)"
                    else:
                        status = "❌"
                        size_info = "(arquivo não encontrado)"
                    
                    main_marker = " 🌟 PRINCIPAL" if img.is_main else ""
                    
                    self.stdout.write(
                        f'   {img.order + 1}. {status} {img.image.name if file_exists else "Sem arquivo"} '
                        f'{size_info}{main_marker}'
                    )
                    
                    # Mostrar URL original
                    if img.original_url:
                        self.stdout.write(f'      Original: {img.original_url[:60]}...')
                    
                except Exception as e:
                    self.stdout.write(f'   {img.order + 1}. ❌ Erro: {e}')
            
            self.stdout.write(f'\n📊 RESUMO:')
            self.stdout.write(f'   Total de imagens: {images.count()}')
            self.stdout.write(f'   Tamanho total: {total_size:,} bytes')
            self.stdout.write(f'   Imagem principal: {"✅" if product.main_image else "❌"}')
            
            # Verificar diretório físico
            if images.exists():
                first_image = images.first()
                if first_image.image:
                    image_dir = os.path.dirname(first_image.image.path)
                    self.stdout.write(f'   Diretório: {image_dir}')
                    
                    if os.path.exists(image_dir):
                        files_in_dir = len([f for f in os.listdir(image_dir) if f.startswith('carousel_test')])
                        self.stdout.write(f'   Arquivos no diretório: {files_in_dir}')
                    
        except Product.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Produto {product_id} não encontrado'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro na verificação: {e}'))

    def cleanup_test_product(self, product_id: int):
        """Remove produto de teste"""
        
        self.stdout.write(f'\n🧹 Removendo produto de teste...')
        
        try:
            product = Product.objects.get(id=product_id)
            
            # Contar imagens antes de remover
            images_count = ProductImage.objects.filter(product=product).count()
            
            # Remover imagens (arquivos serão deletados automaticamente)
            ProductImage.objects.filter(product=product).delete()
            
            # Remover produto
            product.delete()
            
            self.stdout.write(f'✅ Removido: 1 produto + {images_count} imagens')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro na limpeza: {e}'))