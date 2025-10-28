# products/management/commands/test_search_and_extract.py

import time
from datetime import datetime
import requests
from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, quote
import re

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile

from sites.models import Site
from products.models import Product, ProductImage


class Command(BaseCommand):
    help = 'Pesquisa no Nissei e extrai imagens dos produtos'

    def add_arguments(self, parser):
        parser.add_argument('--query', type=str, default='iphone', help='Termo de pesquisa')
        parser.add_argument('--max-products', type=int, default=2, help='Máximo de produtos')
        parser.add_argument('--max-images', type=int, default=3, help='Máximo de imagens por produto')
        parser.add_argument('--cleanup', action='store_true', help='Remover após teste')

    def log(self, message, style=None):
        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        if style:
            self.stdout.write(f'[{ts}] {style(message)}')
        else:
            self.stdout.write(f'[{ts}] {message}')

    def handle(self, *args, **options):
        start = time.time()
        query = options['query']
        max_products = options['max_products']
        max_images = options['max_images']
        cleanup = options['cleanup']

        self.log('⚡ PESQUISA E EXTRAÇÃO NISSEI', self.style.SUCCESS)
        self.log(f'Termo: "{query}" | Produtos: {max_products} | Imagens: {max_images}')
        self.log('=' * 70)

        # 1️⃣ Pesquisar
        product_urls = self.search_products(query, max_products)
        if not product_urls:
            self.log('❌ Nenhum produto', self.style.ERROR)
            return

        # 2️⃣ Processar
        created = []
        for i, url in enumerate(product_urls):
            self.log(f'\n📦 [{i+1}/{len(product_urls)}] {url.split("/")[-1][:50]}')
            pid = self.process_product(url, max_images)
            if pid:
                created.append(pid)

        # 3️⃣ Resumo
        self.log('\n' + '=' * 70)
        self.log(f'✅ {len(created)}/{len(product_urls)} produtos salvos')
        
        if created:
            for pid in created:
                self.verify_product(pid)

        if cleanup and created:
            self.log('\n🧹 Limpando...')
            for pid in created:
                self.cleanup_product(pid)

        self.log(f'\n🎉 Tempo total: {time.time() - start:.2f}s', self.style.SUCCESS)

    def search_products(self, query, max_products):
        """Busca produtos"""
        self.log('🔎 Buscando produtos...')
        t0 = time.time()
        
        try:
            url = f'https://nissei.com/py/catalogsearch/result/?q={quote(query)}'
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            r.raise_for_status()
            
            soup = BeautifulSoup(r.text, 'html.parser')
            links = []
            seen = set()
            
            for item in soup.select('.product-item-link, a.product-item-link'):
                href = item.get('href')
                if href and '/py/' in href and 'catalogsearch' not in href:
                    full = urljoin('https://nissei.com', href)
                    if full not in seen:
                        links.append(full)
                        seen.add(full)
                        if len(links) >= max_products:
                            break
            
            self.log(f'✅ {len(links)} produtos em {time.time() - t0:.2f}s')
            return links
        except Exception as e:
            self.log(f'❌ {e}', self.style.ERROR)
            return []

    def process_product(self, url, max_images):
        """Processa produto"""
        t0 = time.time()
        
        try:
            images = self.extract_images(url, max_images)
            
            if not images:
                self.log('   ⚠️  Sem imagens')
                return None
            
            self.log(f'   ✅ {len(images)} imagens extraídas')
            pid = self.save_product(url, images)
            
            if pid:
                self.log(f'   ✅ Produto {pid} salvo em {time.time() - t0:.2f}s')
            return pid
        except Exception as e:
            self.log(f'   ❌ {e}')
            return None

    def extract_images(self, url, max_images):
        """Extrai imagens do carrossel"""
        from playwright.sync_api import sync_playwright
        
        try:
            t0 = time.time()
            self.log('   🚀 Extraindo imagens...')
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Aumentar timeout
                page.goto(url, wait_until='domcontentloaded', timeout=40000)
                
                # Aguardar carrossel
                try:
                    page.wait_for_selector('[data-gallery-role="gallery"]', timeout=15000)
                    page.wait_for_timeout(4000)  # Mais tempo para JS carregar
                except:
                    self.log('      ⚠️ Timeout ao aguardar carrossel')
                    browser.close()
                    return []
                
                # Extrair URLs
                urls = page.evaluate("""
                    () => {
                        const results = [];
                        
                        // Método 1: data-gallery-role
                        const frames = document.querySelectorAll('[data-gallery-role="nav-frame"] img');
                        if (frames.length > 0) {
                            frames.forEach(img => {
                                if (img.src && !img.src.includes('data:image')) {
                                    results.push(img.src);
                                }
                            });
                        }
                        
                        // Método 2: Classe fotorama
                        if (results.length === 0) {
                            const frames2 = document.querySelectorAll('.fotorama__nav__frame img');
                            frames2.forEach(img => {
                                if (img.src && !img.src.includes('data:image')) {
                                    results.push(img.src);
                                }
                            });
                        }
                        
                        return results;
                    }
                """)
                
                browser.close()
                
                if not urls:
                    self.log('      ❌ Nenhuma URL encontrada')
                    return []
                
                # Converter para originais
                originals = []
                seen = set()
                
                for u in urls:
                    orig = self.cache_to_original(u)
                    if orig and orig not in seen:
                        originals.append(orig)
                        seen.add(orig)
                        fname = orig.split("/")[-1][:40]
                        self.log(f'      ✅ {fname}')
                        if len(originals) >= max_images:
                            break
                
                self.log(f'      ⏱️  {len(originals)} imagens em {time.time() - t0:.2f}s')
                return originals
        
        except Exception as e:
            self.log(f'      ❌ Erro: {e}')
            return []

    def cache_to_original(self, url):
        """Remove /cache/HASH/ da URL para pegar imagem original"""
        if '/cache/' not in url:
            return url
        # Remove padrão: /cache/[32 hex chars]/
        pattern = r'/cache/[a-f0-9]{32}/'
        return re.sub(pattern, '/', url)

    def save_product(self, url, images):
        """Salva produto e imagens"""
        try:
            t0 = time.time()
            
            site, _ = Site.objects.get_or_create(
                url='https://nissei.com',
                defaults={'name': 'Casa Nissei Paraguay'}
            )
            
            # Remover produto duplicado se existir
            Product.objects.filter(url=url, site=site).delete()
            
            name = url.split('/')[-1].replace('-', ' ').title()[:70]
            
            product = Product.objects.create(
                name=f"{name} ({len(images)} imgs)",
                url=url,
                site=site,
                description=f"Produto com {len(images)} imagens",
                price=0,
                status=1,
                search_query="teste_pesquisa"
            )
            
            self.log(f'      📦 Produto {product.id} criado')
            
            # Download paralelo
            with ThreadPoolExecutor(max_workers=4) as ex:
                futures = {ex.submit(self.download, u): (i, u) for i, u in enumerate(images)}
                
                saved = 0
                for fut in futures:
                    i, u = futures[fut]
                    try:
                        content = fut.result()
                        if content:
                            fname = f"nissei_search_{product.id}_{i+1}.jpg"
                            ProductImage.objects.create(
                                product=product,
                                image=ContentFile(content, name=fname),
                                is_main=(i == 0),
                                order=i,
                                original_url=u
                            )
                            if i == 0:
                                product.main_image = ContentFile(content, name=fname)
                                product.save()
                            saved += 1
                    except Exception as e:
                        self.log(f'         ❌ Erro img {i+1}: {str(e)[:40]}')
                
                elapsed = time.time() - t0
                self.log(f'      💾 {saved}/{len(images)} imagens salvas em {elapsed:.2f}s')
                return product.id
        except Exception as e:
            self.log(f'      ❌ Erro ao salvar: {e}')
            return None

    def download(self, url):
        """Download e otimização"""
        try:
            r = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            r.raise_for_status()
            
            img = Image.open(BytesIO(r.content))
            if img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
            if img.width > 1500 or img.height > 1500:
                img.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
            
            out = BytesIO()
            img.save(out, format='JPEG', quality=90, optimize=True)
            return out.getvalue()
        except Exception as e:
            return None

    def verify_product(self, pid):
        """Verifica produto salvo"""
        try:
            p = Product.objects.get(id=pid)
            imgs = p.images.all().order_by('order')
            size = sum(i.image.size for i in imgs if i.image)
            
            self.log(f'\n   📦 ID {pid}: {p.name}')
            self.log(f'   🔗 {p.url}')
            self.log(f'   🖼️  {imgs.count()} imagens | {size/1024:.1f} KB')
            
            for img in imgs:
                if img.image:
                    m = " 🌟" if img.is_main else ""
                    self.log(f'      {img.order+1}. {img.image.name}{m}')
        except Exception as e:
            self.log(f'   ❌ Erro: {e}')

    def cleanup_product(self, pid):
        """Remove produto"""
        try:
            p = Product.objects.get(id=pid)
            c = p.images.count()
            p.images.all().delete()
            p.delete()
            self.log(f'   ✅ Produto {pid} removido ({c} imgs)')
        except Exception as e:
            self.log(f'   ❌ Erro: {e}')