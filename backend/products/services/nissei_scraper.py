import re
import requests
import time
from bs4 import BeautifulSoup
from decimal import Decimal
from products.models import Product
from products.services.image_downloader import ProductImageDownloader
from products.services.agno_scraper import AgnoIntelligentScraper
from sites.models import Site
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse


class NisseiSpecializedScraper(AgnoIntelligentScraper):
    """
    Scraper especializado para o site Nissei.com (Paraguai)
    """
    
    def __init__(self, site: Site):
        super().__init__(site)
        self.base_url = "https://nissei.com"
        self.currency = "Gs."  # Guarani Paraguaio
        
        # Headers específicos para Nissei
        self.session.headers.update({
            'Accept-Language': 'es-419,es;q=0.9,en;q=0.8,pt;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        })
    
    def get_scraping_instructions(self, query: str) -> Dict[str, Any]:
        """
        Configuração específica para Nissei.com baseada na estrutura conhecida
        """
        # Configuração otimizada baseada na análise do site
        return {
            "site_analysis": "Nissei.com - Loja de eletrônicos do Paraguai com estrutura Shopify",
            "search_url_pattern": f"{self.base_url}/py/search?q={{query}}",
            "product_selector": ".grid-product, .product-item, [data-product-id], .product-card",
            "name_selector": ".product-title, .grid-product__title, h3.product-name, .product-info h3",
            "price_selector": ".price, .product-price, .grid-product__price, .money, .price-current",
            "original_price_selector": ".price-compare, .was, .original-price, .compare-at-price",
            "link_selector": "a.product-link, .grid-product__link, .product-item-link",
            "image_selector": ".product-image img, .grid-product__image img, .featured-image img",
            "description_selector": ".product-description, .grid-product__meta",
            "rating_selector": ".rating, .stars, .product-rating",
            "availability_selector": ".stock-level, .availability, .in-stock, .out-of-stock",
            "brand_selector": ".product-vendor, .brand, .manufacturer",
            "filter_keywords": query.lower().split(),
            "confidence_score": 0.92,  # Alta confiança pois conhecemos a estrutura
            "recommendations": "Site Shopify com estrutura padrão. Use seletores específicos para melhor precisão.",
            "base_url": self.base_url,
            "pagination_selector": ".pagination a, .pagination__next",
            "category_urls": {
                "electronica": f"{self.base_url}/py/electronica",
                "informatica": f"{self.base_url}/py/informatica", 
                "fotografia": f"{self.base_url}/py/fotografia-filmacion",
                "videojuegos": f"{self.base_url}/py/videojuegos-juguetes",
                "electrodomesticos": f"{self.base_url}/py/electrodomesticos-muebles"
            }
        }
    
    def _build_search_url(self, query: str, instructions: Dict[str, Any]) -> str:
        """Constrói URL de busca específica para Nissei"""
        # URL de busca específica do Nissei
        search_url = f"{self.base_url}/py/search?q={query.replace(' ', '+')}"
        
        # Se a query corresponde a categorias específicas, usar URL da categoria
        query_lower = query.lower()
        category_mapping = {
            'celular': f"{self.base_url}/py/electronica/celulares",
            'smartphone': f"{self.base_url}/py/electronica/celulares", 
            'notebook': f"{self.base_url}/py/informatica/notebooks",
            'laptop': f"{self.base_url}/py/informatica/notebooks",
            'camera': f"{self.base_url}/py/fotografia-filmacion/camaras",
            'mouse': f"{self.base_url}/py/informatica/mouse-teclados",
            'teclado': f"{self.base_url}/py/informatica/mouse-teclados",
            'audifonos': f"{self.base_url}/py/electronica/audifonos",
            'tablet': f"{self.base_url}/py/informatica/tablets"
        }
        
        for keyword, category_url in category_mapping.items():
            if keyword in query_lower:
                return f"{category_url}?q={query.replace(' ', '+')}"
        
        return search_url
    
    def scrape_products(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Faz scraping especializado no Nissei.com
        """
        try:
            # Obter instruções otimizadas
            instructions = self.get_scraping_instructions(query)
            
            # Construir URL de busca
            search_url = self._build_search_url(query, instructions)
            print(f"🔍 Buscando em: {search_url}")
            
            # Obter conteúdo da primeira página
            products = []
            page = 1
            max_pages = 3  # Limitar a 3 páginas para não ser muito lento
            
            while len(products) < max_results and page <= max_pages:
                page_url = f"{search_url}&page={page}" if page > 1 else search_url
                
                try:
                    response = self.session.get(page_url, timeout=30)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    page_products = self._extract_nissei_products(soup, instructions, query)
                    
                    if not page_products:
                        break  # Sem mais produtos, parar
                    
                    products.extend(page_products)
                    page += 1
                    
                    # Rate limiting
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"⚠️ Erro na página {page}: {str(e)}")
                    break
            
            # Limitar resultados
            products = products[:max_results]
            
            # Adicionar metadados
            for product in products:
                product['site_id'] = self.site.id
                product['search_query'] = query
                product['scraping_instructions'] = instructions
                product['confidence_score'] = instructions.get('confidence_score', 0.9)
                product['currency'] = self.currency
            
            # Salvar produtos
            self._save_nissei_products(products)
            
            print(f"✅ Encontrados {len(products)} produtos no Nissei.com")
            return products
            
        except Exception as e:
            print(f"❌ Erro no scraping do Nissei: {str(e)}")
            return []
    
    def _extract_nissei_products(self, soup: BeautifulSoup, instructions: Dict, query: str) -> List[Dict[str, Any]]:
        """Extrai produtos específicamente da estrutura do Nissei"""
        products = []
        
        # Seletores específicos do Nissei (estrutura Shopify)
        product_selectors = [
            '.grid-product',
            '.product-item',
            '[data-product-id]',
            '.card-product',
            '.product-card',
            '.grid__item'  # Seletor comum do Shopify
        ]
        
        product_elements = []
        for selector in product_selectors:
            elements = soup.select(selector)
            if elements:
                product_elements = elements
                print(f"🎯 Usando seletor: {selector} ({len(elements)} produtos)")
                break
        
        if not product_elements:
            print("⚠️ Nenhum elemento de produto encontrado, tentando seletores genéricos...")
            product_elements = soup.select('div[class*="product"], article[class*="product"]')
        
        for element in product_elements:
            try:
                product_data = self._extract_nissei_product_data(element, instructions)
                if self._is_relevant_product(product_data, query):
                    products.append(product_data)
            except Exception as e:
                print(f"⚠️ Erro ao extrair produto: {str(e)}")
                continue
        
        return products
    
    def _extract_nissei_product_data(self, element, instructions: Dict) -> Dict[str, Any]:
        """Extrai dados de um produto específico do Nissei"""
        
        # Nome do produto
        name_selectors = [
            '.grid-product__title',
            '.product-title', 
            '.card-title',
            'h3',
            'h2',
            '.product-name',
            '[class*="title"]'
        ]
        name = self._extract_text_by_selectors(element, name_selectors)
        
        # Preço
        price_selectors = [
            '.grid-product__price .money',
            '.price .money',
            '.product-price .money',
            '.price-current',
            '[class*="price"]:not([class*="compare"])',
            '.money'
        ]
        price_text = self._extract_text_by_selectors(element, price_selectors)
        price = self._extract_guarani_price(price_text)
        
        # Preço original (se em promoção)
        original_price_selectors = [
            '.compare-at-price .money',
            '.price-compare .money',
            '.was .money',
            '.original-price'
        ]
        original_price_text = self._extract_text_by_selectors(element, original_price_selectors)
        original_price = self._extract_guarani_price(original_price_text) if original_price_text else None
        
        # Link do produto
        link_element = element.find('a')
        if not link_element:
            link_element = element.find_parent('a')
        product_url = urljoin(self.base_url, link_element.get('href')) if link_element else ''
        
        # Imagem
        img_selectors = [
            '.grid-product__image img',
            '.product-image img',
            '.featured-image img',
            'img[class*="product"]',
            'img'
        ]
        img_element = None
        for selector in img_selectors:
            img_element = element.select_one(selector)
            if img_element:
                break
        
        image_url = ''
        if img_element:
            # Tentar diferentes atributos
            src_attrs = ['data-src', 'data-srcset', 'src', 'data-original']
            for attr in src_attrs:
                src = img_element.get(attr)
                if src:
                    # Pegar a primeira URL se for srcset
                    if ',' in src:
                        src = src.split(',')[0].strip().split(' ')[0]
                    image_url = urljoin(self.base_url, src)
                    break
        
        # Marca (se disponível)
        brand_selectors = ['.product-vendor', '.brand', '.manufacturer']
        brand = self._extract_text_by_selectors(element, brand_selectors)
        
        # Disponibilidade
        availability = "Disponible"  # Padrão para produtos listados
        if element.select('.soldout, .out-of-stock, [class*="unavailable"]'):
            availability = "Agotado"
        
        return {
            'name': name or 'Producto sin nombre',
            'price': price,
            'original_price': original_price,
            'url': product_url,
            'image_url': image_url,
            'brand': brand,
            'availability': availability,
            'currency': self.currency,
            'description': ''  # Será preenchido depois se necessário
        }
    
    def _extract_guarani_price(self, price_text: str) -> Optional[Decimal]:
        """Extrai preço em Guarani (Gs.) do texto"""
        if not price_text:
            return None
        
        # Remove "Gs." e outros caracteres, mantém apenas dígitos e pontos/vírgulas
        price_clean = re.sub(r'[^\d.,]', '', price_text.replace('Gs.', '').replace('Gs', ''))
        
        if not price_clean:
            return None
        
        try:
            # Guarani geralmente usa pontos como separadores de milhares
            # Ex: Gs. 1.500.000
            if '.' in price_clean and ',' not in price_clean:
                # Formato: 1.500.000 (pontos como separadores de milhares)
                price_clean = price_clean.replace('.', '')
            elif ',' in price_clean:
                # Se tem vírgula, assumir que é decimal
                price_clean = price_clean.replace('.', '').replace(',', '.')
            
            return Decimal(price_clean)
        except (ValueError, Exception):
            return None
    
    def _is_relevant_product(self, product_data: Dict, query: str) -> bool:
        """Verifica se o produto é relevante para a busca"""
        if not product_data.get('name') or not product_data.get('price'):
            return False
        
        # Verificar se a query está no nome do produto
        name_lower = product_data['name'].lower()
        query_words = query.lower().split()
        
        # Produto é relevante se contém pelo menos uma palavra da busca
        return any(word in name_lower for word in query_words if len(word) > 2)
    
    def _save_nissei_products(self, products: List[Dict[str, Any]]):
        """Salva produtos do Nissei no banco de dados"""
        for product_data in products:
            try:
                # Verificar se produto já existe
                existing = Product.objects.filter(
                    url=product_data.get('url', ''),
                    site=self.site
                ).first()
                
                if existing:
                    # Atualizar produto existente
                    existing.name = product_data.get('name', '')[:300]
                    existing.price = product_data.get('price')
                    existing.original_price = product_data.get('original_price')
                    existing.brand = product_data.get('brand', '')[:100] if product_data.get('brand') else None
                    existing.availability = product_data.get('availability', '')[:100]
                    existing.scraped_data = product_data.get('scraping_instructions', {})
                    existing.save()
                    
                    # Baixar imagens se não tem
                    if not existing.main_image and product_data.get('url'):
                        self._download_product_images_async(existing)
                else:
                    # Criar novo produto
                    new_product = Product.objects.create(
                        name=product_data.get('name', '')[:300],
                        price=product_data.get('price'),
                        original_price=product_data.get('original_price'),
                        url=product_data.get('url', ''),
                        brand=product_data.get('brand', '')[:100] if product_data.get('brand') else None,
                        availability=product_data.get('availability', '')[:100],
                        site=self.site,
                        search_query=product_data.get('search_query', ''),
                        scraped_data=product_data.get('scraping_instructions', {}),
                        status=1  # Aguardando Sincronização
                    )
                    
                    # Baixar imagens para novo produto
                    if product_data.get('url'):
                        self._download_product_images_async(new_product)
                    
            except Exception as e:
                print(f"❌ Erro ao salvar produto: {str(e)}")
                continue
    
    def _download_product_images_async(self, product: Product):
        """Baixa imagens do produto (pode ser feito assincronamente em produção)"""
        try:
            downloader = ProductImageDownloader()
            images = downloader.download_product_images(product, max_images=3)
            
            if images:
                print(f"📸 Baixadas {len(images)} imagens para {product.name}")
        except Exception as e:
            print(f"⚠️ Erro ao baixar imagens: {str(e)}")
