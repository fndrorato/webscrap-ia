import time
from datetime import datetime
import requests
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile

from sites.models import Site
from products.models import Product, ProductImage


class Command(BaseCommand):
    help = 'Extração otimizada de imagens do carrossel Nissei'

    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, default='https://nissei.com/py/apple-iphone-14-a2884')
        parser.add_argument('--max-images', type=int, default=3)
        parser.add_argument('--cleanup', action='store_true')

    def log(self, message, style=None):
        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        if style:
            self.stdout.write(f'[{ts}] {style(message)}')
        else:
            self.stdout.write(f'[{ts}] {message}')

    def handle(self, *args, **options):
        start = time.time()
        url = options['url']
        max_images = options['max_images']
        cleanup = options['cleanup']

        self.log('🎠 EXTRAÇÃO OTIMIZADA DO CARROSSEL NISSEI', self.style.SUCCESS)
        self.log(f'URL: {url}')
        self.log('=' * 70)

        # 1️⃣ Tentar extrair via requests + BeautifulSoup
        image_urls = self.extract_with_bs4(url, max_images)
        if not image_urls:
            # 2️⃣ Se não achou nada, usar Playwright como fallback
            self.log('⚠️  BS4 não encontrou imagens, tentando Playwright...')
            image_urls = self.extract_with_playwright(url, max_images)

        if not image_urls:
            self.log('❌ Nenhuma imagem encontrada', self.style.ERROR)
            return

        self.log(f'✅ {len(image_urls)} imagens encontradas')
        product_id = self.save_images_to_product(url, image_urls)

        if product_id:
            self.verify_saved_images(product_id)
            if cleanup:
                self.cleanup_product(product_id)
            self.log(f'🎉 Concluído em {time.time() - start:.2f}s', self.style.SUCCESS)
        else:
            self.log('❌ Falha ao salvar produto', self.style.ERROR)

    # ------------------------------------------------------------------
    # EXTRAÇÃO 1: Requests + BeautifulSoup (ultra rápido)
    # ------------------------------------------------------------------
    def extract_with_bs4(self, url, max_images):
        try:
            start = time.time()
            headers = {'User-Agent': 'Mozilla/5.0'}
            html = requests.get(url, headers=headers, timeout=10).text
            soup = BeautifulSoup(html, 'html.parser')

            image_urls = []
            seen = set()

            for img_tag in soup.select('.fotorama__nav__frame img, .fotorama__thumb img'):
                src = img_tag.get('data-full') or img_tag.get('src')
                if not src or 'data:image' in src:
                    continue
                src = src.split('?')[0]
                if src not in seen:
                    seen.add(src)
                    image_urls.append(src)
                if len(image_urls) >= max_images:
                    break

            self.log(f'🔍 Extraídas {len(image_urls)} via BeautifulSoup ({time.time() - start:.2f}s)')
            return image_urls
        except Exception as e:
            self.log(f'❌ Erro BS4: {e}', self.style.ERROR)
            return []

    # ------------------------------------------------------------------
    # EXTRAÇÃO 2: Fallback com Playwright (rápido, mas requer navegador)
    # ------------------------------------------------------------------
    def extract_with_playwright(self, url, max_images):
        from playwright.sync_api import sync_playwright
        import time

        try:
            start = time.time()
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=20000)
                page.wait_for_selector('.fotorama__nav__frame img', timeout=10000)

                thumbs = page.query_selector_all('.fotorama__nav__frame img')
                image_urls = []
                seen = set()

                total = min(len(thumbs), max_images)
                self.log(f'🎯 {len(thumbs)} miniaturas encontradas — processando {total}')

                for i in range(total):
                    thumb = thumbs[i]
                    try:
                        # Scroll e clique
                        thumb.scroll_into_view_if_needed()
                        thumb.click()
                        page.wait_for_timeout(500)  # aguardar imagem grande trocar

                        # Capturar imagem grande (do frame ativo)
                        img_element = page.query_selector('.fotorama__stage__frame.fotorama__active img')
                        if not img_element:
                            continue

                        src = img_element.get_attribute('src')
                        if src and 'data:image' not in src and src not in seen:
                            seen.add(src)
                            clean = src.split('?')[0]
                            image_urls.append(clean)
                            self.log(f'  ✅ Imagem {i+1}: {clean[:80]}...')
                        else:
                            self.log(f'  ⚠️  Ignorada (duplicada ou vazia)')
                    except Exception as e:
                        self.log(f'  ❌ Erro miniatura {i+1}: {e}')

                browser.close()
                self.log(f'🎭 Extraídas {len(image_urls)} via Playwright ({time.time() - start:.2f}s)')
                return image_urls

        except Exception as e:
            self.log(f'❌ Erro Playwright: {e}', self.style.ERROR)
            return []


    # ------------------------------------------------------------------
    # DOWNLOAD E SALVAMENTO
    # ------------------------------------------------------------------
    def save_images_to_product(self, url, image_urls):
        self.log(f'💾 Salvando {len(image_urls)} imagens...')
        t0 = time.time()

        site, _ = Site.objects.get_or_create(
            url='https://nissei.com',
            defaults={'name': 'Casa Nissei Paraguay'}
        )

        Product.objects.filter(url=url, site=site).delete()
        product = Product.objects.create(
            name=f"Teste Rápido - {len(image_urls)} imgs",
            url=url,
            site=site,
            description="Produto de teste otimizado",
            price=0,
            status=1
        )

        # 🔄 Baixar em paralelo
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(self.download_and_optimize, img_url, i): img_url
                for i, img_url in enumerate(image_urls)
            }

            for i, (future, img_url) in enumerate(futures.items()):
                try:
                    content = future.result()
                    if not content:
                        self.log(f'     ❌ Falha {img_url[:60]}')
                        continue
                    filename = f"nissei_fast_{product.id}_{i+1}.jpg"
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
                    self.log(f'     ✅ {filename} salvo')
                except Exception as e:
                    self.log(f'     ❌ Erro {str(e)[:70]}')

        self.log(f'✅ Produto {product.id} salvo em {time.time() - t0:.2f}s')
        return product.id

    def download_and_optimize(self, url, i):
        """Download e otimização leve"""
        try:
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            r.raise_for_status()
            return self.optimize_image(r.content)
        except Exception:
            return None

    def optimize_image(self, content):
        """Compressão leve"""
        try:
            img = Image.open(BytesIO(content))
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            if img.width > 1500 or img.height > 1500:
                img.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
            output = BytesIO()
            img.save(output, format='JPEG', quality=90, optimize=True)
            return output.getvalue()
        except:
            return None

    def verify_saved_images(self, product_id):
        self.log('🔍 Verificando imagens...')
        product = Product.objects.get(id=product_id)
        imgs = product.images.all().order_by('order')
        self.log(f'📦 {product.name} - {imgs.count()} imagens')
        for img in imgs:
            main = "🌟" if img.is_main else ""
            self.log(f'  {img.order+1}. {img.image.name} {main}')

    def cleanup_product(self, product_id):
        self.log('🧹 Limpando produto...')
        try:
            p = Product.objects.get(id=product_id)
            count = p.images.count()
            p.images.all().delete()
            p.delete()
            self.log(f'✅ Removido 1 produto + {count} imagens')
        except Exception as e:
            self.log(f'❌ Erro limpeza: {e}')
