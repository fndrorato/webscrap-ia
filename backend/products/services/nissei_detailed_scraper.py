import base64
import os
import re
import requests
import time
import urllib.request
import uuid
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
from products.models import Product, ProductImage
from sites.models import Site


# CONFIGURAÇÃO ADICIONAL para PIL
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True  # Permite imagens truncadas

class NisseiDetailedScraper:
    """
    Scraper completo do Nissei que visita cada produto individualmente
    para extrair descrição detalhada e baixar todas as imagens
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
            'Cache-Control': 'no-cache',
        })
        
        # Configurações
        self.delay_between_requests = 3  # Mais tempo entre requests
        self.delay_between_products = 5  # Pausa entre produtos individuais
        self.max_retries = 3
        self.max_images_per_product = 3
        
        # Validação de imagens
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        self.min_image_size = 1024  # 1KB
        self.supported_formats = ['jpeg', 'jpg', 'png', 'webp']
    
    def scrape_products_detailed(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Scraping completo com extração detalhada de cada produto
        """
        try:
            print(f"🔍 SCRAPING DETALHADO - Busca por '{query}' no Nissei.com")
            print("=" * 60)
            
            # FASE 1: Obter lista básica de produtos
            print("📋 FASE 1: Obtendo lista de produtos...")
            basic_products = self._get_basic_product_list(query, max_results)
            
            if not basic_products:
                print("❌ Nenhum produto encontrado na listagem")
                return []
            
            print(f"✅ {len(basic_products)} produtos encontrados na listagem")
            print("=" * 60)
            
            # FASE 2: Processar cada produto individualmente
            print("🔎 FASE 2: Processando produtos individualmente...")
            detailed_products = []
            
            for i, basic_product in enumerate(basic_products, 1):
                try:
                    print(f"\n📱 PRODUTO {i}/{len(basic_products)}: {basic_product['name'][:50]}...")
                    print(f"🌐 URL: {basic_product['url']}")
                    
                    # Extrair detalhes do produto individual
                    detailed_product = self._extract_product_details(basic_product)
                    
                    if detailed_product:
                        detailed_products.append(detailed_product)
                        print(f"✅ Produto processado com sucesso")
                        
                        # Baixar imagens do produto
                        print("📸 Baixando imagens...")
                        image_count = self._download_product_images(detailed_product)
                        print(f"📸 {image_count} imagens baixadas")
                    else:
                        print("❌ Falha ao processar produto")
                    
                    # Rate limiting entre produtos
                    if i < len(basic_products):
                        print(f"⏱️ Aguardando {self.delay_between_products}s...")
                        time.sleep(self.delay_between_products)
                        
                except Exception as e:
                    print(f"❌ Erro ao processar produto {i}: {str(e)}")
                    continue
            
            # FASE 3: Salvar no banco de dados
            print(f"\n💾 FASE 3: Salvando {len(detailed_products)} produtos...")
            saved_count = self._save_detailed_products(detailed_products)
            
            print(f"🎉 SCRAPING CONCLUÍDO!")
            print(f"📊 Produtos processados: {len(detailed_products)}")
            print(f"💾 Produtos salvos: {saved_count}")
            
            return detailed_products
            
        except Exception as e:
            print(f"❌ Erro geral no scraping detalhado: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def _get_basic_product_list(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Fase 1: Obter lista básica de produtos da busca"""
        try:
            query_encoded = query.replace(' ', '+')
            search_url = f"{self.base_url}/py/catalogsearch/result/?q={query_encoded}"
            
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Usar os mesmos seletores que funcionaram
            product_elements = soup.select('.product-item')[:max_results]
            
            basic_products = []
            for element in product_elements:
                try:
                    # Extrair apenas o essencial da listagem
                    name_elem = element.select_one('.product-item-name a, .product-name a, h3 a')
                    name = name_elem.get_text(strip=True) if name_elem else 'Sem nome'
                    
                    link_elem = element.find('a', href=True)
                    product_url = ''
                    if link_elem:
                        href = link_elem.get('href', '')
                        if href.startswith('/'):
                            product_url = f"{self.base_url}{href}"
                        elif href.startswith('http'):
                            product_url = href
                    
                    if name and product_url and len(name) > 3:
                        basic_products.append({
                            'name': name,
                            'url': product_url,
                            'search_query': query
                        })
                        
                except Exception as e:
                    continue
            
            return basic_products
            
        except Exception as e:
            print(f"❌ Erro ao obter lista básica: {str(e)}")
            return []

    def _extract_product_categories(self, soup: BeautifulSoup) -> List[str]:
        """Extrai categorias do produto - NOVO MÉTODO"""
        categories = []
        
        print(f"🏷️ Procurando categorias...")
        
        # Seletores para breadcrumbs/navegação
        breadcrumb_selectors = [
            '.breadcrumbs li a',
            '.breadcrumb-item a',
            '.breadcrumb a',
            '.navigation .crumb a',
            '.page-header .breadcrumbs a',
            '.toolbar-breadcrumbs a'
        ]
        
        for selector in breadcrumb_selectors:
            try:
                links = soup.select(selector)
                print(f"  🎯 Breadcrumb '{selector}': {len(links)} items")
                
                for link in links:
                    category_text = link.get_text(strip=True)
                    if category_text and len(category_text) > 2:
                        # Filtrar categorias irrelevantes
                        if category_text.lower() not in ['home', 'inicio', 'principal']:
                            categories.append(category_text)
                            print(f"    📂 Categoria: {category_text}")
                
                if categories:
                    break
                    
            except Exception as e:
                continue
        
        # Se não encontrou via breadcrumbs, tentar outras abordagens
        if not categories:
            print(f"⚠️ Tentando encontrar categorias por outros métodos...")
            
            # Procurar em meta tags
            meta_category = soup.find('meta', {'name': 'category'})
            if meta_category:
                categories.append(meta_category.get('content', ''))
            
            # Procurar em dados estruturados
            structured_data = soup.find('script', {'type': 'application/ld+json'})
            if structured_data:
                try:
                    data = json.loads(structured_data.string)
                    if 'category' in data:
                        categories.append(data['category'])
                except:
                    pass
        
        print(f"📊 Total de categorias encontradas: {len(categories)}")
        return list(set(categories))

    def _extract_specifications_improved(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extrai especificações técnicas - VERSÃO MELHORADA"""
        specs = {}
        
        print(f"🔧 Procurando especificações técnicas...")
        
        # Seletores para tabelas de especificações
        spec_table_selectors = [
            '#additional .data.table tbody tr',
            '.additional-attributes-wrapper .data.table tr',
            '.product-specifications tbody tr',
            '.product-attributes tr',
            '.data.table.additional-attributes tr',
            '.spec-table tr',
            '.features-table tr'
        ]
        
        for selector in spec_table_selectors:
            try:
                rows = soup.select(selector)
                print(f"  🎯 Especificações '{selector}': {len(rows)} linhas")
                
                for row in rows:
                    cells = row.select('td, th')
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value and len(key) < 100:  # Filtrar keys muito longas
                            specs[key] = value
                            print(f"    📋 {key}: {value}")
                
                if specs:
                    break
                    
            except Exception as e:
                continue
        
        # Se não encontrou em tabelas, procurar em listas
        if not specs:
            list_selectors = [
                '.product-specs li',
                '.specifications li',
                '.features li',
                '.product-features li'
            ]
            
            for selector in list_selectors:
                try:
                    items = soup.select(selector)
                    for item in items:
                        text = item.get_text(strip=True)
                        if ':' in text:
                            parts = text.split(':', 1)
                            if len(parts) == 2:
                                specs[parts[0].strip()] = parts[1].strip()
                except:
                    continue
        
        print(f"📊 Total de especificações encontradas: {len(specs)}")
        return specs


    def _extract_product_details(self, basic_product: Dict) -> Optional[Dict[str, Any]]:
        """Versão melhorada da extração de detalhes"""
        try:
            product_url = basic_product['url']
            
            # Acessar página individual do produto
            print(f"🌐 Acessando página individual...")
            response = self.session.get(product_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extrair informações detalhadas
            detailed_product = basic_product.copy()
            
            # Nome mais preciso - SELETORES MELHORADOS
            name_selectors = [
                'h1.page-title span',      # Magento comum
                'h1.page-title',
                '.product-info-main h1',
                '.product-name h1',
                'h1.product-title',
                'h1',
                '.main-product-name'
            ]
            detailed_name = self._extract_text_by_selectors(soup, name_selectors)
            if detailed_name:
                detailed_product['name'] = detailed_name
                print(f"📝 Nome atualizado: {detailed_name[:50]}...")
            
            # Preço atual - SELETORES MELHORADOS
            price_selectors = [
                '.product-info-price .price-wrapper .price',
                '.product-info-main .price .price',
                '.price-box .regular-price .price',
                '.price-box .special-price .price',
                '.product-price .price',
                '[data-price-type="finalPrice"] .price',
                '.current-price'
            ]
            price_text = self._extract_text_by_selectors(soup, price_selectors)
            if price_text:
                detailed_product['price'] = self._parse_guarani_price(price_text)
                print(f"💰 Preço: {price_text}")
            
            # Preço original
            original_price_selectors = [
                '.price-box .old-price .price',
                '.price-box .regular-price .price',
                '[data-price-type="oldPrice"] .price',
                '.was-price'
            ]
            original_price_text = self._extract_text_by_selectors(soup, original_price_selectors)
            if original_price_text:
                detailed_product['original_price'] = self._parse_guarani_price(original_price_text)
            
            # DESCRIÇÃO DETALHADA - SELETORES MELHORADOS
            description_selectors = [
                '#product-description-content',
                '.product-info-detailed .product.attribute.description .value',
                '.product.attribute.description .value',
                '.product-description .value',
                '.description .std',
                '.product-collateral .std',
                '.product-tabs .description',
                '.tab-content .description'
            ]
            
            description_parts = []
            for selector in description_selectors:
                try:
                    desc_elem = soup.select_one(selector)
                    if desc_elem:
                        text = desc_elem.get_text(separator='\n', strip=True)
                        if text and len(text) > 20:
                            description_parts.append(text)
                except:
                    continue
            
            detailed_product['description'] = '\n\n'.join(description_parts[:3])  # Máximo 3 seções
            print(f"📝 Descrição: {len(detailed_product['description'])} caracteres")
            
            # CATEGORIAS - NOVO!
            categories = self._extract_product_categories(soup)
            detailed_product['categories'] = categories
            
            # URLs das imagens - MÉTODO MELHORADO
            image_urls = self._extract_product_image_urls(soup)
            detailed_product['image_urls'] = image_urls
            
            # Especificações técnicas - SELETORES MELHORADOS
            specs = self._extract_specifications_improved(soup)
            if specs:
                detailed_product['specifications'] = specs
            
            # Marca - SELETORES MELHORADOS
            brand_selectors = [
                '.product-info-main .product-brand',
                '.product-brand',
                '[itemprop="brand"]',
                '.manufacturer',
                '.brand-name'
            ]
            brand = self._extract_text_by_selectors(soup, brand_selectors)
            if brand:
                detailed_product['brand'] = brand
            
            # Disponibilidade
            stock_selectors = [
                '.product-info-stock-sku .stock span',
                '.availability',
                '.stock.available span',
                '.in-stock',
                '.product-availability'
            ]
            stock_text = self._extract_text_by_selectors(soup, stock_selectors)
            detailed_product['availability'] = stock_text if stock_text else 'Consultar disponibilidad'
            
            # Metadados
            detailed_product.update({
                'scraped_at': timezone.now().isoformat(),
                'site_id': self.site.id,
                'currency': self.currency,
                'country': 'Paraguay'
            })
            
            return detailed_product
            
        except Exception as e:
            print(f"❌ Erro ao extrair detalhes: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None

    def _is_product_related_image(self, url: str, img_element) -> bool:
        """Verifica se imagem genérica é relacionada ao produto"""
        url_lower = url.lower()
        
        # Deve ter extensão de imagem
        if not any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            return False
        
        # Indicadores positivos
        positive_indicators = [
            'product', 'catalog', 'media', 'gallery',
            'iphone', 'samsung', 'apple', 'lg', 'sony'
        ]
        
        # Indicadores negativos
        negative_indicators = [
            'logo', 'icon', 'sprite', 'badge', 'button',
            'arrow', 'star', 'cart', 'menu', 'banner',
            'footer', 'header', 'thumb', 'small'
        ]
        
        has_positive = any(indicator in url_lower for indicator in positive_indicators)
        has_negative = any(indicator in url_lower for indicator in negative_indicators)
        
        # Verificar dimensões do elemento se disponível
        width = img_element.get('width')
        height = img_element.get('height')
        
        if width and height:
            try:
                w, h = int(width), int(height)
                if w < 100 or h < 100:  # Muito pequena
                    return False
            except:
                pass
        
        return has_positive and not has_negative

    def _extract_product_image_urls(self, soup: BeautifulSoup) -> List[str]:
        """Extrai todas as URLs de imagens do produto - VERSÃO MELHORADA"""
        image_urls = set()
        
        print(f"🔍 Procurando imagens na página...")
        
        # Seletores específicos para diferentes estruturas de galeria
        gallery_selectors = [
            # Estruturas modernas de galeria
            '.product-image-gallery img',
            '.gallery-placeholder img',
            '.product-media-gallery img',
            '.fotorama img',
            '.slick-slide img',
            '.swiper-slide img',
            
            # Estruturas de zoom/lightbox
            'img[data-zoom-image]',
            'img[data-full]',
            'img[data-large]',
            '[data-gallery] img',
            
            # Estruturas Magento
            '.product.media img',
            '.product-image-main img',
            '.more-views img',
            
            # Estruturas genéricas
            '.gallery img',
            '.product-gallery img',
            '.images img',
            '.thumbnails img',
            
            # Fallback para imagens com produto no src
            'img[src*="product"]',
            'img[data-src*="product"]',
            'img[src*="catalog"]',
            'img[data-src*="catalog"]'
        ]
        
        for selector in gallery_selectors:
            try:
                images = soup.select(selector)
                print(f"  🎯 Seletor '{selector}': {len(images)} imagens")
                
                for img in images:
                    # Tentar diferentes atributos de fonte de imagem
                    source_attrs = [
                        'data-zoom-image',  # Imagem em alta resolução
                        'data-full',        # Imagem completa
                        'data-large',       # Imagem grande
                        'data-src',         # Lazy loading
                        'src',              # Fonte padrão
                        'data-original',    # Original
                        'data-lazy'         # Lazy load
                    ]
                    
                    for attr in source_attrs:
                        img_url = img.get(attr)
                        if img_url:
                            # Limpar e validar URL
                            img_url = img_url.strip()
                            
                            # Resolver URL absoluta
                            if img_url.startswith('//'):
                                full_url = f"https:{img_url}"
                            elif img_url.startswith('/'):
                                full_url = f"{self.base_url}{img_url}"
                            elif img_url.startswith('http'):
                                full_url = img_url
                            else:
                                full_url = urljoin(self.base_url, img_url)
                            
                            # Validar e adicionar
                            if self._is_valid_product_image_url(full_url):
                                image_urls.add(full_url)
                                print(f"    ✅ Imagem encontrada: {full_url}")
                            break
                            
            except Exception as e:
                print(f"  ❌ Erro com seletor '{selector}': {str(e)}")
                continue
        
        # Se não encontrou imagens específicas, buscar qualquer imagem da página
        if not image_urls:
            print(f"⚠️ Nenhuma imagem encontrada, tentando busca genérica...")
            all_images = soup.find_all('img')
            
            for img in all_images:
                src = img.get('src') or img.get('data-src')
                if src:
                    full_url = urljoin(self.base_url, src)
                    if self._is_product_related_image(full_url, img):
                        image_urls.add(full_url)
                        print(f"    📸 Imagem genérica: {full_url}")
        
        final_urls = list(image_urls)
        
        # ✅ APLICAR LIMITE AQUI TAMBÉM (opcional - para economizar processamento)
        final_urls = final_urls[:self.max_images_per_product]
        
        print(f"📊 Total de imagens selecionadas: {len(final_urls)} (máximo: {self.max_images_per_product})")
        
        return final_urls
    
    def _validate_image_content(self, content: bytes) -> bool:
        """Valida se o conteúdo é realmente uma imagem"""

        if not content or len(content) < 10:
            return False
        
        # ✅ Verificar assinaturas de arquivo de imagem
        image_signatures = {
            b'\xff\xd8\xff': 'JPEG',
            b'\x89PNG\r\n\x1a\n': 'PNG', 
            b'GIF87a': 'GIF',
            b'GIF89a': 'GIF',
            b'RIFF': 'WEBP',  # WEBP começa com RIFF
            b'BM': 'BMP'
        }
        
        for signature, format_name in image_signatures.items():
            if content.startswith(signature):
                print(f"    🔍 Formato detectado: {format_name}")
                return True
        
        print(f"    ⚠️ Assinatura não reconhecida: {content[:10]}")
        return False  # Se não reconhecer, melhor rejeitar

    def _extract_specifications(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extrai especificações técnicas do produto"""
        specs = {}
        
        # Seletores para tabelas de especificações
        spec_selectors = [
            '.additional-attributes-wrapper .data-table tr',
            '.product-specifications tr',
            '.product-attributes tr',
            '.data-table tr'
        ]
        
        for selector in spec_selectors:
            try:
                rows = soup.select(selector)
                for row in rows:
                    cells = row.select('td, th')
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value:
                            specs[key] = value
            except:
                continue
        
        return specs
    
    def _download_product_images(self, product_data: Dict) -> int:
        """Baixa todas as imagens do produto - VERSÃO CORRIGIDA"""
        image_urls = product_data.get('image_urls', [])
        if not image_urls:
            return 0
        
        downloaded_count = 0
        
        for i, img_url in enumerate(image_urls[:self.max_images_per_product]):
            try:
                print(f"  📸 Baixando imagem {i+1}/{min(len(image_urls), self.max_images_per_product)}: {img_url}")
                
                # ✅ CORREÇÃO 1: Headers específicos para imagens
                image_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    'Accept-Encoding': 'identity',  # ✅ Evitar compressão que pode causar problemas
                    'Connection': 'keep-alive'
                }
                
                # ✅ CORREÇÃO 2: Download com stream=True e sem encoding automático
                response = requests.get(
                    img_url, 
                    timeout=30, 
                    stream=True,
                    headers=image_headers,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # ✅ CORREÇÃO 3: Verificar content-type
                content_type = response.headers.get('content-type', '').lower()
                if not any(img_type in content_type for img_type in ['image/', 'jpeg', 'png', 'webp']):
                    print(f"    ⚠️ Content-type suspeito: {content_type}")
                    # Continuar mesmo assim, pode ser imagem válida
                
                # ✅ CORREÇÃO 4: Verificar tamanho antes de baixar tudo
                content_length = response.headers.get('content-length')
                if content_length:
                    size = int(content_length)
                    if size > self.max_image_size:
                        print(f"    ⚠️ Imagem muito grande: {size:,} bytes")
                        continue
                    if size < self.min_image_size:
                        print(f"    ⚠️ Imagem muito pequena: {size:,} bytes")
                        continue
                
                # ✅ CORREÇÃO 5: Ler conteúdo como bytes, NUNCA como texto
                try:
                    image_content = b''  # Inicializar como bytes
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # Filtrar chunks vazios
                            image_content += chunk
                    
                    print(f"    📥 Baixados {len(image_content):,} bytes")
                    
                except Exception as e:
                    print(f"    ❌ Erro ao ler conteúdo: {str(e)}")
                    continue
                
                # ✅ CORREÇÃO 6: Validar que é realmente uma imagem
                if not self._validate_image_content(image_content):
                    print(f"    ❌ Conteúdo não é uma imagem válida")
                    continue
                
                # ✅ CORREÇÃO 7: Processar imagem com tratamento de erro robusto
                processed_image = self._process_product_image_safe(image_content, img_url)
                if not processed_image:
                    print(f"    ❌ Falha ao processar imagem")
                    continue
                
                # Gerar nome único
                filename = self._generate_image_filename(product_data, i)
                
                # Salvar temporariamente na memória
                if 'processed_images' not in product_data:
                    product_data['processed_images'] = []
                
                product_data['processed_images'].append({
                    'content_base64': base64.b64encode(processed_image['content']).decode('utf-8'),
                    'filename': filename,
                    'original_url': img_url,
                    'width': processed_image['width'],
                    'height': processed_image['height'],
                    'is_main': i == 0,
                    'content_type': processed_image.get('content_type', 'image/jpeg')
                })
                
                downloaded_count += 1
                print(f"    ✅ Imagem processada ({processed_image['width']}x{processed_image['height']})")
                
                # Rate limiting
                time.sleep(1)
                # import json
                # print(json.dumps(processed_image['content'], default=str))  

                
            except requests.RequestException as e:
                print(f"    ❌ Erro de rede ao baixar imagem: {str(e)}")
                continue
            except UnicodeDecodeError as e:
                print(f"    ❌ Erro de encoding: {str(e)}")
                print(f"    🔧 Tentando método alternativo...")
                # Tentar método alternativo
                try:
                    alt_content = self._download_image_alternative(img_url)
                    if alt_content:
                        processed_image = self._process_product_image_safe(alt_content, img_url)
                        if processed_image:
                            # Adicionar imagem processada...
                            downloaded_count += 1
                except:
                    pass
                continue
            except Exception as e:
                print(f"    ❌ Erro geral ao baixar imagem: {str(e)}")
                continue
        
        return downloaded_count
    
    def _download_image_alternative(self, url: str) -> Optional[bytes]:
        """Método alternativo para download de imagens problemáticas"""
        try:
            print(f"    🔄 Tentando método alternativo...")
            
            # Usar urllib ao invés de requests
            import urllib.request
            
            # Criar request com headers
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read()
                
                if len(content) > self.min_image_size:
                    print(f"    ✅ Método alternativo funcionou: {len(content):,} bytes")
                    return content
            
            return None
            
        except Exception as e:
            print(f"    ❌ Método alternativo falhou: {str(e)}")
            return None

    def _process_product_image_safe(self, image_content: bytes, original_url: str) -> Optional[Dict[str, Any]]:
        """Processa imagem com tratamento de erro robusto"""
        try:
            # ✅ CORREÇÃO: Garantir que é bytes
            if not isinstance(image_content, bytes):
                print(f"    ❌ Conteúdo não é bytes: {type(image_content)}")
                return None
            
            print(f"    🔄 Processando {len(image_content):,} bytes...")
            
            # ✅ Criar BytesIO de forma segura
            image_buffer = BytesIO(image_content)
            
            # ✅ Abrir imagem com PIL de forma segura
            try:
                img = Image.open(image_buffer)
                img.verify()  # Verificar se é imagem válida
                
                # Reabrir após verify (verify fecha o arquivo)
                image_buffer.seek(0)
                img = Image.open(image_buffer)
                
            except Exception as e:
                print(f"    ❌ PIL não conseguiu abrir: {str(e)}")
                return None
            
            # Verificar dimensões mínimas
            width, height = img.size
            if width < 50 or height < 50:
                print(f"    ❌ Imagem muito pequena: {width}x{height}")
                return None
            
            print(f"    📐 Dimensões originais: {width}x{height}")
            
            # ✅ Converter para RGB se necessário (tratamento robusto)
            try:
                if img.mode not in ['RGB', 'L']:  # L = grayscale
                    if img.mode == 'RGBA':
                        # Criar fundo branco para transparência
                        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                        rgb_img.paste(img, mask=img.split()[-1])
                        img = rgb_img
                    elif img.mode == 'P':
                        # Paleta de cores
                        img = img.convert('RGBA')
                        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                        rgb_img.paste(img, mask=img.split()[-1] if len(img.split()) > 3 else None)
                        img = rgb_img
                    else:
                        # Outros modos
                        img = img.convert('RGB')
                        
            except Exception as e:
                print(f"    ⚠️ Erro na conversão, usando original: {str(e)}")
            
            # Redimensionar se muito grande
            max_dimension = 1200
            if width > max_dimension or height > max_dimension:
                print(f"    🔄 Redimensionando de {width}x{height}")
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                width, height = img.size
                print(f"    📐 Novas dimensões: {width}x{height}")
            
            # ✅ Salvar de forma segura
            output_buffer = BytesIO()
            
            try:
                # Salvar como JPEG com qualidade boa
                img.save(
                    output_buffer, 
                    format='JPEG', 
                    quality=85, 
                    optimize=True,
                    progressive=True  # JPEG progressivo
                )
                
                processed_content = output_buffer.getvalue()
                
                if not processed_content:
                    print(f"    ❌ Conteúdo processado vazio")
                    return None
                
                print(f"    ✅ Processada: {len(processed_content):,} bytes")
                
                return {
                    'content': processed_content,
                    'width': width,
                    'height': height,
                    'format': 'JPEG',
                    'content_type': 'image/jpeg'
                }
                
            except Exception as e:
                print(f"    ❌ Erro ao salvar imagem processada: {str(e)}")
                return None
            
        except Exception as e:
            print(f"    ❌ Erro geral no processamento: {str(e)}")
            import traceback
            print(f"    🔍 Traceback: {traceback.format_exc()}")
            return None
        
        finally:
            # ✅ Limpar buffers
            try:
                if 'image_buffer' in locals():
                    image_buffer.close()
                if 'output_buffer' in locals():
                    output_buffer.close()
            except:
                pass

    def _is_valid_image_signature(self, content: bytes) -> bool:
        """Verifica assinatura do arquivo para confirmar que é uma imagem válida"""
        if len(content) < 4:
            return False
        
        # Assinaturas de arquivos de imagem
        signatures = {
            b'\xFF\xD8\xFF': 'JPEG',
            b'\x89\x50\x4E\x47': 'PNG',
            b'\x47\x49\x46\x38': 'GIF',
            b'\x52\x49\x46\x46': 'WEBP',  # RIFF (pode ser WEBP)
            b'\x00\x00\x01\x00': 'ICO',
            b'\x42\x4D': 'BMP'
        }
        
        for signature, format_name in signatures.items():
            if content.startswith(signature):
                print(f"    ✅ Formato detectado: {format_name}")
                return True
        
        print(f"    ⚠️ Assinatura desconhecida: {content[:8].hex()}")
        return False

    def _process_product_image(self, image_content: bytes) -> Optional[Dict[str, Any]]:
        """Processa imagem com PIL"""
        try:
            # Abrir imagem
            img = Image.open(BytesIO(image_content))
            
            # Verificar dimensões mínimas
            width, height = img.size
            if width < 100 or height < 100:
                return None
            
            # Converter para RGB se necessário
            if img.mode in ['RGBA', 'P']:
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            # Redimensionar se muito grande
            max_dimension = 1200
            if width > max_dimension or height > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                width, height = img.size
            
            # Salvar otimizada
            output = BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            
            return {
                'content': output.getvalue(),
                'width': width,
                'height': height,
                'format': 'JPEG'
            }
            
        except Exception as e:
            return None
    
    def _generate_image_filename(self, product_data: Dict, index: int) -> str:
        """Gera nome único para imagem"""
        from django.utils.text import slugify
        
        name_slug = slugify(product_data['name'])[:30]
        unique_id = str(uuid.uuid4())[:8]
        
        return f"{name_slug}_{index+1}_{unique_id}.jpg"
    
    def _is_valid_product_image_url(self, url: str) -> bool:
        """Validação melhorada de URLs de imagem"""
        if not url or len(url) < 10:
            return False
        
        url_lower = url.lower()
        
        # Deve ter extensão de imagem
        if not any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
            return False
        
        # Indicadores positivos
        positive_indicators = [
            'product', 'catalog', 'media', 'gallery', 'image',
            '/m/', '/l/', '/xl/', 'large', 'full'
        ]
        
        # Indicadores negativos (mais específicos)
        negative_indicators = [
            'icon', 'logo', 'sprite', 'badge', 'button', 'star',
            'cart', 'arrow', 'loading', 'placeholder',
            'thumb', 'small', '50x50', '100x100', '150x150',
            'watermark', 'overlay'
        ]
        
        has_positive = any(indicator in url_lower for indicator in positive_indicators)
        has_negative = any(indicator in url_lower for indicator in negative_indicators)
        
        # Verificar dimensões na URL
        size_patterns = re.findall(r'(\d{2,4})x(\d{2,4})', url_lower)
        if size_patterns:
            width, height = map(int, size_patterns[0])
            if width < 200 or height < 200:  # Muito pequena
                return False
            if width > 2000 or height > 2000:  # Muito grande (pode ser original)
                return True
        
        return (has_positive or not has_negative) and not has_negative
    
    def _extract_text_by_selectors(self, soup, selectors: List[str]) -> str:
        """Extrai texto usando lista de seletores"""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(strip=True)
                    if text and len(text) > 1:
                        return text
            except:
                continue
        return ''
    
    def _parse_guarani_price(self, price_text: str) -> Optional[Decimal]:
        """Parse de preço em Guarani"""
        if not price_text:
            return None
        
        try:
            price_clean = re.sub(r'[^\d.,]', '', price_text)
            if not price_clean:
                return None
            
            if '.' in price_clean and ',' not in price_clean:
                price_clean = price_clean.replace('.', '')
            elif ',' in price_clean and '.' in price_clean:
                parts = price_clean.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    price_clean = parts[0].replace('.', '') + '.' + parts[1]
                else:
                    price_clean = price_clean.replace('.', '').replace(',', '')
            elif ',' in price_clean:
                parts = price_clean.split(',')
                if len(parts) == 2 and len(parts[1]) <= 2:
                    price_clean = parts[0] + '.' + parts[1]
                else:
                    price_clean = price_clean.replace(',', '')
            
            return Decimal(price_clean)
            
        except:
            return None

    def sanitize_for_json(obj):
        """
        Converte recursivamente objetos não-serializáveis para tipos JSON-safe.
        - bytes/bytearray/memoryview -> tenta decodificar utf-8, senão base64 string
        - datetime/date/time -> isoformat
        - Decimal -> float
        - UUID -> str
        - Mapping -> dict recursivo
        - list/tuple/set -> lista recursiva
        - Django QuerySet / Model -> tenta model_to_dict ou lista
        - fallback -> str(obj)
        """
        # tipos triviais
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj

        # bytes / bytearray / memoryview
        if isinstance(obj, (bytes, bytearray, memoryview)):
            b = bytes(obj)
            try:
                return b.decode('utf-8')
            except UnicodeDecodeError:
                return base64.b64encode(b).decode('ascii')

        # datetime / date / time
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            try:
                return obj.isoformat()
            except Exception:
                return str(obj)

        # Decimal
        if isinstance(obj, decimal.Decimal):
            try:
                return float(obj)
            except Exception:
                return str(obj)

        # UUID
        if isinstance(obj, uuid.UUID):
            return str(obj)

        # Mapping (dict-like)
        if isinstance(obj, Mapping):
            cleaned = {}
            for k, v in obj.items():
                # garantir chave como string
                key = str(k)
                cleaned[key] = sanitize_for_json(v)
            return cleaned

        # listas / tuplas / sets
        if isinstance(obj, (list, tuple, set)):
            return [sanitize_for_json(i) for i in obj]

        # Django QuerySet / Model
        try:
            from django.db.models import Model, QuerySet
            if isinstance(obj, QuerySet):
                return [sanitize_for_json(item) for item in list(obj)]
            if isinstance(obj, Model):
                try:
                    from django.forms.models import model_to_dict
                    return sanitize_for_json(model_to_dict(obj))
                except Exception:
                    # fallback: retornar PK ou str
                    try:
                        return sanitize_for_json(obj.pk)
                    except Exception:
                        return str(obj)
        except Exception:
            # Django não está disponível ou houve erro -> seguir
            pass

        # fallback geral
        try:
            return str(obj)
        except Exception:
            return repr(obj)


    def find_first_bad(obj, path="root"):
        """
        Tenta localizar o primeiro elemento que não é json-serializável (apenas para debug).
        Retorna uma tupla (path, tipo, repr_truncado, exception_str) ou None.
        """
        try:
            json.dumps(obj)
            return None
        except Exception as e:
            # se for dict
            if isinstance(obj, Mapping):
                for k, v in obj.items():
                    bad = find_first_bad(v, f"{path}.{k}")
                    if bad:
                        return bad
            elif isinstance(obj, (list, tuple)):
                for i, v in enumerate(obj):
                    bad = find_first_bad(v, f"{path}[{i}]")
                    if bad:
                        return bad
            else:
                return (path, type(obj).__name__, repr(obj)[:300], str(e))
        return None


    def scrape_products_with_limit(self, query: str, max_results: int = 20, max_detailed: int = 5) -> List[Dict[str, Any]]:
        """
        Scraping com limite separado para acessar detalhes — versão com sanitização recursiva.
        """
        try:
            print(f"🔍 SCRAPING COM LIMITE - Busca por '{query}' no Nissei.com")
            print(f"📋 Buscar na listagem: {max_results} produtos")
            print(f"🔎 Acessar detalhes de: {max_detailed} produtos")
            print("=" * 60)
            
            # FASE 1: Obter lista básica de produtos
            print("📋 FASE 1: Obtendo lista de produtos...")
            basic_products = self._get_basic_product_list(query, max_results)
            
            if not basic_products:
                print("❌ Nenhum produto encontrado na listagem")
                return []
            
            print(f"✅ {len(basic_products)} produtos encontrados na listagem")
            
            # ✅ APLICAR LIMITE PARA DETALHES
            products_for_details = basic_products[:max_detailed]
            
            print(f"🎯 Selecionados {len(products_for_details)} produtos para extração detalhada")
            print("=" * 60)
            
            # FASE 2: Processar apenas os produtos limitados
            print("🔎 FASE 2: Processando produtos selecionados individualmente...")
            detailed_products = []
            
            for i, basic_product in enumerate(products_for_details, 1):
                try:
                    print(f"\n📱 PRODUTO {i}/{len(products_for_details)}: {basic_product.get('name','')[:50]}...")
                    print(f"🌐 URL: {basic_product.get('url','')}")
                    
                    # Extrair detalhes do produto individual
                    detailed_product = self._extract_product_details(basic_product)
                    
                    if detailed_product:
                        detailed_products.append(detailed_product)
                        print(f"✅ Produto processado com sucesso")
                        
                        # Baixar imagens
                        print(f"📸 Baixando até {self.max_images_per_product} imagens...")
                        image_count = self._download_product_images(detailed_product)
                        print(f"📸 {image_count} imagens baixadas")
                    else:
                        print("❌ Falha ao processar produto")
                    
                    # Rate limiting entre produtos
                    if i < len(products_for_details):
                        print(f"⏱️ Aguardando {self.delay_between_products}s...")
                        time.sleep(self.delay_between_products)
                        
                except Exception as e:
                    print(f"❌ Erro ao processar produto {i}: {str(e)}")
                    continue
            
            # FASE 3: Adicionar produtos restantes SEM detalhes (apenas básicos)
            remaining_products = basic_products[max_detailed:]
            if remaining_products:
                print(f"\n📋 FASE 3: Adicionando {len(remaining_products)} produtos básicos (sem detalhes)...")
                
                for basic_product in remaining_products:
                    basic_product.update({
                        'scraped_at': timezone.now().isoformat(),
                        'site_id': self.site.id,
                        'currency': self.currency,
                        'country': 'Paraguay',
                        'details_extracted': False,
                        'description': 'Detalhes não extraídos - produto da listagem básica',
                        'categories': [],
                        'specifications': {},
                        'image_urls': [],
                        'processed_images': []
                    })
                    detailed_products.append(basic_product)  # agora dentro do loop
            
            # FASE 4: Salvar no banco de dados
            print(f"\n💾 FASE 4: Salvando {len(detailed_products)} produtos...")
            saved_count = self._save_products_with_details_flag(detailed_products)
            
            print(f"🎉 SCRAPING CONCLUÍDO!")
            print(f"📊 Total encontrados: {len(basic_products)}")
            print(f"🔎 Com detalhes extraídos: {len(products_for_details)}")
            print(f"📋 Apenas básicos: {len(remaining_products)}")
            print(f"💾 Produtos salvos: {saved_count}")
            
            # Montar response_data (igual ao que você já usa)
            response_data = {
                'query': query.strip(),
                'parameters': {
                    'max_results_requested': max_results,
                    'max_detailed_requested': max_detailed,
                    'max_images_per_product': self.max_images_per_product,
                    'actual_detailed_processed': len(detailed_products)
                },
                'site': {
                    'name': getattr(self.site, 'name', None),
                    'url': getattr(self.site, 'url', None),
                    'country': 'Paraguay'
                },
                'scraping_results': {
                    'products_with_details': len(detailed_products),
                    'products': detailed_products
                },
                'database_results': {
                    'saved_products_count': saved_count,
                    # Se você precisa do serializer aqui, deixe — vamos sanitizar tudo depois
                    'products': ProductSerializer(
                        Product.objects.filter(
                            search_query__icontains=query,
                            site=self.site,
                            status__in=[1, 2]
                        ).prefetch_related('images').order_by('-created_at')[:10],
                        many=True,
                        context={'request': None}
                    ).data
                },
                'currency': getattr(self, 'currency', 'Gs.'),
                'timestamp': timezone.now().isoformat(),
                'performance': {
                    'total_time_saved': f"Processou detalhes de apenas {len(detailed_products)} ao invés de {max_results} produtos",
                    'estimated_time': f"~{len(detailed_products) * 8} segundos ao invés de ~{max_results * 8} segundos"
                },
                'success': True
            }

            # FASE 5: Sanitizar recursivamente TODO response_data antes de retornar
            sanitized = sanitize_for_json(response_data)

            # Checagem extra: tentar serializar para JSON e, em caso de erro, imprimir diagnóstico
            try:
                json.dumps(sanitized)
            except Exception as e:
                print("❌ ERRO ao serializar response_data após sanitização:", str(e))
                bad = find_first_bad(sanitized)
                if bad:
                    print("🔍 Primeiro campo problemático encontrado:", bad)
                else:
                    print("🔍 Não foi possível localizar automaticamente o campo problemático.")
            
            return sanitized
            
        except Exception as e:
            print(f"❌ Erro geral no scraping com limite: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []


    def _save_products_with_details_flag(self, products: List[Dict[str, Any]]) -> int:
        """Salva produtos com flag indicando se tem detalhes extraídos"""
        saved_count = 0
        
        for product_data in products:
            try:
                has_details = product_data.get('details_extracted', True)
                
                # Verificar se produto já existe
                existing = Product.objects.filter(
                    url=product_data['url'],
                    site=self.site
                ).first()
                
                if existing:
                    # Atualizar apenas se tem detalhes OU se não tinha antes
                    if has_details or not existing.description:
                        existing.name = product_data['name'][:300]
                        existing.price = product_data.get('price')
                        existing.original_price = product_data.get('original_price')
                        if has_details:  # Só atualizar descrição se tem detalhes
                            existing.description = product_data.get('description', '')
                        existing.brand = product_data.get('brand', '')[:100] if product_data.get('brand') else None
                        existing.availability = product_data.get('availability', '')[:100]
                        existing.search_query = product_data.get('search_query', '')
                        existing.updated_at = timezone.now()
                        existing.save()
                    
                    product_obj = existing
                else:
                    # Criar novo produto
                    product_obj = Product.objects.create(
                        name=product_data['name'][:300],
                        price=product_data.get('price'),
                        original_price=product_data.get('original_price'),
                        description=product_data.get('description', ''),
                        url=product_data['url'],
                        brand=product_data.get('brand', '')[:100] if product_data.get('brand') else None,
                        availability=product_data.get('availability', '')[:100],
                        site=self.site,
                        search_query=product_data.get('search_query', ''),
                        status=1
                    )
                
                # Salvar imagens apenas se tem detalhes extraídos
                if has_details and 'processed_images' in product_data:
                    self._save_product_images(product_obj, product_data['processed_images'])
                
                saved_count += 1
                status_text = "completo" if has_details else "básico"
                print(f"💾 Produto salvo ({status_text}): {product_obj.name[:50]}...")
                
            except Exception as e:
                print(f"❌ Erro ao salvar produto: {str(e)}")
                continue
        
        return saved_count

    def debug_page_structure(self, soup: BeautifulSoup):
        """Método para debug - analisa estrutura da página"""
        print(f"\n🔍 DEBUG - ESTRUTURA DA PÁGINA")
        print("=" * 40)
        
        # Contar elementos importantes
        images = soup.find_all('img')
        print(f"📸 Total de imagens na página: {len(images)}")
        
        # Mostrar classes de imagem
        img_classes = set()
        for img in images[:20]:  # Primeiras 20
            classes = img.get('class', [])
            if classes:
                img_classes.update(classes)
        
        print(f"🏷️ Classes de imagem encontradas: {list(img_classes)[:10]}")
        
        # Procurar divs com 'gallery', 'image', 'photo'
        gallery_divs = soup.find_all('div', class_=lambda x: x and any(word in ' '.join(x) for word in ['gallery', 'image', 'photo', 'media']))
        print(f"🖼️ Divs relacionadas a galeria: {len(gallery_divs)}")
        
        for div in gallery_divs[:5]:
            classes = ' '.join(div.get('class', []))
            print(f"  📂 Classe: {classes}")
        
        # Procurar breadcrumbs
        breadcrumb_elements = soup.find_all(['nav', 'div', 'ol', 'ul'], class_=lambda x: x and 'breadcrumb' in ' '.join(x).lower())
        print(f"🗂️ Elementos breadcrumb: {len(breadcrumb_elements)}")

    def _save_detailed_products(self, products: List[Dict[str, Any]]) -> int:
        """Salva produtos detalhados no banco com imagens"""
        saved_count = 0
        
        for product_data in products:
            try:
                # Verificar se produto já existe
                existing = Product.objects.filter(
                    url=product_data['url'],
                    site=self.site
                ).first()
                
                if existing:
                    # Atualizar produto existente
                    existing.name = product_data['name'][:300]
                    existing.price = product_data.get('price')
                    existing.original_price = product_data.get('original_price')
                    existing.description = product_data.get('description', '')
                    existing.brand = product_data.get('brand', '')[:100] if product_data.get('brand') else None
                    existing.availability = product_data.get('availability', '')[:100]
                    existing.search_query = product_data.get('search_query', '')
                    existing.updated_at = timezone.now()
                    existing.save()
                    
                    product_obj = existing
                else:
                    # Criar novo produto
                    product_obj = Product.objects.create(
                        name=product_data['name'][:300],
                        price=product_data.get('price'),
                        original_price=product_data.get('original_price'),
                        description=product_data.get('description', ''),
                        url=product_data['url'],
                        brand=product_data.get('brand', '')[:100] if product_data.get('brand') else None,
                        availability=product_data.get('availability', '')[:100],
                        site=self.site,
                        search_query=product_data.get('search_query', ''),
                        status=1
                    )
                
                # Salvar imagens processadas
                if 'processed_images' in product_data:
                    self._save_product_images(product_obj, product_data['processed_images'])
                
                saved_count += 1
                print(f"💾 Produto salvo: {product_obj.name[:50]}...")
                
            except Exception as e:
                print(f"❌ Erro ao salvar produto: {str(e)}")
                continue
        
        return saved_count
    
    def _save_product_images(self, product: Product, processed_images: List[Dict]):
        """Salva imagens processadas no banco - VERSÃO CORRIGIDA"""
        try:
            # Remover imagens antigas se existirem
            ProductImage.objects.filter(product=product).delete()
            if product.main_image:
                try:
                    if hasattr(product.main_image, 'path') and os.path.exists(product.main_image.path):
                        os.remove(product.main_image.path)
                except:
                    pass
                product.main_image = None
            
            for i, img_data in enumerate(processed_images):
                try:
                    print(f"  💾 Salvando imagem {i+1}: {img_data['filename']}")
                    
                    # ✅ CORREÇÃO: Criar ContentFile de forma segura
                    content = img_data['content']
                    if not isinstance(content, bytes):
                        print(f"    ❌ Conteúdo não é bytes: {type(content)}")
                        continue
                    
                    # Criar arquivo Django com conteúdo binário
                    image_file = ContentFile(
                        content, 
                        name=img_data['filename']
                    )
                    
                    # ✅ Criar registro ProductImage
                    product_image = ProductImage.objects.create(
                        product=product,
                        image=image_file,
                        is_main=img_data.get('is_main', False),
                        alt_text=f"{product.name} - Imagem {i+1}",
                        order=i,
                        original_url=img_data['original_url']
                    )
                    
                    # Definir primeira imagem como principal
                    if i == 0:
                        product.main_image = product_image.image
                        product.save()
                    
                    print(f"    ✅ Imagem salva: {img_data['filename']}")
                    
                except Exception as e:
                    print(f"    ❌ Erro ao salvar imagem {i+1}: {str(e)}")
                    import traceback
                    print(f"    🔍 Traceback: {traceback.format_exc()}")
                    continue
                    
        except Exception as e:
            print(f"❌ Erro geral ao salvar imagens: {str(e)}")
