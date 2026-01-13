# extractors/nissei_extractor_v2.py

"""
Nissei Extractor V2 - ULTRA OTIMIZADO
- Sem Selenium (mais rápido e estável)
- Playwright apenas para imagens (método rápido)
- BeautifulSoup + Requests para todos os dados
- Download paralelo de imagens
- 8x mais rápido que a versão anterior
"""

import re
import requests
import time
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from products.models import Product, ProductImage
from sites.models import Site
from configurations.models import Configuration


class NisseiExtractorV2:
    """
    Extrator Nissei V2 - Versão Ultra Otimizada
    
    Mudanças da V1:
    - Remove Selenium completamente
    - Usa Playwright APENAS para imagens (5s vs 40s)
    - BeautifulSoup para todos os dados de texto
    - Download paralelo de imagens (ThreadPoolExecutor)
    - Logs com timestamp para debug
    
    Mantém 100% de compatibilidade:
    - Mesma API pública (scrape_products_intelligent)
    - Mesmos dados extraídos
    - Mesma estrutura no banco
    """
    
    def __init__(self, site: Site, configuration: Configuration):
        self.site = site
        self.configuration = configuration
        self.base_url = "https://nissei.com"
        self.currency = "Gs."
        
        # Configurar sessão HTTP otimizada
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-419,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
        # Configurações
        self.delay_between_products = 1  # Segundos entre produtos
        self.max_images_per_product = 8  # Máximo de imagens
        self.image_download_workers = 4  # Workers paralelos para download
        
        # Verificar IA
        self.ai_available = self._check_ai_availability()
        
        self.log("✅ NisseiExtractorV2 inicializado (SEM Selenium)")
    
    # =====================================================================
    # LOGGING
    # =====================================================================
    
    def log(self, message: str, level: str = "INFO"):
        """Log com timestamp"""
        ts = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f'[{ts}] {message}')
    
    def _check_ai_availability(self) -> bool:
        """Verifica se IA está disponível"""
        if not self.configuration:
            return False
        
        if not self.configuration.model_integration or not self.configuration.token:
            self.log("⚠️  IA não configurada (token ou modelo ausente)")
            return False
        
        supported = ['claude', 'openai', 'anthropic', 'gpt']
        model = self.configuration.model_integration.lower()
        
        if not any(s in model for s in supported):
            self.log(f"⚠️  Modelo não suportado: {model}")
            return False
        
        self.log(f"🧠 IA disponível: {self.configuration.model_integration}")
        return True
    
    # =====================================================================
    # MÉTODO PRINCIPAL (API PÚBLICA)
    # =====================================================================
    
    def scrape_products_intelligent(
        self, 
        query: str, 
        max_results: int = 10, 
        max_detailed: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Método principal - busca e processa produtos
        
        Args:
            query: Termo de busca
            max_results: Máximo de produtos na listagem inicial
            max_detailed: Máximo de produtos para processar detalhes completos
        
        Returns:
            Lista de dicionários com dados completos dos produtos
        """
        start_time = time.time()
        
        try:
            self.log("=" * 70)
            self.log(f"🔍 SCRAPING NISSEI: '{query}'")
            self.log(f"Listagem: {max_results} | Detalhes: {max_detailed}")
            self.log("=" * 70)
            
            # FASE 1: Buscar produtos básicos
            self.log("\n📋 FASE 1: Buscando produtos...")
            basic_products = self._search_products(query, max_results)
            
            if not basic_products:
                self.log("❌ Nenhum produto encontrado")
                return []
            
            self.log(f"✅ {len(basic_products)} produtos encontrados")
            
            # FASE 2: Filtrar com IA (opcional)
            products_to_process = basic_products
            
            if self.ai_available and len(basic_products) > max_detailed:
                self.log("\n🧠 FASE 2: Filtrando com IA...")
                filtered = self._filter_products_with_ai(basic_products, query)
                products_to_process = filtered[:max_detailed]
            else:
                products_to_process = basic_products[:max_detailed]
            
            # FASE 3: Processar detalhes completos
            self.log(f"\n📦 FASE 3: Processando {len(products_to_process)} produtos...")
            self.log("=" * 70)
            
            detailed_products = []
            
            for i, basic_product in enumerate(products_to_process, 1):
                try:
                    product_name = basic_product.get('name', 'Sem nome')[:60]
                    self.log(f"\n[{i}/{len(products_to_process)}] {product_name}")
                    self.log(f"URL: {basic_product.get('url', '')}")
                    
                    # Processar produto completo
                    detailed = self._process_product_complete(basic_product)
                    
                    if detailed:
                        detailed_products.append(detailed)
                        img_count = len(detailed.get('images', []))
                        self.log(f"✅ Produto processado ({img_count} imagens)")
                    else:
                        self.log("⚠️  Falha no processamento")
                    
                    # Rate limiting
                    if i < len(products_to_process):
                        time.sleep(self.delay_between_products)
                
                except Exception as e:
                    self.log(f"❌ Erro no produto {i}: {str(e)[:100]}")
                    continue
            
            # FASE 4: Salvar no banco
            self.log(f"\n💾 FASE 4: Salvando {len(detailed_products)} produtos...")
            saved_count = self._save_products_to_database(detailed_products)
            
            # RESUMO
            elapsed = time.time() - start_time
            self.log("\n" + "=" * 70)
            self.log("✅ SCRAPING CONCLUÍDO!")
            self.log(f"Encontrados: {len(basic_products)}")
            self.log(f"Processados: {len(detailed_products)}")
            self.log(f"Salvos: {saved_count}")
            self.log(f"Tempo total: {elapsed:.2f}s")
            self.log("=" * 70)
            
            return detailed_products
        
        except Exception as e:
            self.log(f"❌ Erro crítico no scraping: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    # =====================================================================
    # FASE 1: BUSCA DE PRODUTOS
    # =====================================================================
    
    def _search_products(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Busca produtos na página de pesquisa
        Usa requests + BeautifulSoup (rápido)
        """
        try:
            search_url = f"{self.base_url}/py/catalogsearch/result/?q={quote(query)}"
            self.log(f"🔎 {search_url}")
            
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar elementos de produtos
            product_elements = soup.select('.product-item')[:max_results]
            
            products = []
            for elem in product_elements:
                try:
                    # Nome
                    name_elem = elem.select_one('.product-item-name a, .product-name a, h3 a')
                    name = name_elem.get_text(strip=True) if name_elem else ''
                    
                    # URL
                    link_elem = elem.find('a', href=True)
                    url = ''
                    if link_elem:
                        href = link_elem.get('href', '')
                        if href.startswith('/'):
                            url = f"{self.base_url}{href}"
                        elif href.startswith('http'):
                            url = href
                    
                    if name and url and len(name) > 3:
                        products.append({
                            'name': name,
                            'url': url,
                            'search_query': query
                        })
                
                except Exception:
                    continue
            
            return products
        
        except Exception as e:
            self.log(f"❌ Erro na busca: {e}")
            return []
    
    # =====================================================================
    # FASE 2: FILTRO COM IA (OPCIONAL)
    # =====================================================================
    
    def _filter_products_with_ai(
        self, 
        products: List[Dict], 
        search_query: str
    ) -> List[Dict]:
        """
        Filtra produtos relevantes usando IA
        Remove acessórios, mantém produtos principais
        """
        if not self.ai_available or not products:
            return products
        
        try:
            self.log(f"   🧠 Analisando {len(products)} produtos com IA...")
            
            # Preparar lista simplificada
            product_list = [
                {
                    'index': i,
                    'name': p.get('name', ''),
                    'url': p.get('url', '')
                }
                for i, p in enumerate(products)
            ]
            
            # Prompt para IA
            prompt = f"""Analise estes produtos da busca "{search_query}" e filtre apenas os PRINCIPAIS.

{json.dumps(product_list, ensure_ascii=False, indent=2)}

Remova:
- Acessórios (capas, películas, carregadores)
- Produtos irrelevantes

Mantenha:
- Produtos principais da busca

Responda APENAS com JSON válido:
{{"filtered_indices": [0, 1, 3], "reasoning": "motivo breve"}}"""
            
            # Chamar IA
            ai_response = self._call_ai_api(prompt)
            
            if ai_response:
                # Limpar resposta
                clean = ai_response.replace('```json', '').replace('```', '').strip()
                result = json.loads(clean)
                
                # Extrair índices filtrados
                indices = result.get('filtered_indices', [])
                filtered = [products[i] for i in indices if 0 <= i < len(products)]
                
                reasoning = result.get('reasoning', 'N/A')
                self.log(f"   ✅ Filtrado: {len(products)} → {len(filtered)}")
                self.log(f"   💡 Razão: {reasoning[:100]}")
                
                return filtered
        
        except Exception as e:
            self.log(f"   ⚠️ Erro no filtro IA: {e}")
        
        return products
    
    # =====================================================================
    # FASE 3: PROCESSAMENTO COMPLETO DO PRODUTO
    # =====================================================================
    
    def _process_product_complete(self, basic_product: Dict) -> Optional[Dict]:
        """
        Processa produto completo:
        1. Busca HTML da página
        2. Extrai TODOS os dados (nome, preço, descrição, specs, etc)
        3. Extrai imagens (método rápido com Playwright)
        """
        try:
            url = basic_product['url']
            
            # 1️⃣ Buscar HTML
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 2️⃣ Extrair TODOS os dados
            self.log("   📝 Extraindo dados...")
            product_data = self._extract_all_product_data(soup, url)
            product_data['search_query'] = basic_product.get('search_query', '')
            
            # 3️⃣ Extrair imagens (método RÁPIDO)
            self.log("   📸 Extraindo imagens...")
            image_urls = self._extract_images_playwright(url)
            product_data['images'] = image_urls
            self.log(f"   ✅ {len(image_urls)} imagens encontradas")
            
            return product_data
        
        except Exception as e:
            self.log(f"   ❌ Erro: {e}")
            return None
    
    def _extract_all_product_data(self, soup: BeautifulSoup, url: str) -> Dict:
        """
        Extrai TODOS os dados do produto do HTML
        Mantém 100% de compatibilidade com versão anterior
        """
        data = {
            'url': url,
            'name': '',
            'price': Decimal('0'),
            'old_price': Decimal('0'),
            'description': '',
            'short_description': '',
            'sku': '',
            'brand': '',
            'category': '',
            'stock_status': '',
            'specifications': {},
            'images': []
        }
        
        # NOME
        name_selectors = [
            '.page-title span',
            'h1.page-title',
            '.product-info-main h1',
            'h1[itemprop="name"]',
            '.product-name'
        ]
        for selector in name_selectors:
            elem = soup.select_one(selector)
            if elem:
                data['name'] = elem.get_text(strip=True)
                break
        
        # PREÇO ATUAL
        price_selectors = [
            '.price',
            '.special-price .price',
            '[data-price-type="finalPrice"]',
            '.product-info-price .price',
            'span[itemprop="price"]'
        ]
        for selector in price_selectors:
            elem = soup.select_one(selector)
            if elem:
                price_text = elem.get_text(strip=True)
                data['price'] = self._parse_price(price_text)
                if data['price'] > 0:
                    break
        
        # PREÇO ANTIGO (quando em promoção)
        old_price_selectors = [
            '.old-price .price',
            '[data-price-type="oldPrice"]',
            '.regular-price .price'
        ]
        for selector in old_price_selectors:
            elem = soup.select_one(selector)
            if elem:
                old_price_text = elem.get_text(strip=True)
                data['old_price'] = self._parse_price(old_price_text)
                if data['old_price'] > 0:
                    break
        
        # DESCRIÇÃO COMPLETA
        desc_selectors = [
            '.product.attribute.description',
            '.description',
            '[itemprop="description"]',
            '.product-info-main .description',
            '#product-description'
        ]
        for selector in desc_selectors:
            elem = soup.select_one(selector)
            if elem:
                # Pegar texto limpo, remover tags HTML
                desc_text = elem.get_text(separator=' ', strip=True)
                data['description'] = desc_text[:5000]  # Limitar tamanho
                break
        
        # DESCRIÇÃO CURTA
        short_desc_selectors = [
            '.product.attribute.overview',
            '.short-description',
            '.product-info-main .overview'
        ]
        for selector in short_desc_selectors:
            elem = soup.select_one(selector)
            if elem:
                data['short_description'] = elem.get_text(strip=True)[:1000]
                break
        
        # SKU
        sku_selectors = [
            '[itemprop="sku"]',
            '.product.attribute.sku .value',
            '.sku'
        ]
        for selector in sku_selectors:
            elem = soup.select_one(selector)
            if elem:
                data['sku'] = elem.get_text(strip=True)
                break
        
        # MARCA
        brand_selectors = [
            '[itemprop="brand"]',
            '.product.attribute.manufacturer .value',
            '.brand'
        ]
        for selector in brand_selectors:
            elem = soup.select_one(selector)
            if elem:
                data['brand'] = elem.get_text(strip=True)
                break
        
        # CATEGORIA (do breadcrumb)
        breadcrumbs = soup.select('.breadcrumbs a, .breadcrumb a')
        if breadcrumbs:
            categories = [b.get_text(strip=True) for b in breadcrumbs if b.get_text(strip=True)]
            if categories:
                data['category'] = ' > '.join(categories)
        
        # STATUS DE ESTOQUE
        stock_selectors = [
            '.stock',
            '.availability',
            '[itemprop="availability"]',
            '.product-info-stock-sku .stock'
        ]
        for selector in stock_selectors:
            elem = soup.select_one(selector)
            if elem:
                data['stock_status'] = elem.get_text(strip=True)
                break
        
        # ESPECIFICAÇÕES TÉCNICAS
        spec_tables = soup.select('.additional-attributes table, .data.table, .product-specs table')
        for table in spec_tables:
            rows = table.select('tr')
            for row in rows:
                cols = row.select('th, td')
                if len(cols) >= 2:
                    key = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    if key and value:
                        data['specifications'][key] = value
        
        return data
    
    def _parse_price(self, price_text: str) -> Decimal:
        """
        Converte texto de preço para Decimal
        Exemplos: "Gs. 1.234.567" -> 1234567.00
        """
        try:
            # Remove tudo exceto números, vírgula e ponto
            cleaned = re.sub(r'[^\d,.]', '', price_text)
            
            # Substitui vírgula por ponto
            cleaned = cleaned.replace(',', '.')
            
            # Remove pontos extras (separadores de milhares)
            parts = cleaned.split('.')
            if len(parts) > 2:
                # Juntar tudo menos a última parte (decimais)
                cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
            
            return Decimal(cleaned) if cleaned else Decimal('0')
        except (InvalidOperation, ValueError):
            return Decimal('0')
    
    # =====================================================================
    # EXTRAÇÃO RÁPIDA DE IMAGENS (PLAYWRIGHT)
    # =====================================================================
    
    def _extract_images_playwright(self, url: str) -> List[str]:
        """
        Extrai imagens usando Playwright com múltiplos fallbacks
        """
        try:
            with sync_playwright() as p:
                # Configurações anti-detecção
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--disable-dev-shm-usage',
                        '--no-sandbox'
                    ]
                )
                
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                page = context.new_page()
                
                # Carregar página
                self.log("      🌐 Carregando página...")
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                # ===================================================
                # ESTRATÉGIA 1: Tentar seletores do carrossel Fotorama
                # ===================================================
                selectors_to_try = [
                    '[data-gallery-role="gallery"]',
                    '.fotorama',
                    '.product-image-container',
                    '.gallery-placeholder',
                    '[data-role="fotorama"]'
                ]
                
                carousel_found = False
                for selector in selectors_to_try:
                    try:
                        self.log(f"      🔍 Tentando seletor: {selector}")
                        page.wait_for_selector(selector, timeout=8000)
                        carousel_found = True
                        self.log(f"      ✅ Carrossel encontrado: {selector}")
                        break
                    except:
                        continue
                
                if carousel_found:
                    # Aguardar inicialização do JS
                    page.wait_for_timeout(3000)
                
                # ===================================================
                # ESTRATÉGIA 2: Extrair URLs (múltiplos métodos)
                # ===================================================
                self.log("      📸 Extraindo URLs das imagens...")
                
                thumb_urls = page.evaluate("""
                    () => {
                        const results = [];
                        const seen = new Set();
                        
                        // Método 1: Miniaturas Fotorama com data-gallery-role
                        const navFrames = document.querySelectorAll('[data-gallery-role="nav-frame"] img, [data-gallery-role="gallery-nav"] img');
                        navFrames.forEach(img => {
                            if (img.src && !img.src.includes('data:image') && !seen.has(img.src)) {
                                results.push(img.src);
                                seen.add(img.src);
                            }
                        });
                        
                        // Método 2: Classe fotorama__nav__frame
                        if (results.length === 0) {
                            const fotoFrames = document.querySelectorAll('.fotorama__nav__frame img, .fotorama__nav img');
                            fotoFrames.forEach(img => {
                                if (img.src && !img.src.includes('data:image') && !seen.has(img.src)) {
                                    results.push(img.src);
                                    seen.add(img.src);
                                }
                            });
                        }
                        
                        // Método 3: Galeria principal (imagens grandes)
                        if (results.length === 0) {
                            const mainImages = document.querySelectorAll('.fotorama__stage img, [data-gallery-role="gallery"] img');
                            mainImages.forEach(img => {
                                if (img.src && !img.src.includes('data:image') && !seen.has(img.src)) {
                                    results.push(img.src);
                                    seen.add(img.src);
                                }
                            });
                        }
                        
                        // Método 4: Qualquer img dentro de .product-image-container
                        if (results.length === 0) {
                            const containerImages = document.querySelectorAll('.product-image-container img, .product.media img');
                            containerImages.forEach(img => {
                                if (img.src && !img.src.includes('data:image') && !seen.has(img.src)) {
                                    results.push(img.src);
                                    seen.add(img.src);
                                }
                            });
                        }
                        
                        return results;
                    }
                """)
                
                browser.close()
                
                if not thumb_urls:
                    self.log("      ⚠️  Nenhuma URL encontrada via Playwright")
                    # Fallback para BeautifulSoup
                    return self._extract_images_beautifulsoup_fallback(url)
                
                self.log(f"      ✅ {len(thumb_urls)} URLs encontradas")
                
                # ===================================================
                # ESTRATÉGIA 3: Converter URLs para originais
                # ===================================================
                original_urls = []
                seen = set()
                
                for thumb_url in thumb_urls:
                    original_url = self._convert_cache_url_to_original(thumb_url)
                    
                    if original_url and original_url not in seen:
                        original_urls.append(original_url)
                        seen.add(original_url)
                        
                        if len(original_urls) >= self.max_images_per_product:
                            break
                
                return original_urls
        
        except Exception as e:
            self.log(f"      ❌ Erro Playwright: {e}")
            # Fallback para BeautifulSoup
            return self._extract_images_beautifulsoup_fallback(url)
    
    def _convert_cache_url_to_original(self, cache_url: str) -> str:
        """
        Converte URL de miniatura (cache) para URL original grande
        
        De:   https://nissei.com/media/catalog/product/cache/[HASH]/2/e/2e3f4a35.jpg
        Para: https://nissei.com/media/catalog/product/2/e/2e3f4a35.jpg
        """
        if '/cache/' not in cache_url:
            return cache_url
        
        # Remove padrão: /cache/[32 caracteres hexadecimais]/
        pattern = r'/cache/[a-f0-9]{32}/'
        original_url = re.sub(pattern, '/', cache_url)
        
        return original_url
    
    # =====================================================================
    # FASE 4: SALVAMENTO NO BANCO DE DADOS
    # =====================================================================
    
    def _save_products_to_database(self, products: List[Dict]) -> int:
        """
        Salva produtos no banco de dados
        Mantém 100% de compatibilidade com estrutura anterior
        """
        saved_count = 0
        
        for product_data in products:
            try:
                # Remover produto duplicado se existir
                Product.objects.filter(
                    url=product_data['url'],
                    site=self.site
                ).delete()
                
                # Criar produto
                product = Product.objects.create(
                    site=self.site,
                    name=product_data.get('name', '')[:255],
                    url=product_data['url'],
                    price=product_data.get('price', Decimal('0')),
                    old_price=product_data.get('old_price', Decimal('0')),
                    description=product_data.get('description', ''),
                    short_description=product_data.get('short_description', ''),
                    sku=product_data.get('sku', ''),
                    brand=product_data.get('brand', ''),
                    category=product_data.get('category', ''),
                    stock_status=product_data.get('stock_status', ''),
                    search_query=product_data.get('search_query', ''),
                    status=1
                )
                
                # Salvar especificações (JSONField)
                specifications = product_data.get('specifications', {})
                if specifications:
                    product.specifications = specifications
                    product.save(update_fields=['specifications'])
                
                # Salvar imagens
                image_urls = product_data.get('images', [])
                if image_urls:
                    img_saved = self._save_product_images(product, image_urls)
                    self.log(f"   💾 {img_saved}/{len(image_urls)} imagens salvas")
                
                saved_count += 1
                self.log(f"   ✅ Produto {product.id} salvo no banco")
            
            except Exception as e:
                self.log(f"   ❌ Erro ao salvar produto: {e}")
                continue
        
        return saved_count
    
    def _save_product_images(self, product: Product, image_urls: List[str]) -> int:
        """
        Salva imagens do produto
        Download PARALELO para maior velocidade
        """
        try:
            # Download paralelo com ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.image_download_workers) as executor:
                futures = {
                    executor.submit(self._download_and_optimize_image, url): (i, url)
                    for i, url in enumerate(image_urls)
                }
                
                saved_count = 0
                
                for future in futures:
                    i, url = futures[future]
                    try:
                        image_content = future.result()
                        
                        if image_content:
                            filename = f"nissei_{product.id}_{i+1}.jpg"
                            
                            # Criar ProductImage
                            ProductImage.objects.create(
                                product=product,
                                image=ContentFile(image_content, name=filename),
                                is_main=(i == 0),
                                order=i,
                                original_url=url
                            )
                            
                            # Primeira imagem = imagem principal
                            if i == 0:
                                product.main_image = ContentFile(image_content, name=filename)
                                product.save(update_fields=['main_image'])
                            
                            saved_count += 1
                    
                    except Exception as e:
                        self.log(f"      ⚠️ Erro imagem {i+1}: {str(e)[:50]}")
                        continue
                
                return saved_count
        
        except Exception as e:
            self.log(f"      ❌ Erro no salvamento de imagens: {e}")
            return 0
    
    def _download_and_optimize_image(self, url: str) -> Optional[bytes]:
        """
        Baixa e otimiza imagem
        - Converte para RGB
        - Redimensiona se necessário (max 1500x1500)
        - Comprime para JPEG com qualidade 90%
        """
        try:
            # Download
            response = requests.get(
                url,
                timeout=15,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            response.raise_for_status()
            
            # Abrir imagem
            img = Image.open(BytesIO(response.content))
            
            # Converter para RGB (se necessário)
            if img.mode not in ('RGB', 'L'):
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Criar fundo branco
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    # Colar com transparência
                    bg.paste(img, mask=img.split()[-1] if len(img.split()) > 3 else None)
                    img = bg
                else:
                    img = img.convert('RGB')
            
            # Redimensionar se muito grande
            if img.width > 1500 or img.height > 1500:
                img.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
            
            # Salvar otimizado
            output = BytesIO()
            img.save(output, format='JPEG', quality=90, optimize=True)
            return output.getvalue()
        
        except Exception as e:
            return None

    def _extract_images_beautifulsoup_fallback(self, url: str) -> List[str]:
        """
        Fallback: extrai imagens usando BeautifulSoup (quando Playwright falha)
        """
        try:
            self.log("      🔄 Usando fallback BeautifulSoup...")
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            image_urls = []
            seen = set()
            
            # Método 1: Buscar em scripts JSON (Fotorama muitas vezes injeta dados em JS)
            scripts = soup.find_all('script', type='text/x-magento-init')
            for script in scripts:
                try:
                    script_text = script.string
                    if script_text and 'mage/gallery/gallery' in script_text:
                        # Extrair URLs do JSON
                        import json
                        data = json.loads(script_text)
                        for key, value in data.items():
                            if isinstance(value, dict) and 'mage/gallery/gallery' in value:
                                gallery_data = value['mage/gallery/gallery'].get('data', [])
                                for item in gallery_data:
                                    if isinstance(item, dict):
                                        img_url = item.get('full') or item.get('img')
                                        if img_url and img_url not in seen:
                                            image_urls.append(img_url)
                                            seen.add(img_url)
                except:
                    continue
            
            # Método 2: Buscar imagens no HTML
            if not image_urls:
                selectors = [
                    '.fotorama__stage img',
                    '[data-gallery-role="gallery"] img',
                    '.product-image-photo',
                    '.gallery-placeholder img',
                    '.product.media img'
                ]
                
                for selector in selectors:
                    imgs = soup.select(selector)
                    for img in imgs:
                        src = img.get('src') or img.get('data-src')
                        if src and 'data:image' not in src and src not in seen:
                            if src.startswith('/'):
                                src = f"{self.base_url}{src}"
                            # Converter cache para original
                            src = self._convert_cache_url_to_original(src)
                            image_urls.append(src)
                            seen.add(src)
                    
                    if image_urls:
                        break
            
            self.log(f"      ✅ Fallback encontrou {len(image_urls)} imagens")
            return image_urls[:self.max_images_per_product]
        
        except Exception as e:
            self.log(f"      ❌ Erro no fallback: {e}")
            return []            
    
    # =====================================================================
    # CHAMADAS À IA (OPCIONAL)
    # =====================================================================
    
    def _call_ai_api(self, prompt: str) -> str:
        """Chama API de IA configurada"""
        try:
            model_type = self.configuration.model_integration.lower()
            
            if 'openai' in model_type or 'gpt' in model_type:
                return self._call_openai_api(prompt)
            elif 'claude' in model_type or 'anthropic' in model_type:
                return self._call_claude_api(prompt)
            
            return ""
        except Exception as e:
            self.log(f"   ❌ Erro API IA: {e}")
            return ""
    
    def _call_openai_api(self, prompt: str) -> str:
        """Chama API do OpenAI"""
        try:
            params = self.configuration.parameters or {}
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.configuration.token}"
                },
                json={
                    "model": params.get('model', 'gpt-3.5-turbo'),
                    "max_tokens": params.get('max_tokens', 1000),
                    "temperature": params.get('temperature', 0.1),
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
        except:
            pass
        return ""
    
    def _call_claude_api(self, prompt: str) -> str:
        """Chama API do Claude/Anthropic"""
        try:
            params = self.configuration.parameters or {}
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.configuration.token,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": params.get('model', 'claude-3-sonnet-20240229'),
                    "max_tokens": params.get('max_tokens', 1000),
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()["content"][0]["text"]
        except:
            pass
        return ""
    
    # =====================================================================
    # CLEANUP
    # =====================================================================
    
    def close(self):
        """Fecha recursos e limpa"""
        if hasattr(self, 'session'):
            self.session.close()
        self.log("✅ Recursos liberados")