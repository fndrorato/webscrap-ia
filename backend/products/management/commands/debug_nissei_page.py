from django.core.management.base import BaseCommand
from products.models import Site
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

class Command(BaseCommand):
    help = 'Debug específico de uma página do Nissei para encontrar imagens e categorias'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url', 
            type=str, 
            default='https://nissei.com/py/apple-iphone-13-lz-a',
            help='URL específica para analisar'
        )

    def handle(self, *args, **options):
        url = options['url']
        
        self.stdout.write(f"🔍 DEBUG PÁGINA ESPECÍFICA")
        self.stdout.write(f"URL: {url}")
        self.stdout.write("=" * 60)
        
        try:
            # Fazer request
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            response = session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            self.stdout.write(f"✅ Página carregada: {len(response.text):,} caracteres")
            self.stdout.write("")
            
            # ANÁLISE DE IMAGENS
            self._analyze_images(soup, url)
            self.stdout.write("")
            
            # ANÁLISE DE CATEGORIAS  
            self._analyze_categories(soup)
            self.stdout.write("")
            
            # ANÁLISE DE ESTRUTURA GERAL
            self._analyze_structure(soup)
            
        except Exception as e:
            self.stdout.write(f"❌ ERRO: {str(e)}")

    def _analyze_images(self, soup, base_url):
        """Análise detalhada das imagens"""
        self.stdout.write("📸 ANÁLISE DE IMAGENS")
        self.stdout.write("-" * 30)
        
        # Encontrar todas as imagens
        all_images = soup.find_all('img')
        self.stdout.write(f"Total de imagens na página: {len(all_images)}")
        
        # Categorizar imagens
        product_images = []
        other_images = []
        
        for img in all_images:
            src = img.get('src') or img.get('data-src') or img.get('data-zoom-image')
            if src:
                full_url = urljoin(base_url, src)
                
                # Classificar imagem
                is_product = self._is_likely_product_image(full_url, img)
                
                if is_product:
                    product_images.append((full_url, img))
                else:
                    other_images.append((full_url, img))
        
        self.stdout.write(f"\n📱 IMAGENS DE PRODUTO POTENCIAIS: {len(product_images)}")
        for i, (url, img) in enumerate(product_images[:8], 1):
            alt_text = img.get('alt', 'Sem alt')[:50]
            classes = ' '.join(img.get('class', []))
            self.stdout.write(f"  {i}. {url}")
            self.stdout.write(f"     Alt: {alt_text}")
            self.stdout.write(f"     Classes: {classes}")
            
            # Verificar atributos especiais
            special_attrs = {}
            for attr in ['data-zoom-image', 'data-full', 'data-large', 'data-src']:
                if img.get(attr):
                    special_attrs[attr] = img[attr]
            
            if special_attrs:
                self.stdout.write(f"     Atributos especiais: {special_attrs}")
            self.stdout.write("")
        
        self.stdout.write(f"🔍 OUTRAS IMAGENS: {len(other_images)}")
        for i, (url, img) in enumerate(other_images[:5], 1):
            classes = ' '.join(img.get('class', []))[:50]
            self.stdout.write(f"  {i}. {url[:60]}...")
            self.stdout.write(f"     Classes: {classes}")
        
        # Procurar por seletores específicos de galeria
        self.stdout.write(f"\n🖼️ ELEMENTOS DE GALERIA:")
        gallery_selectors = [
            '.fotorama',
            '.product-image-gallery', 
            '.gallery-placeholder',
            '.product-media-gallery',
            '.more-views',
            '[data-gallery]',
            '.slick-slide',
            '.swiper-slide'
        ]
        
        for selector in gallery_selectors:
            elements = soup.select(selector)
            if elements:
                self.stdout.write(f"  ✅ {selector}: {len(elements)} elementos")
                for elem in elements[:2]:
                    classes = ' '.join(elem.get('class', []))
                    self.stdout.write(f"     Classes: {classes}")
            else:
                self.stdout.write(f"  ❌ {selector}: 0 elementos")

    def _analyze_categories(self, soup):
        """Análise detalhada das categorias"""
        self.stdout.write("🏷️ ANÁLISE DE CATEGORIAS")
        self.stdout.write("-" * 30)
        
        # Breadcrumbs
        breadcrumb_selectors = [
            '.breadcrumbs',
            '.breadcrumb', 
            '.navigation',
            '[class*="breadcrumb"]'
        ]
        
        categories_found = []
        
        for selector in breadcrumb_selectors:
            elements = soup.select(selector)
            self.stdout.write(f"Seletor '{selector}': {len(elements)} elementos")
            
            for elem in elements:
                # Procurar links dentro
                links = elem.find_all('a')
                for link in links:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    if text and len(text) > 1:
                        categories_found.append((text, href))
                        self.stdout.write(f"  📂 {text} → {href}")
        
        # Meta tags
        self.stdout.write(f"\n📋 META TAGS:")
        meta_category = soup.find('meta', {'name': 'category'})
        if meta_category:
            self.stdout.write(f"  Meta category: {meta_category.get('content')}")
        
        meta_keywords = soup.find('meta', {'name': 'keywords'})
        if meta_keywords:
            keywords = meta_keywords.get('content', '')[:100]
            self.stdout.write(f"  Meta keywords: {keywords}...")
        
        # JSON-LD
        json_scripts = soup.find_all('script', {'type': 'application/ld+json'})
        self.stdout.write(f"\n📊 JSON-LD: {len(json_scripts)} scripts")
        
        for script in json_scripts:
            try:
                import json
                data = json.loads(script.string)
                if 'category' in data:
                    self.stdout.write(f"  JSON categoria: {data['category']}")
                if '@type' in data:
                    self.stdout.write(f"  JSON tipo: {data['@type']}")
            except:
                pass

    def _analyze_structure(self, soup):
        """Análise geral da estrutura"""
        self.stdout.write("🏗️ ESTRUTURA GERAL")
        self.stdout.write("-" * 30)
        
        # Title
        title = soup.find('title')
        if title:
            self.stdout.write(f"📋 Título: {title.get_text()}")
        
        # H1
        h1 = soup.find('h1')
        if h1:
            self.stdout.write(f"🎯 H1: {h1.get_text(strip=True)}")
        
        # Procurar divs com classes relacionadas a produto
        product_divs = soup.find_all('div', class_=lambda x: x and any(
            word in ' '.join(x).lower() 
            for word in ['product', 'item', 'detail', 'info']
        ))
        
        self.stdout.write(f"\n📦 DIVS DE PRODUTO: {len(product_divs)}")
        for div in product_divs[:5]:
            classes = ' '.join(div.get('class', []))[:80]
            self.stdout.write(f"  📂 {classes}")
        
        # Procurar por preços
        price_elements = soup.find_all(['span', 'div'], string=re.compile(r'Gs\.|[0-9]{1,3}[,.]?[0-9]{3}'))
        self.stdout.write(f"\n💰 ELEMENTOS COM PREÇO: {len(price_elements)}")
        for elem in price_elements[:3]:
            text = elem.get_text(strip=True)
            classes = ' '.join(elem.get('class', []))[:50]
            self.stdout.write(f"  💵 {text} (classes: {classes})")

    def _is_likely_product_image(self, url, img_element):
        """Determina se é provável que seja imagem de produto"""
        url_lower = url.lower()
        
        # Deve ter extensão de imagem
        if not any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            return False
        
        # Indicadores positivos
        positive_indicators = [
            'product', 'catalog', 'media', 'gallery', 'iphone', 'samsung', 
            'apple', 'image', '/m/', '/l/', 'large'
        ]
        
        # Indicadores negativos
        negative_indicators = [
            'logo', 'icon', 'sprite', 'badge', 'button', 'arrow',
            'cart', 'menu', 'header', 'footer', 'banner'
        ]
        
        has_positive = any(indicator in url_lower for indicator in positive_indicators)
        has_negative = any(indicator in url_lower for indicator in negative_indicators)
        
        # Verificar classes do elemento
        classes = ' '.join(img_element.get('class', [])).lower()
        if any(word in classes for word in ['product', 'gallery', 'main', 'featured']):
            has_positive = True
        
        return has_positive and not has_negative