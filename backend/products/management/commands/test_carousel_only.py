# products/management/commands/test_carousel_only.py

import time
from datetime import datetime
import requests
from io import BytesIO
from PIL import Image

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from sites.models import Site
from products.models import Product, ProductImage


class Command(BaseCommand):
    help = 'Extrai imagens do carrossel Nissei e salva no banco'

    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, default='https://nissei.com/py/apple-iphone-14-a2884')
        parser.add_argument('--max-images', type=int, default=3)
        parser.add_argument('--cleanup', action='store_true')

    def log(self, message, style=None):
        """Log com timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        if style:
            self.stdout.write(f'[{timestamp}] {style(message)}')
        else:
            self.stdout.write(f'[{timestamp}] {message}')

    def handle(self, *args, **options):
        start_time = time.time()
        
        url = options['url']
        max_images = options['max_images']
        cleanup = options['cleanup']
        
        self.log('🎠 EXTRAÇÃO DE IMAGENS DO CARROSSEL NISSEI', self.style.SUCCESS)
        self.log(f'URL: {url}')
        self.log(f'Máximo: {max_images} imagens')
        self.log('=' * 70)
        
        # Extrair imagens
        image_urls = self.extract_carousel_images(url, max_images)
        
        if not image_urls:
            self.log('❌ Nenhuma imagem extraída', self.style.ERROR)
            return
        
        self.log(f'✅ {len(image_urls)} imagens únicas extraídas')
        
        # Salvar no banco
        product_id = self.save_images_to_product(url, image_urls)
        
        if product_id:
            self.verify_saved_images(product_id)
            if cleanup:
                self.cleanup_product(product_id)
            
            elapsed = time.time() - start_time
            self.log(f'🎉 CONCLUÍDO! Tempo total: {elapsed:.2f}s', self.style.SUCCESS)
        else:
            self.log('❌ FALHA', self.style.ERROR)

    def extract_carousel_images(self, url: str, max_images: int) -> list:
        """Extrai URLs das imagens grandes do carrossel"""
        
        self.log('🔍 Extraindo imagens do carrossel...')
        step_start = time.time()
        
        driver = None
        try:
            # Configurar Chrome
            self.log('⚙️  Configurando Chrome headless...')
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            
            driver = webdriver.Chrome(options=options)
            self.log(f'✅ Chrome iniciado ({time.time() - step_start:.2f}s)')
            
            # Acessar página
            page_start = time.time()
            self.log('🌐 Acessando página...')
            driver.get(url)
            self.log(f'✅ Página carregada ({time.time() - page_start:.2f}s)')
            
            # Aguardar carrossel
            wait_start = time.time()
            self.log('⏳ Aguardando carrossel...')
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'fotorama__stage'))
            )
            time.sleep(3)  # Aguardar animações
            self.log(f'✅ Carrossel detectado ({time.time() - wait_start:.2f}s)')
            
            # Encontrar miniaturas
            thumbnails = driver.find_elements(By.CSS_SELECTOR, '.fotorama__nav__frame')
            total = len(thumbnails)
            self.log(f'📸 {total} miniaturas encontradas')
            
            if total == 0:
                return []
            
            # Processar miniaturas
            image_urls = []
            seen_urls = set()
            
            # Limitar ao máximo
            to_process = min(total, max_images)
            self.log(f'🔄 Processando {to_process} miniaturas...')
            
            for i in range(to_process):
                click_start = time.time()
                
                try:
                    # Re-encontrar a miniatura (evita stale element)
                    thumbnails = driver.find_elements(By.CSS_SELECTOR, '.fotorama__nav__frame')
                    if i >= len(thumbnails):
                        self.log(f'  [{i+1}/{to_process}] ❌ Miniatura não encontrada')
                        continue
                    
                    thumb = thumbnails[i]
                    
                    self.log(f'  [{i+1}/{to_process}] Clicando na miniatura...')
                    
                    # Capturar URL ANTES do clique (para comparar)
                    try:
                        before_img = driver.find_element(By.CSS_SELECTOR, '.fotorama__stage__frame.fotorama__active img')
                        url_before = before_img.get_attribute('src')
                    except:
                        url_before = None
                    
                    # Scroll até a miniatura
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", thumb)
                    time.sleep(0.3)
                    
                    # Clicar na miniatura
                    driver.execute_script("arguments[0].click();", thumb)
                    
                    # AGUARDAR A IMAGEM TROCAR
                    self.log(f'     ⏳ Aguardando imagem carregar...')
                    max_wait = 5
                    wait_interval = 0.2
                    attempts = 0
                    current_url = url_before
                    
                    while attempts < (max_wait / wait_interval):
                        time.sleep(wait_interval)
                        try:
                            current_img = driver.find_element(By.CSS_SELECTOR, '.fotorama__stage__frame.fotorama__active img')
                            current_url = current_img.get_attribute('src')
                            
                            # Se a URL mudou, sucesso!
                            if current_url != url_before and current_url:
                                break
                        except:
                            pass
                        attempts += 1
                    
                    # Capturar a imagem
                    img_url = None
                    
                    # Método 1: Tentar pegar do stage ativo
                    try:
                        img_element = driver.find_element(By.CSS_SELECTOR, '.fotorama__stage__frame.fotorama__active img')
                        img_url = img_element.get_attribute('src')
                    except:
                        pass
                    
                    # Método 2: Tentar pegar data-full da miniatura clicada
                    if not img_url or img_url == url_before:
                        try:
                            img_thumb = thumb.find_element(By.TAG_NAME, 'img')
                            img_url = img_thumb.get_attribute('data-full') or img_thumb.get_attribute('src')
                        except:
                            pass
                    
                    if img_url and 'data:image' not in img_url and len(img_url) > 30:
                        # Limpar URL do cache para pegar imagem original
                        clean_url = self.clean_image_url(img_url)
                        
                        if clean_url not in seen_urls:
                            image_urls.append(clean_url)
                            seen_urls.add(clean_url)
                            elapsed = time.time() - click_start
                            self.log(f'     ✅ Nova imagem ({elapsed:.2f}s): {clean_url[:70]}...')
                        else:
                            self.log(f'     ⚠️ Duplicada (já capturada)')
                    else:
                        self.log(f'     ❌ URL inválida ou vazia')
                
                except Exception as e:
                    self.log(f'     ❌ Erro: {str(e)[:80]}')
                    import traceback
                    traceback.print_exc()
            
            total_time = time.time() - step_start
            self.log(f'✅ Extração concluída em {total_time:.2f}s')
            return image_urls
        
        except Exception as e:
            self.log(f'❌ Erro na extração: {e}', self.style.ERROR)
            import traceback
            traceback.print_exc()
            return []
        
        finally:
            if driver:
                driver.quit()
                self.log('🔌 Chrome fechado')

    def clean_image_url(self, url: str) -> str:
        """Remove cache da URL para pegar imagem original"""
        if '/cache/' in url:
            parts = url.split('/cache/')
            if len(parts) > 1:
                # Pegar tudo depois do hash do cache
                after_cache = parts[1].split('/', 1)
                if len(after_cache) > 1:
                    return parts[0] + '/' + after_cache[1]
        return url

    def save_images_to_product(self, url: str, image_urls: list) -> int:
        """Salva imagens no banco"""
        
        self.log(f'💾 Salvando {len(image_urls)} imagens...')
        save_start = time.time()
        
        try:
            # Criar/buscar site
            site, _ = Site.objects.get_or_create(
                url='https://nissei.com',
                defaults={'name': 'Casa Nissei Paraguay'}
            )
            
            # Limpar produto anterior
            Product.objects.filter(url=url, site=site).delete()
            
            # Criar produto
            product = Product.objects.create(
                name=f"Teste Carrossel - {len(image_urls)} imgs",
                url=url,
                site=site,
                description="Produto de teste",
                price=0,
                status=1
            )
            
            self.log(f'✅ Produto {product.id} criado')
            
            # Salvar imagens
            saved = 0
            for i, img_url in enumerate(image_urls):
                img_start = time.time()
                try:
                    self.log(f'  [{i+1}/{len(image_urls)}] Baixando: {img_url[:60]}...')
                    
                    # Baixar
                    download_start = time.time()
                    r = requests.get(img_url, timeout=30, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                    })
                    r.raise_for_status()
                    download_time = time.time() - download_start
                    self.log(f'     📥 Baixada em {download_time:.2f}s ({len(r.content):,} bytes)')
                    
                    # Otimizar
                    process_start = time.time()
                    content = self.optimize_image(r.content)
                    if not content:
                        self.log('     ❌ Falha ao processar')
                        continue
                    process_time = time.time() - process_start
                    self.log(f'     🔧 Processada em {process_time:.2f}s ({len(content):,} bytes)')
                    
                    # Salvar
                    db_start = time.time()
                    filename = f"nissei_{product.id}_{i+1}.jpg"
                    img_file = ContentFile(content, name=filename)
                    
                    ProductImage.objects.create(
                        product=product,
                        image=img_file,
                        is_main=(i == 0),
                        order=i,
                        original_url=img_url
                    )
                    
                    if i == 0:
                        product.main_image = img_file
                        product.save()
                    
                    db_time = time.time() - db_start
                    total_img_time = time.time() - img_start
                    
                    saved += 1
                    self.log(f'     ✅ Salva no DB em {db_time:.2f}s (total: {total_img_time:.2f}s)')
                
                except Exception as e:
                    self.log(f'     ❌ Erro: {str(e)[:80]}')
            
            total_save_time = time.time() - save_start
            self.log(f'✅ {saved}/{len(image_urls)} salvas em {total_save_time:.2f}s')
            return product.id
        
        except Exception as e:
            self.log(f'❌ Erro ao salvar: {e}', self.style.ERROR)
            import traceback
            traceback.print_exc()
            return None

    def optimize_image(self, content: bytes) -> bytes:
        """Otimiza imagem"""
        try:
            if not content or len(content) < 1000:
                return None
            
            img = Image.open(BytesIO(content))
            
            # Converter para RGB
            if img.mode not in ('RGB', 'L'):
                if img.mode in ('RGBA', 'LA', 'P'):
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    bg.paste(img, mask=img.split()[-1] if len(img.split()) > 3 else None)
                    img = bg
                else:
                    img = img.convert('RGB')
            
            # Redimensionar
            if img.width > 1500 or img.height > 1500:
                img.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
            
            # Salvar
            output = BytesIO()
            img.save(output, format='JPEG', quality=90, optimize=True)
            return output.getvalue()
        except:
            return None

    def verify_saved_images(self, product_id: int):
        """Verifica imagens salvas"""
        self.log('🔍 Verificação:')
        
        try:
            product = Product.objects.get(id=product_id)
            images = product.images.all().order_by('order')
            
            self.log(f'📦 {product.name}')
            self.log(f'🖼️  {images.count()} imagens salvas')
            
            total = 0
            for img in images:
                if img.image:
                    size = img.image.size
                    total += size
                    main = " 🌟" if img.is_main else ""
                    self.log(f'   {img.order + 1}. ✅ {img.image.name} ({size:,} bytes){main}')
                    if img.original_url:
                        self.log(f'      URL: {img.original_url[:80]}...')
            
            self.log(f'📊 Total: {total:,} bytes ({total/1024/1024:.2f} MB)')
        except Exception as e:
            self.log(f'❌ Erro na verificação: {e}')

    def cleanup_product(self, product_id: int):
        """Remove produto"""
        self.log('🧹 Removendo produto de teste...')
        try:
            p = Product.objects.get(id=product_id)
            count = p.images.count()
            p.images.all().delete()
            p.delete()
            self.log(f'✅ Removido: 1 produto + {count} imagens')
        except Exception as e:
            self.log(f'❌ Erro na limpeza: {e}')