import base64
import os
import re
import requests
import time
import json
import uuid
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
from django.conf import settings

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains

from products.models import Product, ProductImage
from sites.models import Site
from configurations.models import Configuration


class AISeleniumNisseiScraper:
    """
    Scraper refatorado - apenas o essencial que funciona
    Baseado no teste que funciona corretamente
    """
    
    def __init__(self, site: Site, configuration: Configuration):
        self.site = site
        self.configuration = configuration
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
        
        # Configurações simplificadas
        self.delay_between_products = 2
        self.max_images_per_product = 8  # Aumentado para pegar mais imagens
        
        # Configurar Selenium
        self.driver = None
        self.setup_selenium()
        
        # Verificar se IA está disponível
        self.ai_available = self._check_ai_availability()
    
    def _check_ai_availability(self) -> bool:
        """Verifica se a configuração de IA está válida"""
        if not self.configuration:
            return False
        
        required_fields = ['model_integration', 'token']
        for field in required_fields:
            if not getattr(self.configuration, field, None):
                print(f"Configuração inválida: campo '{field}' não definido")
                return False
        
        supported_models = ['claude', 'openai', 'anthropic']
        model_type = self.configuration.model_integration.lower()
        
        if not any(supported in model_type for supported in supported_models):
            print(f"Modelo não suportado: {self.configuration.model_integration}")
            return False
        
        print(f"IA configurada: {self.configuration.model_integration}")
        return True
    
    def setup_selenium(self):
        """Setup do Selenium - igual ao teste que funciona"""
        try:
            chrome_options = Options()
            
            # Configurações básicas
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--disable-default-apps')
            
            # Configurações para evitar detecção
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # User agent
            chrome_options.add_argument(
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Timeouts
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            # Remover detecção de automação
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            print("✅ Selenium configurado")
            
        except Exception as e:
            print(f"❌ Erro ao configurar Selenium: {e}")
            self.driver = None

    # ===== MÉTODO PRINCIPAL SIMPLIFICADO =====
    
    def scrape_products_intelligent(self, query: str, max_results: int = 10, max_detailed: int = 5) -> List[Dict[str, Any]]:
        """Método principal simplificado"""
        try:
            print(f"SCRAPING SIMPLIFICADO com {self.configuration.model_integration}")
            print(f"Busca: '{query}' | Max listagem: {max_results} | Max detalhes: {max_detailed}")
            print("=" * 70)
            
            # FASE 1: Obter lista básica de produtos
            print("FASE 1: Obtendo lista de produtos...")
            basic_products = self._get_basic_product_list(query, max_results)
            
            if not basic_products:
                print("Nenhum produto encontrado na listagem")
                return []
            
            print(f"{len(basic_products)} produtos encontrados na listagem")
            
            # FASE 2: Filtrar com IA se disponível
            if self.ai_available:
                print("FASE 2: Filtrando produtos relevantes com IA...")
                filtered_products = self._filter_products_with_ai(basic_products, query)
            else:
                filtered_products = basic_products
            
            # FASE 3: Processar produtos com detalhes
            products_for_details = filtered_products[:max_detailed]
            print(f"Processando {len(products_for_details)} produtos com detalhes")
            print("=" * 70)
            
            detailed_products = []
            
            for i, basic_product in enumerate(products_for_details, 1):
                try:
                    print(f"\nPRODUTO {i}/{len(products_for_details)}: {basic_product.get('name', '')[:50]}...")
                    print(f"URL: {basic_product.get('url', '')}")
                    
                    # Processar produto (versão simplificada)
                    detailed_product = self._process_product_simple(basic_product)
                    
                    if detailed_product:
                        detailed_products.append(detailed_product)
                        print(f"Produto processado com sucesso")
                        
                        # Baixar imagens usando método do teste
                        print(f"Baixando imagens...")
                        image_count = self._download_product_images(detailed_product)
                        print(f"{image_count} imagens baixadas")
                    else:
                        print("Falha ao processar produto")
                    
                    # Rate limiting
                    if i < len(products_for_details):
                        print(f"Aguardando {self.delay_between_products}s...")
                        time.sleep(self.delay_between_products)
                        
                except Exception as e:
                    print(f"Erro ao processar produto {i}: {str(e)}")
                    continue
            
            # FASE 4: Salvar no banco
            print(f"\nFASE 4: Salvando {len(detailed_products)} produtos...")
            saved_count = self._save_products(detailed_products)
            
            print(f"SCRAPING CONCLUÍDO!")
            print(f"Total encontrados: {len(basic_products)}")
            print(f"Processados: {len(detailed_products)}")
            print(f"Produtos salvos: {saved_count}")
            
            return detailed_products
            
        except Exception as e:
            print(f"Erro geral no scraping: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []
        finally:
            self._cleanup_selenium()

    # ===== PROCESSAMENTO SIMPLIFICADO =====
    
    def _process_product_simple(self, basic_product: Dict) -> Optional[Dict[str, Any]]:
        """Processamento simplificado de produto"""
        product_url = basic_product['url']
        
        # Estratégia 1: Requests para dados básicos
        print("📡 Extraindo dados básicos...")
        basic_data = self._extract_basic_data_from_url(product_url)
        
        # Estratégia 2: SEMPRE usar Selenium para imagens do carrossel
        print("🎠 Extraindo imagens do carrossel com Selenium...")
        carousel_images = self._extract_carousel_images_like_test(product_url)
        
        # Combinar resultados
        result = basic_product.copy()
        result.update(basic_data)
        
        if carousel_images:
            result['image_urls'] = carousel_images
            print(f"✅ {len(carousel_images)} imagens do carrossel extraídas")
        else:
            print("⚠️ Nenhuma imagem do carrossel extraída")
        
        # Adicionar metadados
        result.update({
            'scraped_at': timezone.now().isoformat(),
            'site_id': self.site.id,
            'currency': self.currency,
            'country': 'Paraguay',
            'details_extracted': True,
            'extraction_method': 'simplified_carousel'
        })
        
        return result
    
    def _extract_basic_data_from_url(self, url: str) -> Dict[str, Any]:
        """Extração básica de dados via requests"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            data = {}
            
            # Nome
            name_selectors = ['h1.page-title span', 'h1.page-title', 'h1']
            name = self._extract_text_by_selectors(soup, name_selectors)
            if name:
                data['name'] = name
            
            # Preço
            price_selectors = ['.price-wrapper .price', '.price-box .price', '[class*="price"]']
            price_text = self._extract_text_by_selectors(soup, price_selectors)
            if price_text:
                data['price'] = self._parse_guarani_price(price_text)
            
            # SKU
            sku_code = self._extract_sku_code(soup)
            if sku_code:
                data['sku_code'] = sku_code
            
            # Descrição (Más Información prioritária)
            description = self._extract_description_simple(soup)
            if description:
                data['description'] = description
            
            return data
            
        except Exception as e:
            print(f"Erro na extração básica: {e}")
            return {}
    
    def _extract_carousel_images_like_test(self, url: str) -> List[str]:
        """
        MÉTODO PRINCIPAL: Extrai imagens exatamente como no teste que funciona
        """
        if not self.driver:
            print("❌ Selenium não disponível")
            return []
        
        try:
            print(f"🎠 Acessando página para extrair carrossel: {url}")
            
            # Acessar página
            self.driver.get(url)
            
            # Aguardar carregamento (igual ao teste)
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)  # Mesmo timing do teste
            
            all_images = []
            
            # PASSO 1: Aguardar carrossel carregar
            print("⏳ Aguardando carrossel carregar...")
            carousel_loaded = self._wait_for_carousel_loading()
            if not carousel_loaded:
                print("⚠️ Carrossel não detectado")
                return []
            
            # PASSO 2: Capturar imagem inicial
            print("📸 Capturando imagem inicial...")
            initial_image = self._get_current_carousel_image()
            if initial_image:
                all_images.append(initial_image)
                print(f"   ✅ Inicial: {initial_image[:60]}...")
            
            # PASSO 3: Encontrar botões de navegação
            print("🔍 Procurando botões de navegação...")
            next_buttons = self._find_next_buttons()
            
            if not next_buttons:
                print("   ⚠️ Nenhum botão encontrado")
                return all_images
            
            print(f"   ✅ {len(next_buttons)} botão(ões) encontrado(s)")
            
            # PASSO 4: Navegar pelo carrossel (igual ao teste)
            print("🔄 Navegando pelo carrossel...")
            navigation_images = self._navigate_carousel_unlimited(next_buttons[0])
            
            # Adicionar imagens únicas
            for img in navigation_images:
                if img and img not in all_images:
                    all_images.append(img)
            
            # Limitar resultado
            final_images = all_images[:self.max_images_per_product]
            print(f"🎯 RESULTADO: {len(final_images)} imagens extraídas")
            
            return final_images
            
        except Exception as e:
            print(f"❌ Erro na extração do carrossel: {e}")
            return []

    # ===== MÉTODOS DO CARROSSEL (COPIADOS DO TESTE) =====
    
    def _wait_for_carousel_loading(self) -> bool:
        """Aguarda carrossel carregar - igual ao teste"""
        try:
            fotorama_selectors = [
                '.fotorama__stage',
                '.fotorama__nav', 
                '[data-fotorama]',
                '.fotorama'
            ]
            
            for selector in fotorama_selectors:
                try:
                    WebDriverWait(self.driver, 8).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"   ✅ Fotorama detectado: {selector}")
                    time.sleep(3)  # Aguardar JS
                    return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"   ❌ Erro ao detectar carrossel: {e}")
            return False
    
    def _get_current_carousel_image(self) -> Optional[str]:
        """Obtém imagem atual do carrossel - igual ao teste"""
        selectors = [
            '.fotorama__stage__frame.fotorama__active img',
            '.fotorama__img',
            '.fotorama__stage img',
            '.product-image-main img',
            '.main-image img',
            '.product-gallery img:first-child',
            'img[src*="catalog"]:first-of-type'
        ]
        
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        size = element.size
                        if size.get('width', 0) > 200 and size.get('height', 0) > 200:
                            for attr in ['data-zoom-image', 'data-large-image', 'data-src', 'src']:
                                url = element.get_attribute(attr)
                                if url and self._is_valid_product_image_url(url):
                                    return self._resolve_image_url(url)
            except:
                continue
        
        return None
    
    def _find_next_buttons(self) -> List:
        """Encontra botões de navegação - igual ao teste"""
        selectors = [
            '.fotorama__arr--next',
            '.fotorama__arr[data-side="next"]',
            '.carousel-control-next',
            '.slick-next',
            '.swiper-button-next',
            'button[class*="next"]',
            'button[aria-label*="next"]',
            'button[title*="next"]'
        ]
        
        found_buttons = []
        
        for selector in selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        classes = (button.get_attribute('class') or '').lower()
                        aria = (button.get_attribute('aria-label') or '').lower()
                        
                        if any(word in classes + aria for word in ['prev', 'previous', 'back']):
                            continue
                        
                        found_buttons.append(button)
                        print(f"   Botão encontrado: {selector}")
                        break
                        
            except Exception as e:
                continue
        
        # Remover duplicatas por posição
        unique_buttons = []
        for button in found_buttons:
            try:
                location = button.location
                if not any(btn.location == location for btn in unique_buttons):
                    unique_buttons.append(button)
            except:
                unique_buttons.append(button)
        
        return unique_buttons
    
    def _navigate_carousel_unlimited(self, next_button) -> List[str]:
        """Navega pelo carrossel - igual ao teste"""
        navigation_images = []
        consecutive_failures = 0
        max_failures = 3
        max_clicks = self.max_images_per_product
        
        print(f"🔄 Navegando: máx {max_clicks} cliques")
        
        for click_num in range(max_clicks):
            try:
                if not next_button.is_displayed() or not next_button.is_enabled():
                    print(f"   Botão indisponível no clique {click_num + 1}")
                    break
                
                # Capturar imagem antes
                image_before = self._get_current_carousel_image()
                
                # Scroll e click
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(1)
                
                clicked = self._click_button_robust(next_button)
                if not clicked:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        break
                    continue
                
                # Aguardar transição
                time.sleep(2)
                
                # Capturar nova imagem
                image_after = self._get_current_carousel_image()
                
                if image_after and image_after != image_before:
                    if image_after not in navigation_images:
                        navigation_images.append(image_after)
                        consecutive_failures = 0
                        print(f"   ✅ Clique {click_num + 1}: nova imagem")
                    else:
                        consecutive_failures += 1
                        print(f"   ⚠️ Clique {click_num + 1}: imagem duplicada")
                elif image_after == image_before:
                    consecutive_failures += 1
                    print(f"   ⚠️ Clique {click_num + 1}: sem mudança")
                else:
                    consecutive_failures += 1
                    print(f"   ❌ Clique {click_num + 1}: erro ao capturar")
                
                if consecutive_failures >= max_failures:
                    print(f"   Parando: {max_failures} falhas consecutivas")
                    break
                    
            except Exception as e:
                consecutive_failures += 1
                print(f"   ❌ Erro no clique {click_num + 1}: {str(e)[:50]}")
                if consecutive_failures >= max_failures:
                    break
        
        print(f"   Resultado: {len(navigation_images)} imagens via navegação")
        return navigation_images
    
    def _click_button_robust(self, button) -> bool:
        """Clique robusto - igual ao teste"""
        strategies = [
            lambda: button.click(),
            lambda: self.driver.execute_script("arguments[0].click();", button),
            lambda: ActionChains(self.driver).move_to_element(button).click().perform()
        ]
        
        for strategy in strategies:
            try:
                strategy()
                return True
            except:
                continue
        
        return False

    # ===== MÉTODOS AUXILIARES ESSENCIAIS =====
    
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
    
    def _extract_sku_code(self, soup: BeautifulSoup) -> Optional[str]:
        """Extrai código SKU"""
        sku_patterns = [
            r'SKU[:\s]+([A-Z]{1,5}-\d{4,10})',
            r'SKU[:\s]+([A-Z0-9-]{5,15})',
            r'Código[:\s]+([A-Z]{1,5}-\d{4,10})',
        ]
        
        # Buscar em todo texto da página
        try:
            full_text = soup.get_text()
            for pattern in sku_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    sku_code = match.group(1).strip().upper()
                    print(f"✅ SKU encontrado: {sku_code}")
                    return sku_code
        except:
            pass
        
        return None
    
    def _extract_description_simple(self, soup: BeautifulSoup) -> str:
        """Extração simplificada de descrição"""
        # Prioridade para "Más Información"
        mas_info_selectors = [
            '#additional table#product-attribute-specs-table',
            '.additional-attributes-wrapper table',
            '#additional'
        ]
        
        for selector in mas_info_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    if element.name == 'table' or element.select('table'):
                        content = self._extract_table_content(element)
                    else:
                        content = element.get_text(separator='\n', strip=True)
                    
                    if content and len(content) > 50:
                        print(f"✅ Descrição encontrada em: {selector}")
                        return content[:2000]  # Limitar tamanho
            except:
                continue
        
        # Fallback para descrição genérica
        desc_selectors = [
            '.product.attribute.description',
            '.product-description',
            '[itemprop="description"]'
        ]
        
        for selector in desc_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator='\n', strip=True)
                    if content and len(content) > 50:
                        return content[:2000]
            except:
                continue
        
        return ""
    
    def _extract_table_content(self, table_element) -> str:
        """Extrai conteúdo de tabela estruturada"""
        try:
            if table_element.name != 'table':
                table = table_element.select_one('table')
                if not table:
                    return table_element.get_text(separator='\n', strip=True)
                table_element = table
            
            rows = table_element.find_all('tr')
            table_content = []
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        table_content.append(f"{key}: {value}")
                elif len(cells) == 1:
                    cell_text = cells[0].get_text(strip=True)
                    if cell_text and len(cell_text) > 5:
                        table_content.append(cell_text)
            
            return '\n'.join(table_content) if table_content else ""
                
        except Exception as e:
            return table_element.get_text(separator='\n', strip=True) if table_element else ""
    
    def _is_valid_product_image_url(self, url: str) -> bool:
        """Verifica se URL é válida para imagem de produto"""
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Deve ter extensão de imagem
        if not any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            return False
        
        # Deve ser do Nissei
        if 'nissei.com' not in url_lower:
            return False
        
        # Deve parecer ser de produto
        if not any(indicator in url_lower for indicator in ['catalog', 'media', 'product']):
            return False
        
        return True
    
    def _resolve_image_url(self, url: str) -> str:
        """Resolve URL relativa para absoluta"""
        if not url:
            return url
        
        if url.startswith('//'):
            return f"https:{url}"
        elif url.startswith('/'):
            return f"https://nissei.com{url}"
        else:
            return url

    # ===== DOWNLOAD E SALVAMENTO DE IMAGENS =====
    
    def _download_product_images(self, product_data: Dict) -> int:
        """Download de imagens - simplificado"""
        image_urls = product_data.get('image_urls', [])
        if not image_urls:
            return 0
        
        print(f"📥 Baixando {len(image_urls)} imagens...")
        
        downloaded_count = 0
        
        for i, img_url in enumerate(image_urls):
            try:
                print(f"  📸 Baixando {i+1}/{len(image_urls)}: {img_url[:60]}...")
                
                response = requests.get(
                    img_url, 
                    timeout=30, 
                    stream=True, 
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                        'Referer': product_data.get('url', ''),
                    }
                )
                response.raise_for_status()
                
                # Ler conteúdo
                image_content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        image_content += chunk
                
                print(f"    📊 Baixado: {len(image_content)} bytes")
                
                # Processar imagem
                processed_image = self._process_image(image_content)
                if not processed_image:
                    print(f"    ❌ Falha no processamento")
                    continue
                
                # Preparar para salvamento
                if 'processed_images' not in product_data:
                    product_data['processed_images'] = []
                
                filename = f"product_{i+1}_{uuid.uuid4().hex[:8]}.jpg"
                
                product_data['processed_images'].append({
                    'content_base64': base64.b64encode(processed_image['content']).decode('utf-8'),
                    'filename': filename,
                    'original_url': img_url,
                    'width': processed_image['width'],
                    'height': processed_image['height'],
                    'is_main': (i == 0),
                    'content_type': 'image/jpeg',
                    'file_size': len(processed_image['content'])
                })
                
                downloaded_count += 1
                print(f"    ✅ Processada: {processed_image['width']}x{processed_image['height']}")
                
                time.sleep(0.5)  # Rate limiting
                    
            except Exception as e:
                print(f"    ❌ Erro: {str(e)}")
                continue
        
        print(f"📊 Total processadas: {downloaded_count}/{len(image_urls)}")
        return downloaded_count
    
    def _process_image(self, image_content: bytes) -> Optional[Dict[str, Any]]:
        """Processamento de imagem - igual ao teste"""
        try:
            if not image_content or len(image_content) < 1000:
                return None
            
            # Abrir com PIL
            image_buffer = BytesIO(image_content)
            img = Image.open(image_buffer)
            img.verify()
            
            # Reabrir para processamento
            image_buffer.seek(0)
            img = Image.open(image_buffer)
            
            original_width, original_height = img.size
            
            # Filtrar imagens muito pequenas
            if original_width < 100 or original_height < 100:
                return None
            
            # Converter para RGB
            if img.mode not in ['RGB', 'L']:
                if img.mode == 'RGBA':
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1] if len(img.split()) > 3 else None)
                    img = rgb_img
                else:
                    img = img.convert('RGB')
            
            # Redimensionar se muito grande
            max_dimension = 1200
            if original_width > max_dimension or original_height > max_dimension:
                print(f"    🔧 Redimensionando de {original_width}x{original_height}")
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            
            final_width, final_height = img.size
            
            # Salvar otimizado
            output_buffer = BytesIO()
            img.save(output_buffer, format='JPEG', quality=85, optimize=True)
            processed_content = output_buffer.getvalue()
            
            return {
                'content': processed_content,
                'width': final_width,
                'height': final_height,
                'format': 'JPEG',
                'content_type': 'image/jpeg'
            }
            
        except Exception as e:
            print(f"    ❌ Erro no processamento: {e}")
            return None

    # ===== SALVAMENTO NO BANCO =====
    
    def _save_products(self, products: List[Dict[str, Any]]) -> int:
        """Salva produtos no banco - simplificado"""
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
                    existing.name = product_data.get('name', existing.name)[:300]
                    existing.price = product_data.get('price') or existing.price
                    existing.description = product_data.get('description', existing.description)
                    existing.sku_code = product_data.get('sku_code') or getattr(existing, 'sku_code', None)
                    existing.search_query = product_data.get('search_query', existing.search_query)
                    existing.updated_at = timezone.now()
                    existing.save()
                    product_obj = existing
                else:
                    # Criar novo produto
                    product_obj = Product.objects.create(
                        name=product_data.get('name', 'Produto sem nome')[:300],
                        price=product_data.get('price'),
                        description=product_data.get('description', ''),
                        url=product_data['url'],
                        site=self.site,
                        search_query=product_data.get('search_query', ''),
                        status=1
                    )
                    
                    # Adicionar SKU se o campo existir
                    if hasattr(product_obj, 'sku_code'):
                        product_obj.sku_code = product_data.get('sku_code')
                        product_obj.save()
                
                # Salvar imagens
                if 'processed_images' in product_data:
                    self._save_product_images(product_obj, product_data['processed_images'])
                
                saved_count += 1
                print(f"Produto salvo: {product_obj.name[:50]}... | SKU: {product_data.get('sku_code', 'N/A')}")
                
            except Exception as e:
                print(f"Erro ao salvar produto: {str(e)}")
                continue
        
        return saved_count
    
    def _save_product_images(self, product: Product, processed_images: List[Dict]):
        """Salva imagens no banco - compatível"""
        try:
            print(f"💾 Salvando {len(processed_images)} imagens para produto {product.id}")
            
            # Verificar campos do modelo
            model_fields = [field.name for field in ProductImage._meta.get_fields()]
            
            # Remover imagens antigas
            ProductImage.objects.filter(product=product).delete()
            
            saved_count = 0
            
            for i, img_data in enumerate(processed_images):
                try:
                    content = base64.b64decode(img_data.get('content_base64', ''))
                    filename = img_data.get('filename', f'product_{product.id}_img_{i+1}.jpg')
                    image_file = ContentFile(content, name=filename)
                    
                    # Dados básicos (sempre existem)
                    image_data = {
                        'product': product,
                        'image': image_file,
                        'is_main': img_data.get('is_main', False),
                        'alt_text': f"{product.name} - Imagem {i+1}",
                        'order': i,
                        'original_url': img_data.get('original_url', '')
                    }
                    
                    # Campos opcionais (só se existirem)
                    optional_fields = {
                        'width': img_data.get('width', 0),
                        'height': img_data.get('height', 0),
                        'file_size': img_data.get('file_size', len(content)),
                        'content_type': img_data.get('content_type', 'image/jpeg')
                    }
                    
                    for field_name, value in optional_fields.items():
                        if field_name in model_fields:
                            image_data[field_name] = value
                    
                    # Criar registro
                    product_image = ProductImage.objects.create(**image_data)
                    
                    # Primeira como principal
                    if i == 0:
                        product.main_image = product_image.image
                        product.save(update_fields=['main_image'])
                    
                    saved_count += 1
                    print(f"    ✅ Imagem {i+1} salva")
                    
                except Exception as e:
                    print(f"    ❌ Erro na imagem {i+1}: {e}")
                    continue
            
            print(f"📊 {saved_count}/{len(processed_images)} imagens salvas")
            return saved_count
            
        except Exception as e:
            print(f"❌ Erro ao salvar imagens: {e}")
            return 0

    # ===== MÉTODOS AUXILIARES =====
    
    def _get_basic_product_list(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Obter lista básica de produtos"""
        try:
            query_encoded = query.replace(' ', '+')
            search_url = f"{self.base_url}/py/catalogsearch/result/?q={query_encoded}"
            
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            product_elements = soup.select('.product-item')[:max_results]
            
            basic_products = []
            for element in product_elements:
                try:
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
            print(f"Erro ao obter lista básica: {str(e)}")
            return []
    
    def _filter_products_with_ai(self, products: List[Dict], search_query: str) -> List[Dict]:
        """Filtro com IA (opcional)"""
        if not self.ai_available or not products:
            return products
        
        try:
            print(f"🧠 Filtrando {len(products)} produtos com IA")
            
            # Preparar lista simplificada
            product_list = []
            for i, product in enumerate(products):
                product_list.append({
                    'index': i,
                    'name': product.get('name', ''),
                    'url': product.get('url', '')
                })
            
            # Prompt simples
            filter_prompt = f"""
Filtre apenas os produtos PRINCIPAIS da busca "{search_query}":

{json.dumps(product_list, ensure_ascii=False, indent=2)}

Remova acessórios como capas, películas, carregadores.
Mantenha apenas produtos principais.

Responda JSON:
{{"filtered_indices": [0, 1, 3], "reasoning": "motivo"}}
"""
            
            # Chamar IA
            ai_response = self._call_ai_api(filter_prompt)
            
            if ai_response:
                response_clean = ai_response.replace('```json', '').replace('```', '').strip()
                filter_result = json.loads(response_clean)
                
                filtered_indices = filter_result.get('filtered_indices', [])
                filtered_products = []
                for index in filtered_indices:
                    if 0 <= index < len(products):
                        filtered_products.append(products[index])
                
                print(f"📊 Filtrado: {len(products)} → {len(filtered_products)}")
                return filtered_products
            
        except Exception as e:
            print(f"Erro no filtro IA: {e}")
        
        return products
    
    def _call_ai_api(self, prompt: str) -> str:
        """Chama API de IA"""
        try:
            model_type = self.configuration.model_integration.lower()
            
            if 'openai' in model_type or 'gpt' in model_type:
                return self._call_openai_api(prompt)
            elif 'claude' in model_type or 'anthropic' in model_type:
                return self._call_claude_api(prompt)
            
            return ""
                
        except Exception as e:
            print(f"Erro na API de IA: {e}")
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
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
        except Exception as e:
            print(f"Erro OpenAI API: {e}")
        
        return ""
    
    def _call_claude_api(self, prompt: str) -> str:
        """Chama API do Claude"""
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
                data = response.json()
                return data["content"][0]["text"]
                
        except Exception as e:
            print(f"Erro Claude API: {e}")
        
        return ""
    
    def _cleanup_selenium(self):
        """Limpa recursos do Selenium"""
        if self.driver:
            try:
                self.driver.quit()
                print("Selenium finalizado")
            except:
                pass
            self.driver = None
    
    def close(self):
        """Fecha todos os recursos"""
        self._cleanup_selenium()
        if hasattr(self, 'session'):
            self.session.close()
