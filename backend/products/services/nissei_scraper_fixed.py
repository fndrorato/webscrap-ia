import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import re
import time
from decimal import Decimal, InvalidOperation
from django.utils import timezone  # ✅ IMPORT CORRIGIDO
from products.models import Product
from sites.models import Site

class NisseiScraper:
    """
    Scraper independente e robusto para Nissei.com - VERSÃO CORRIGIDA
    """
    
    def __init__(self, site: Site):
        self.site = site
        self.base_url = "https://nissei.com"
        self.currency = "Gs."
        
        # Configurar sessão HTTP
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-419,es;q=0.9,en;q=0.8,pt;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        })
        
        # Rate limiting
        self.delay_between_requests = 2
        self.max_retries = 3
    
    def scrape_products(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Método principal para fazer scraping de produtos no Nissei"""
        try:
            print(f"🔍 Iniciando busca por '{query}' no Nissei.com...")
            
            # Construir URL de busca
            search_url = self._build_search_url(query)
            print(f"🌐 URL de busca: {search_url}")
            
            # Fazer scraping das páginas
            all_products = []
            page = 1
            max_pages = 2  # Reduzir para ser mais rápido
            
            while len(all_products) < max_results and page <= max_pages:
                try:
                    page_url = self._get_page_url(search_url, page)
                    print(f"📄 Processando página {page}: {page_url}")
                    
                    # Obter HTML da página
                    html_content = self._fetch_page(page_url)
                    if not html_content:
                        print(f"⚠️ Não foi possível obter conteúdo da página {page}")
                        break
                    
                    # Debug: verificar se temos produtos na página
                    if "producto" in html_content.lower() or "product" in html_content.lower():
                        print("✅ Página contém produtos")
                    else:
                        print("⚠️ Página pode não conter produtos")
                    
                    # Extrair produtos da página
                    page_products = self._extract_products_from_html(html_content, query)
                    
                    if not page_products:
                        print(f"⚠️ Nenhum produto extraído da página {page}")
                        
                        # Se primeira página sem produtos, tentar URL alternativa
                        if page == 1:
                            alt_search_url = f"{self.base_url}/py/search?q={query.replace(' ', '+')}"
                            if alt_search_url != search_url:
                                print(f"🔄 Tentando URL alternativa: {alt_search_url}")
                                alt_html = self._fetch_page(alt_search_url)
                                if alt_html:
                                    page_products = self._extract_products_from_html(alt_html, query)
                    
                    if page_products:
                        all_products.extend(page_products)
                        print(f"✅ Página {page}: {len(page_products)} produtos encontrados")
                    else:
                        print(f"❌ Página {page}: nenhum produto válido")
                        break
                    
                    page += 1
                    
                    # Rate limiting
                    if page <= max_pages:
                        time.sleep(self.delay_between_requests)
                
                except Exception as e:
                    print(f"❌ Erro na página {page}: {str(e)}")
                    break
            
            # Limitar resultados finais
            final_products = all_products[:max_results]
            
            # Adicionar metadados usando timezone importado corretamente
            for product in final_products:
                product.update({
                    'site_id': self.site.id,
                    'site_name': self.site.name,
                    'search_query': query,
                    'currency': self.currency,
                    'scraped_at': timezone.now().isoformat(),  # ✅ CORRIGIDO
                    'country': 'Paraguay'
                })
            
            # Salvar no banco de dados
            self._save_products(final_products)
            
            print(f"🎉 Scraping concluído: {len(final_products)} produtos encontrados e salvos")
            return final_products
            
        except Exception as e:
            print(f"❌ Erro geral no scraping: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def _build_search_url(self, query: str) -> str:
        """Constrói URL de busca - VERSÃO MELHORADA"""
        query_encoded = query.replace(' ', '+')
        
        # URLs de busca possíveis para o Nissei
        possible_urls = [
            f"{self.base_url}/py/catalogsearch/result/?q={query_encoded}",
            f"{self.base_url}/py/search?q={query_encoded}",
            f"{self.base_url}/search?q={query_encoded}",
        ]
        
        # Por enquanto, usar a primeira
        return possible_urls[0]
    
    def _get_page_url(self, base_search_url: str, page: int) -> str:
        """Constrói URL para páginas específicas"""
        if page == 1:
            return base_search_url
        
        separator = '&' if '?' in base_search_url else '?'
        return f"{base_search_url}{separator}page={page}"
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """Faz requisição HTTP e retorna HTML"""
        for attempt in range(self.max_retries):
            try:
                print(f"🌐 Fazendo requisição para: {url}")
                response = self.session.get(url, timeout=30)
                
                print(f"📊 Status: {response.status_code}")
                
                if response.status_code == 200:
                    content_length = len(response.text)
                    print(f"📄 Conteúdo recebido: {content_length:,} caracteres")
                    return response.text
                else:
                    print(f"❌ Status HTTP não é 200: {response.status_code}")
                
            except requests.RequestException as e:
                print(f"⚠️ Tentativa {attempt + 1} falhou: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        
        return None
    
    def _extract_products_from_html(self, html: str, query: str) -> List[Dict[str, Any]]:
        """Extrai produtos do HTML - VERSÃO MELHORADA"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            products = []
            
            print(f"🔍 Analisando HTML ({len(html):,} caracteres)...")
            
            # Seletores expandidos baseados na estrutura real observada
            product_selectors = [
                # Seletores principais
                '.product-item',
                '.grid-product', 
                '.product-card',
                '[data-product-id]',
                
                # Seletores alternativos
                '.item.product',
                'li.item',
                '.product-item-info',
                'article[class*="product"]',
                'div[class*="product"]:not([class*="related"]):not([class*="upsell"])',
                
                # Seletores genéricos
                '.item',
                '[itemtype*="Product"]'
            ]
            
            # Tentar encontrar produtos
            product_elements = []
            selector_used = None
            
            for selector in product_selectors:
                elements = soup.select(selector)
                if elements:
                    # Filtrar elementos que realmente parecem produtos
                    valid_elements = []
                    for elem in elements:
                        if self._looks_like_product_element(elem):
                            valid_elements.append(elem)
                    
                    if valid_elements:
                        product_elements = valid_elements
                        selector_used = selector
                        print(f"🎯 Usando seletor '{selector}': {len(valid_elements)} elementos válidos (de {len(elements)} total)")
                        break
            
            if not product_elements:
                print("⚠️ Nenhum produto encontrado com seletores conhecidos")
                # Debug: mostrar algumas classes encontradas
                all_classes = set()
                for elem in soup.find_all(['div', 'article', 'li'], class_=True):
                    if isinstance(elem.get('class'), list):
                        all_classes.update(elem['class'])
                
                product_classes = [cls for cls in all_classes if any(word in cls.lower() for word in ['product', 'item', 'grid', 'card'])]
                if product_classes:
                    print(f"🔍 Classes relacionadas encontradas: {product_classes[:10]}")
                
                return []
            
            # Extrair dados de cada produto
            for i, element in enumerate(product_elements[:50]):  # Limitar para evitar timeout
                try:
                    product_data = self._extract_single_product(element, i + 1)
                    
                    if self._is_valid_product(product_data, query):
                        products.append(product_data)
                        print(f"✅ Produto {len(products)}: {product_data['name'][:50]}...")
                    else:
                        print(f"❌ Produto {i+1} inválido: {product_data.get('name', 'sem nome')[:30]}...")
                        
                except Exception as e:
                    print(f"⚠️ Erro ao extrair produto {i+1}: {str(e)}")
                    continue
            
            print(f"✅ {len(products)} produtos válidos extraídos de {len(product_elements)} elementos")
            return products
            
        except Exception as e:
            print(f"❌ Erro ao processar HTML: {str(e)}")
            return []
    
    def _looks_like_product_element(self, element) -> bool:
        """Verifica se elemento parece ser um produto real"""
        # Deve ter algum texto
        text_content = element.get_text(strip=True)
        if not text_content or len(text_content) < 10:
            return False
        
        # Não deve ser navegação, footer, etc.
        classes = ' '.join(element.get('class', [])).lower()
        exclude_classes = ['nav', 'header', 'footer', 'sidebar', 'menu', 'breadcrumb', 'pagination']
        if any(exc in classes for exc in exclude_classes):
            return False
        
        # Deve ter indicações de produto
        has_price_indicators = bool(element.select('[class*="price"], [class*="cost"], [class*="money"]'))
        has_title_indicators = bool(element.select('h1, h2, h3, h4, [class*="title"], [class*="name"]'))
        has_link_indicators = bool(element.select('a[href]'))
        
        return has_price_indicators or (has_title_indicators and has_link_indicators)
    
    def _extract_single_product(self, element, index: int = 0) -> Dict[str, Any]:
        """Extrai dados de um único produto - VERSÃO MELHORADA"""
        
        print(f"🔎 Extraindo produto {index}...")
        
        # Nome do produto - seletores expandidos
        name_selectors = [
            # Seletores específicos
            '.product-item-name a',
            '.product-name a',
            '.product-title',
            '.grid-product__title',
            '.card-title',
            'h3 a', 'h2 a', 'h4 a',
            
            # Seletores genéricos
            'a[class*="name"]',
            'a[class*="title"]',
            '[class*="product-name"]',
            '[class*="item-name"]',
            
            # Muito genéricos (últimos)
            'a[href*="product"]',
            'h3', 'h2', 'h4'
        ]
        
        name = self._extract_text_by_selectors(element, name_selectors)
        if not name:
            # Tentar extrair do primeiro link encontrado
            first_link = element.find('a')
            if first_link:
                name = first_link.get_text(strip=True)
        
        print(f"   Nome: {name[:50] if name else 'NÃO ENCONTRADO'}...")
        
        # Preço atual - seletores expandidos
        price_selectors = [
            # Específicos para Nissei/Magento
            '.price .regular-price .price',
            '.price .special-price .price',
            '.product-price-value',
            '.price-current',
            
            # Genéricos para preço
            '.price',
            '[class*="price"]:not([class*="old"]):not([class*="was"])',
            '.money',
            '[class*="cost"]',
            '[data-price]'
        ]
        
        price_text = self._extract_text_by_selectors(element, price_selectors)
        if not price_text:
            # Tentar extrair preço de atributos
            price_elem = element.find(attrs={'data-price': True})
            if price_elem:
                price_text = price_elem.get('data-price')
        
        current_price = self._parse_guarani_price(price_text)
        print(f"   Preço: {price_text} -> {current_price}")
        
        # Preço original (se em promoção)
        original_price_selectors = [
            '.old-price .price',
            '.regular-price .price',
            '[class*="was"]',
            '[class*="original"]',
            '[class*="compare"]'
        ]
        original_price_text = self._extract_text_by_selectors(element, original_price_selectors)
        original_price = self._parse_guarani_price(original_price_text) if original_price_text else None
        
        # Link do produto
        link_element = element.find('a', href=True)
        product_url = ''
        if link_element:
            href = link_element.get('href', '')
            if href:
                if href.startswith('/'):
                    product_url = f"{self.base_url}{href}"
                elif href.startswith('http'):
                    product_url = href
                else:
                    product_url = urljoin(self.base_url, href)
        
        print(f"   URL: {product_url}")
        
        # Imagem principal
        img_selectors = [
            '.product-image-main img',
            '.product-image img', 
            '.item-image img',
            'img[class*="product"]',
            'img'
        ]
        image_url = self._extract_image_url(element, img_selectors)
        
        # Marca/fabricante
        brand_selectors = [
            '.product-brand',
            '.brand',
            '.manufacturer',
            '[class*="brand"]'
        ]
        brand = self._extract_text_by_selectors(element, brand_selectors)
        
        # Status de disponibilidade
        availability = "Disponible"
        stock_indicators = element.select('.out-of-stock, .unavailable, [class*="soldout"]')
        if stock_indicators:
            availability = "Agotado"
        
        product_data = {
            'name': name.strip() if name else 'Produto sem nome',
            'price': current_price,
            'original_price': original_price,
            'url': product_url,
            'image_url': image_url,
            'brand': brand.strip() if brand else None,
            'availability': availability,
            'description': '',
            'debug_info': {
                'name_text': price_text,
                'has_price': bool(current_price),
                'has_url': bool(product_url)
            }
        }
        
        return product_data
    
    def _extract_text_by_selectors(self, element, selectors: List[str]) -> str:
        """Extrai texto usando lista de seletores CSS"""
        for selector in selectors:
            try:
                found = element.select_one(selector)
                if found:
                    text = found.get_text(strip=True)
                    if text and len(text) > 1:  # Pelo menos 2 caracteres
                        return text
            except Exception:
                continue
        return ''
    
    def _extract_image_url(self, element, selectors: List[str]) -> str:
        """Extrai URL da imagem principal"""
        for selector in selectors:
            try:
                img = element.select_one(selector)
                if img:
                    # Tentar diferentes atributos
                    for attr in ['data-src', 'data-srcset', 'src', 'data-original']:
                        src = img.get(attr)
                        if src:
                            # Se for srcset, pegar primeira URL
                            if ',' in src:
                                src = src.split(',')[0].strip().split(' ')[0]
                            
                            # Resolver URL absoluta
                            if src.startswith('/'):
                                full_url = f"{self.base_url}{src}"
                            elif src.startswith('http'):
                                full_url = src
                            else:
                                full_url = urljoin(self.base_url, src)
                            
                            # Validar se é imagem válida
                            if self._is_valid_image_url(full_url):
                                return full_url
            except Exception:
                continue
        return ''
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Valida se URL é de uma imagem real de produto"""
        if not url or len(url) < 10:
            return False
        
        url_lower = url.lower()
        
        # Deve ter extensão de imagem
        if not any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
            return False
        
        # Excluir ícones pequenos
        exclude_patterns = ['icon', 'logo', 'sprite', 'badge', '1x1', 'pixel', 'spacer', 'loading']
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False
        
        return True
    
    def _parse_guarani_price(self, price_text: str) -> Optional[Decimal]:
        """Converte texto de preço em Guarani para Decimal - MELHORADO"""
        if not price_text:
            return None
        
        try:
            print(f"   🔄 Parseando preço: '{price_text}'")
            
            # Remover texto não numérico, manter apenas dígitos, pontos e vírgulas
            price_clean = re.sub(r'[^\d.,]', '', price_text)
            
            if not price_clean:
                return None
            
            # Lógica para Guarani Paraguaio
            # Formato comum: "Gs. 1.500.000" ou "1.500.000"
            if '.' in price_clean and ',' not in price_clean:
                # Formato: 1.500.000 - remover pontos (são separadores de milhares)
                price_clean = price_clean.replace('.', '')
            elif ',' in price_clean and '.' in price_clean:
                # Formato: 1.500.000,00 - remover pontos, vírgula vira ponto decimal
                parts = price_clean.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:  # centavos
                    price_clean = parts[0].replace('.', '') + '.' + parts[1]
                else:
                    # Vírgula pode ser separador de milhares
                    price_clean = price_clean.replace('.', '').replace(',', '')
            elif ',' in price_clean:
                # Só vírgula - pode ser decimal ou separador de milhares
                parts = price_clean.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    price_clean = parts[0] + '.' + parts[1]
                else:
                    price_clean = price_clean.replace(',', '')
            
            decimal_price = Decimal(price_clean)
            print(f"   ✅ Preço parseado: {decimal_price}")
            return decimal_price
            
        except (InvalidOperation, ValueError, Exception) as e:
            print(f"   ❌ Erro ao parsear preço '{price_text}': {str(e)}")
            return None
    
    def _is_valid_product(self, product_data: Dict[str, Any], query: str) -> bool:
        """Valida se o produto extraído é válido e relevante - MELHORADO"""
        
        # Deve ter nome
        if not product_data.get('name') or len(product_data['name'].strip()) < 3:
            print(f"   ❌ Nome inválido: '{product_data.get('name', '')}'")
            return False
        
        # Deve ter preço OU URL (alguns produtos podem não mostrar preço na listagem)
        if not product_data.get('price') and not product_data.get('url'):
            print(f"   ❌ Sem preço nem URL")
            return False
        
        name = product_data['name'].lower()
        
        # Nome não pode ser muito genérico
        generic_names = ['producto', 'item', 'ver más', 'más info', 'detalle']
        if any(generic in name for generic in generic_names):
            print(f"   ❌ Nome muito genérico: '{name}'")
            return False
        
        # Verificar relevância com a busca (mais relaxado)
        query_words = [word.lower().strip() for word in query.split() if len(word) > 2]
        if query_words:
            # Buscar correspondências parciais
            relevance_score = 0
            for query_word in query_words:
                if query_word in name:
                    relevance_score += 1
                elif any(query_word in name_word for name_word in name.split()):
                    relevance_score += 0.5
            
            # Aceitar se tem pelo menos 30% de relevância
            min_relevance = len(query_words) * 0.3
            if relevance_score < min_relevance:
                print(f"   ❌ Baixa relevância: {relevance_score:.1f} < {min_relevance:.1f}")
                return False
        
        print(f"   ✅ Produto válido: '{product_data['name'][:30]}...'")
        return True
    
    def _save_products(self, products: List[Dict[str, Any]]):
        """Salva produtos no banco de dados - com timezone corrigido"""
        saved_count = 0
        updated_count = 0
        
        for product_data in products:
            try:
                # Verificar se produto já existe
                existing_product = Product.objects.filter(
                    url=product_data.get('url', ''),
                    site=self.site
                ).first()
                
                if existing_product:
                    # Atualizar produto existente
                    existing_product.name = product_data['name'][:300]
                    existing_product.price = product_data.get('price')
                    existing_product.original_price = product_data.get('original_price')
                    existing_product.brand = product_data.get('brand', '')[:100] if product_data.get('brand') else None
                    existing_product.availability = product_data.get('availability', '')[:100]
                    existing_product.search_query = product_data.get('search_query', '')
                    existing_product.updated_at = timezone.now()  # ✅ CORRIGIDO
                    existing_product.save()
                    updated_count += 1
                    
                else:
                    # Criar novo produto
                    Product.objects.create(
                        name=product_data['name'][:300],
                        price=product_data.get('price'),
                        original_price=product_data.get('original_price'),
                        url=product_data.get('url', ''),
                        brand=product_data.get('brand', '')[:100] if product_data.get('brand') else None,
                        availability=product_data.get('availability', '')[:100],
                        site=self.site,
                        search_query=product_data.get('search_query', ''),
                        status=1  # Aguardando Sincronização
                    )
                    saved_count += 1
                    
            except Exception as e:
                print(f"⚠️ Erro ao salvar produto '{product_data.get('name', 'N/A')}': {str(e)}")
                continue
        
        print(f"💾 Salvos: {saved_count} novos, {updated_count} atualizados")
