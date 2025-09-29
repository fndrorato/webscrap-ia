import base64
import os
import re
import requests
import time
import json
import uuid
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
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

from products.models import Product, ProductImage
from sites.models import Site
# Assumindo que Configuration está em um app chamado 'core' ou similar
from configurations.models import Configuration


class AISeleniumNisseiScraper:
    """
    Scraper avançado do Nissei com IA + Selenium usando Configuration flexível
    Suporta Claude, OpenAI, e outros modelos configuráveis
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
        
        # Configurações
        self.delay_between_requests = 1     # Era 3, agora 1
        self.delay_between_products = 2     # Era 5, agora 2
        self.max_retries = 2               # Era 3, agora 2
        self.max_images_per_product = 3
        
        # Configurar Selenium
        self.driver = None
        self.setup_selenium()
        
        # Validação de imagens
        self.max_image_size = 10 * 1024 * 1024  # 10MB
        self.min_image_size = 1024  # 1KB
        self.supported_formats = ['jpeg', 'jpg', 'png', 'webp']
        
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
        """SUBSTITUIR método setup_selenium() existente por este"""
        try:
            chrome_options = Options()
            
            # Configurações básicas
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # REMOVER estas linhas se existirem no código original:
            # chrome_options.add_argument('--disable-images')      # COMENTAR!
            # chrome_options.add_argument('--disable-javascript')  # COMENTAR!
            
            # Otimizações que funcionaram no teste
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            
            # Configurações para evitar detecção (do teste)
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # User agent
            chrome_options.add_argument(
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Timeouts que funcionaram no teste
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            # Remover detecção de automação
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            print("✅ Selenium configurado (versão que funcionou no teste)")
            
        except Exception as e:
            print(f"❌ Erro ao configurar Selenium: {e}")
            self.driver = None
    
    # ===== MÉTODO PRINCIPAL ATUALIZADO =====

    def scrape_products_intelligent(self, query: str, max_results: int = 10, max_detailed: int = 5) -> List[Dict[str, Any]]:
        """
        Scraping inteligente MELHORADO com:
        1. Filtro IA para relevância
        2. Extração de SKU
        3. Imagens do carrossel JavaScript  
        4. Descrição específica (Más Información → Detalles)
        """
        try:
            print(f"SCRAPING INTELIGENTE MELHORADO com {self.configuration.model_integration}")
            print(f"Busca: '{query}' | Max listagem: {max_results} | Max detalhes: {max_detailed}")
            print("=" * 70)
            
            # FASE 1: Obter lista básica de produtos
            print("FASE 1: Obtendo lista de produtos...")
            basic_products = self._get_basic_product_list(query, max_results)
            
            if not basic_products:
                print("Nenhum produto encontrado na listagem")
                return []
            
            print(f"{len(basic_products)} produtos encontrados na listagem")
            
            # FASE 1.5: 🧠 FILTRAR COM IA (NOVO!)
            print("FASE 1.5: Filtrando produtos relevantes com IA...")
            filtered_products = self._filter_products_with_ai(basic_products, query)
            
            # Ajustar quantidade de detalhes baseado no filtro
            products_for_details = filtered_products[:max_detailed]
            print(f"Processando {len(products_for_details)} produtos filtrados com IA + Selenium")
            print("=" * 70)
            
            detailed_products = []
            
            for i, basic_product in enumerate(products_for_details, 1):
                try:
                    print(f"\nPRODUTO {i}/{len(products_for_details)}: {basic_product.get('name', '')[:50]}...")
                    print(f"URL: {basic_product.get('url', '')}")
                    
                    # Usar estratégia inteligente MELHORADA
                    detailed_product = self._extract_product_intelligent_enhanced(basic_product)
                    
                    if detailed_product:
                        detailed_products.append(detailed_product)
                        print(f"Produto processado com IA + Selenium")
                        
                        # Baixar imagens DO CARROSSEL (melhorado)
                        print(f"Baixando imagens do carrossel...")
                        image_count = self._download_product_images(detailed_product)
                        print(f"{image_count} imagens baixadas")
                    else:
                        print("Falha ao processar produto")
                    
                    # Rate limiting entre produtos
                    if i < len(products_for_details):
                        print(f"Aguardando {self.delay_between_products}s...")
                        time.sleep(self.delay_between_products)
                        
                except Exception as e:
                    print(f"Erro ao processar produto {i}: {str(e)}")
                    continue
            
            # FASE 3: Produtos restantes (apenas se sobraram depois do filtro)
            remaining_products = filtered_products[max_detailed:]
            if remaining_products:
                print(f"\nFASE 3: Adicionando {len(remaining_products)} produtos básicos filtrados...")
                for basic_product in remaining_products:
                    basic_product.update({
                        'scraped_at': timezone.now().isoformat(),
                        'site_id': self.site.id,
                        'currency': self.currency,
                        'country': 'Paraguay',
                        'extraction_method': 'basic_filtered',
                        'details_extracted': False,
                        'description': 'Produto filtrado por IA - detalhes não extraídos',
                        'sku_code': None,
                        'categories': [],
                        'specifications': {},
                        'image_urls': [],
                        'processed_images': []
                    })
                    detailed_products.append(basic_product)
            
            # FASE 4: Salvar no banco de dados  
            print(f"\nFASE 4: Salvando {len(detailed_products)} produtos...")
            saved_count = self._save_products_enhanced(detailed_products)
            
            print(f"SCRAPING INTELIGENTE MELHORADO CONCLUÍDO!")
            print(f"Total encontrados: {len(basic_products)}")
            print(f"Filtrados por IA: {len(filtered_products)}")
            print(f"Com detalhes completos: {len(products_for_details)}")
            print(f"Produtos salvos: {saved_count}")
            
            return detailed_products
            
        except Exception as e:
            print(f"Erro geral no scraping inteligente: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []
        finally:
            self._cleanup_selenium()

    # ===== MÉTODO DE EXTRAÇÃO MELHORADO =====

    def _extract_product_intelligent_enhanced(self, basic_product: Dict) -> Optional[Dict[str, Any]]:
        """
        VERSÃO MODIFICADA: SEMPRE tenta carrossel independente de ter imagens básicas
        """
        product_url = basic_product['url']
        
        print("📡 Estratégia 1: Requests básico...")
        basic_result = self._extract_with_requests_enhanced(product_url)
        
        # MUDANÇA CRÍTICA: Não considera suficiente apenas por ter imagens básicas
        # Sempre vai para Selenium se disponível para tentar carrossel
        has_basic_data = (
            bool(basic_result.get('name')) and 
            bool(basic_result.get('price')) and 
            bool(basic_result.get('description'))
        )
        
        if has_basic_data:
            print("✅ Dados básicos extraídos, mas tentando carrossel...")
        else:
            print("⚠️ Dados básicos incompletos")
        
        # SEMPRE tentar Selenium para carrossel (exceto se driver não disponível)
        print("🌐 Estratégia 2: Selenium + Carrossel (FORÇADO)...")
        selenium_result, html_content = self._extract_with_selenium_enhanced(product_url)
        
        # Combinar resultados (Selenium pode ter imagens melhores do carrossel)
        combined_result = basic_product.copy()
        if basic_result:
            combined_result.update(basic_result)
        if selenium_result:
            # PRIORIZAR imagens do Selenium (carrossel) sobre básicas
            if selenium_result.get('image_urls'):
                print(f"🔄 Substituindo imagens básicas por imagens do carrossel")
                print(f"   Básicas: {len(basic_result.get('image_urls', []))} imagens")
                print(f"   Carrossel: {len(selenium_result.get('image_urls', []))} imagens")
                combined_result['image_urls'] = selenium_result['image_urls']
            
            # Atualizar outros campos do Selenium
            for key, value in selenium_result.items():
                if key != 'image_urls' and value:  # Não sobrescrever image_urls já tratado acima
                    combined_result[key] = value
        
        # Verificar resultado final
        if self._is_extraction_sufficient_enhanced(combined_result):
            print("✅ Extração completa após Selenium + Carrossel")
            combined_result['extraction_method'] = 'selenium_enhanced_carousel'
            return self._finalize_product_data(combined_result)
        
        # Estratégia 3: IA (apenas se realmente necessário)
        if self.ai_available and html_content:
            print(f"🧠 Estratégia 3: IA ({self.configuration.model_integration})...")
            ai_result = self._extract_with_ai(product_url, html_content)
            
            if ai_result:
                combined_result.update(ai_result)
                combined_result['extraction_method'] = f'ai_{self.configuration.model_integration.lower()}_enhanced'
                print("✅ IA complementou os dados")
            else:
                combined_result['extraction_method'] = 'selenium_enhanced_carousel_partial'
                print("⚠️ IA não melhorou, usando dados do Selenium + Carrossel")
        else:
            combined_result['extraction_method'] = 'selenium_enhanced_carousel_only'
        
        return self._finalize_product_data(combined_result)

    # ===== MÉTODOS AUXILIARES MELHORADOS =====

    def _extract_with_requests_enhanced(self, url: str) -> Dict[str, Any]:
        """Extração básica MELHORADA com SKU"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extração básica + melhorias
            data = self._extract_basic_data(soup)  # Método existente
            
            # 🏷️ ADICIONAR: Extração de SKU
            sku_code = self._extract_sku_code(soup)
            if sku_code:
                data['sku_code'] = sku_code
            
            # 📝 MELHORAR: Usar nova extração de descrição
            enhanced_description = self._extract_description_enhanced(soup)
            if enhanced_description:
                data['description'] = enhanced_description
            
            return data
        except Exception as e:
            print(f"Requests melhorado falhou: {e}")
            return {}

    def _extract_with_selenium_enhanced(self, url: str) -> tuple[Dict[str, Any], str]:
        """
        VERSÃO MODIFICADA: FORÇA extração do carrossel
        """
        if not self.driver:
            print("Selenium não disponível")
            return {}, ""
        
        try:
            print(f"Acessando com Selenium FORÇADO para carrossel: {url}")
            self.driver.get(url)
            
            # Aguardar carregamento básico
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Aguardar conteúdo dinâmico + ativar abas
            self._wait_for_dynamic_content()
            
            # Obter HTML renderizado
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # MUDANÇA: Chamar extração avançada que FORÇA carrossel
            selenium_data = self._extract_advanced_data_with_forced_carousel(soup, self.driver)
            
            return selenium_data, html_content
            
        except Exception as e:
            print(f"Selenium melhorado falhou: {e}")
            return {}, ""


    def _extract_advanced_data_enhanced(self, soup: BeautifulSoup, driver=None) -> Dict[str, Any]:
        """Extração avançada CORRIGIDA com Fotorama + Descrição Priorizada"""
        data = {}
        
        # Usar método existente como base
        base_data = self._extract_advanced_data(soup)
        data.update(base_data)
        
        # 🏷️ SKU (já funcionando)
        sku_code = self._extract_sku_code(soup)
        if sku_code:
            data['sku_code'] = sku_code
        
        # 🎠 CORREÇÃO 1: Imagens ESPECÍFICAS do carrossel Fotorama
        print("🎠 Extraindo imagens do carrossel...")
        fotorama_images = self._extract_fotorama_carousel_images(soup, driver)  # Deve chamar o método novo
        
        if fotorama_images:
            data['image_urls'] = fotorama_images
            print(f"✅ {len(fotorama_images)} imagens do carrossel extraídas")
        else:
            print("⚠️ Nenhuma imagem do carrossel - usando extração básica")
            # Fallback para método básico se falhar
            basic_images = self._extract_images_basic(soup)
            if basic_images:
                data['image_urls'] = basic_images
            
        # 📝 CORREÇÃO 2: Descrição com prioridade FIXA (Más Información → Detalles)
        print("📝 Extraindo descrição com prioridade corrigida...")
        priority_description = self._extract_description_priority_fixed(soup, driver)
        
        if priority_description:
            data['description'] = priority_description
            print(f"✅ Descrição priorizada extraída ({len(priority_description)} chars)")
        else:
            print("⚠️ Descrição priorizada falhou, usando básica...")
            # Fallback para método original se tudo falhar
            basic_desc = self._extract_description_smart(soup)
            if basic_desc:
                data['description'] = basic_desc
        
        return data

    def _extract_carousel_images_improved(self, soup: BeautifulSoup, driver=None) -> List[str]:
        """Método principal melhorado - ADICIONAR na classe"""
        
        print("=== EXTRAÇÃO DE IMAGENS DO CARROSSEL (MELHORADA) ===")
        
        if not driver:
            print("Selenium necessário - usando fallback estático")
            return self._extract_images_basic(soup)
        
        image_candidates = []
        
        try:
            # Debug da estrutura
            self._debug_page_structure(driver)
            
            # Aguardar carrossel carregar
            if not self._wait_for_carousel_advanced(driver):
                print("Carrossel não detectado - extraindo todas as imagens de produto")
                return self._extract_all_product_images(driver)
            
            # Extrair imagem principal
            main_image = self._extract_main_carousel_image(driver)
            if main_image:
                image_candidates.append((main_image, 15, 'main-image'))
            
            # Navegar por thumbnails
            nav_images = self._navigate_carousel_smart(driver)
            for i, img_url in enumerate(nav_images):
                if img_url not in [c[0] for c in image_candidates]:
                    image_candidates.append((img_url, 12, f'navigation-{i+1}'))
            
            # Buscar em data attributes
            data_images = self._extract_data_attribute_images(driver)
            for img_url in data_images:
                if img_url not in [c[0] for c in image_candidates]:
                    image_candidates.append((img_url, 8, 'data-attribute'))
            
            # Processar resultados
            final_images = self._process_image_candidates(image_candidates)
            
            print(f"RESULTADO: {len(final_images)} imagens extraídas")
            return final_images
            
        except Exception as e:
            print(f"Erro na extração: {e}")
            return self._extract_all_product_images(driver)        

    def extract_carousel_with_arrow_navigation(self, soup: BeautifulSoup, driver=None) -> List[str]:
        """
        Navegação ESPECÍFICA por setas do carrossel Nissei
        Foca em detectar e clicar nas setas para navegar
        """
        print("🎯 === NAVEGAÇÃO POR SETAS DO CARROSSEL ===")
        
        if not driver:
            print("❌ Selenium obrigatório para navegação por setas")
            return []
        
        all_images = []
        
        try:
            # PASSO 1: Aguardar página carregar completamente
            print("⏳ Aguardando carregamento completo...")
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)  # Aguardar JavaScript inicializar
            
            # PASSO 2: Debug detalhado da estrutura do carrossel
            print("🔍 Analisando estrutura do carrossel...")
            self._debug_carousel_structure_detailed(driver)
            
            # PASSO 3: Capturar imagem inicial (antes de navegar)
            print("📸 Capturando imagem inicial...")
            initial_image = self._get_current_carousel_image(driver)
            if initial_image:
                all_images.append(initial_image)
                print(f"   ✅ Inicial: {initial_image[:60]}...")
            else:
                print("   ❌ Nenhuma imagem inicial encontrada")
            
            # PASSO 4: Encontrar botão de próxima imagem
            print("🔍 Procurando botões de navegação...")
            next_buttons = self._find_carousel_next_buttons(driver)
            
            if not next_buttons:
                print("   ❌ Nenhum botão de navegação encontrado")
                return all_images
            
            print(f"   ✅ {len(next_buttons)} botões encontrados")
            
            # PASSO 5: Navegar pelo carrossel clicando nas setas
            print("🔄 Iniciando navegação por setas...")
            navigation_images = self._navigate_with_arrows_detailed(driver, next_buttons[0])
            
            # PASSO 6: Adicionar imagens não duplicadas
            for img in navigation_images:
                if img and img not in all_images:
                    all_images.append(img)
            
            print(f"🎯 RESULTADO: {len(all_images)} imagens extraídas via setas")
            
            return all_images[:self.max_images_per_product]
            
        except Exception as e:
            print(f"❌ Erro na navegação por setas: {e}")
            import traceback
            print(traceback.format_exc())
            return all_images

    def _debug_carousel_structure_detailed(self, driver):
        """Debug MUITO detalhado da estrutura do carrossel"""
        
        print("🔍 === DEBUG DETALHADO DO CARROSSEL ===")
        
        # 1. Procurar por elementos Fotorama
        fotorama_selectors = [
            '.fotorama',
            '[data-fotorama]', 
            '.fotorama__stage',
            '.fotorama__nav',
            '.fotorama__arr'
        ]
        
        for selector in fotorama_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"{selector}: {len(elements)} elementos")
                
                if elements:
                    elem = elements[0]
                    print(f"   Classe: {elem.get_attribute('class')}")
                    print(f"   ID: {elem.get_attribute('id')}")
                    print(f"   Visível: {elem.is_displayed()}")
            except Exception as e:
                print(f"{selector}: ERRO - {e}")
        
        # 2. Procurar por botões de seta especificamente
        arrow_selectors = [
            '.fotorama__arr--next',
            '.fotorama__arr--prev', 
            '.fotorama__arr[data-side="next"]',
            '.fotorama__arr[data-side="prev"]',
            'button[class*="next"]',
            'button[class*="arrow"]',
            '.carousel-control-next',
            '.slick-next',
            'button[aria-label*="next"]'
        ]
        
        print("\n🎯 BOTÕES DE SETA:")
        for selector in arrow_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                print(f"{selector}: {len(buttons)} botões")
                
                for i, btn in enumerate(buttons[:2]):  # Primeiros 2
                    try:
                        print(f"   Botão {i+1}:")
                        print(f"     Visível: {btn.is_displayed()}")
                        print(f"     Habilitado: {btn.is_enabled()}")
                        print(f"     Texto: '{btn.text.strip()}'")
                        print(f"     Classe: {btn.get_attribute('class')}")
                        print(f"     Posição: {btn.location}")
                    except Exception as e:
                        print(f"     ERRO: {e}")
            except Exception as e:
                print(f"{selector}: ERRO - {e}")
        
        # 3. Verificar imagens atuais
        print("\n📸 IMAGENS ATUAIS:")
        current_images = driver.find_elements(By.CSS_SELECTOR, "img[src*='catalog'], img[data-src*='catalog']")
        print(f"Imagens de produto visíveis: {len(current_images)}")
        
        for i, img in enumerate(current_images[:3]):
            try:
                print(f"   Img {i+1}:")
                print(f"     src: {img.get_attribute('src')[:60] if img.get_attribute('src') else 'None'}...")
                print(f"     data-src: {img.get_attribute('data-src')[:60] if img.get_attribute('data-src') else 'None'}...")
                print(f"     Visível: {img.is_displayed()}")
                print(f"     Tamanho: {img.size}")
            except Exception as e:
                print(f"     ERRO: {e}")

    def _find_carousel_next_buttons(self, driver) -> List:
        """Encontra botões de próxima imagem do carrossel"""
        
        selectors = [
            '.fotorama__arr--next',
            '.fotorama__arr[data-side="next"]',
            '.carousel-control-next',
            '.slick-next',
            'button[class*="next"]',
            'button[aria-label*="next"]'
        ]
        
        found_buttons = []
        
        for selector in selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        # Evitar botões de "anterior"
                        classes = (button.get_attribute('class') or '').lower()
                        aria = (button.get_attribute('aria-label') or '').lower()
                        
                        if any(word in classes + aria for word in ['prev', 'previous', 'back']):
                            continue
                        
                        found_buttons.append(button)
                        break
                        
            except:
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

    def _get_current_carousel_image(self, driver) -> Optional[str]:
        """Obtém imagem atualmente visível no carrossel"""
        
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
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        # Verificar se é imagem grande (não thumbnail)
                        size = element.size
                        if size.get('width', 0) > 200 and size.get('height', 0) > 200:
                            
                            # Buscar melhor URL disponível
                            for attr in ['data-zoom-image', 'data-large-image', 'data-src', 'src']:
                                url = element.get_attribute(attr)
                                if url and self._is_valid_product_image_url(url):
                                    return self._resolve_image_url(url)
            except:
                continue
        
        return None

    def _navigate_with_arrows_detailed(self, driver, next_button) -> List[str]:
        """Navegação detalhada com logging completo"""
        
        navigation_images = []
        max_clicks = 8  # Máximo de cliques nas setas
        
        print(f"🔄 Iniciando navegação: máximo {max_clicks} cliques")
        
        for click_num in range(max_clicks):
            try:
                print(f"\n--- CLIQUE {click_num + 1}/{max_clicks} ---")
                
                # PASSO 1: Verificar se botão ainda está disponível
                if not next_button.is_displayed() or not next_button.is_enabled():
                    print("   ⚠️ Botão não está mais disponível")
                    break
                
                # PASSO 2: Capturar imagem ANTES do clique (para comparação)
                image_before = self._get_current_carousel_image(driver)
                print(f"   📸 Antes: {image_before[:60] if image_before else 'None'}...")
                
                # PASSO 3: Scroll até botão (garantir que está visível)
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                    next_button
                )
                time.sleep(1)
                
                # PASSO 4: Clicar no botão
                print("   🖱️ Clicando botão...")
                try:
                    # Tentar clique normal primeiro
                    next_button.click()
                    print("      ✅ Clique normal OK")
                except Exception as e:
                    print(f"      ⚠️ Clique normal falhou: {e}")
                    # Fallback: JavaScript click
                    driver.execute_script("arguments[0].click();", next_button)
                    print("      ✅ Clique JS OK")
                
                # PASSO 5: Aguardar transição do carrossel
                print("   ⏳ Aguardando transição...")
                time.sleep(3)  # Aguardar animação completa
                
                # PASSO 6: Capturar imagem DEPOIS do clique
                image_after = self._get_current_carousel_image(driver)
                print(f"   📸 Depois: {image_after[:60] if image_after else 'None'}...")
                
                # PASSO 7: Verificar se mudou
                if image_after and image_after != image_before:
                    if image_after not in navigation_images:
                        navigation_images.append(image_after)
                        print("   ✅ NOVA IMAGEM CAPTURADA!")
                    else:
                        print("   ⚠️ Imagem já capturada anteriormente")
                elif image_after == image_before:
                    print("   ⚠️ Imagem não mudou - possível fim do carrossel")
                    # Tentar mais um clique para confirmar
                    if click_num < 2:  # Só nas primeiras tentativas
                        continue
                    else:
                        break
                else:
                    print("   ❌ Erro ao capturar imagem após clique")
                
                # PASSO 8: Verificar se chegou ao fim do carrossel
                # (alguns carrosseis desabilitam o botão no final)
                try:
                    if ('disabled' in next_button.get_attribute('class') or 
                        next_button.get_attribute('disabled') or
                        not next_button.is_enabled()):
                        print("   ⚠️ Botão desabilitado - fim do carrossel")
                        break
                except:
                    pass
                    
            except Exception as e:
                print(f"   ❌ Erro no clique {click_num + 1}: {e}")
                # Tentar continuar com próximo clique
                continue
        
        print(f"\n🎯 Navegação concluída: {len(navigation_images)} imagens capturadas")
        
        return navigation_images

    def test_arrow_navigation_only(self):
        """Teste ISOLADO da navegação por setas"""
        
        test_url = "https://nissei.com/py/apple-iphone-16-pro-a3083-1"
        
        print("🧪 === TESTE ISOLADO: NAVEGAÇÃO POR SETAS ===")
        print(f"URL: {test_url}")
        print("=" * 60)
        
        # Configurar Selenium
        if not self.driver:
            self.setup_selenium_for_images()  # Usar versão que carrega imagens
        
        if not self.driver:
            print("❌ ERRO: Selenium não inicializou")
            return []
        
        try:
            # Acessar página
            print("📡 Acessando página...")
            self.driver.get(test_url)
            
            # Aguardar carregamento
            print("⏳ Aguardando carregamento...")
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)
            
            # Extrair usando navegação por setas
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            images = self.extract_carousel_with_arrow_navigation(soup, self.driver)
            
            # Validar resultados
            print(f"\n📊 === RESULTADOS ===")
            print(f"Total de imagens: {len(images)}")
            
            for i, url in enumerate(images, 1):
                print(f"{i}. {url}")
                
                # Testar se URL funciona
                try:
                    response = requests.head(url, timeout=5)
                    status = "✅" if response.status_code == 200 else f"❌ {response.status_code}"
                    print(f"   Status: {status}")
                except:
                    print(f"   Status: ❌ ERRO")
            
            print(f"\n🎉 Teste concluído!")
            print("💡 Driver mantido aberto para inspeção manual")
            print("   Use self.driver.quit() quando terminar")
            
            return images
            
        except Exception as e:
            print(f"❌ ERRO no teste: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _is_extraction_sufficient_enhanced(self, data: Dict) -> bool:
        """Critérios melhorados incluindo SKU"""
        if not data:
            return False
        
        has_name = bool(data.get('name')) and len(data.get('name', '')) > 5
        has_price = bool(data.get('price'))
        has_desc = bool(data.get('description')) and len(data.get('description', '')) > 30
        has_images = bool(data.get('image_urls')) and len(data.get('image_urls', [])) > 0
        has_sku = bool(data.get('sku_code'))  # NOVO critério
        
        print(f"🔍 Verificando suficiência melhorada:")
        print(f"   - Nome: {'✅' if has_name else '❌'}")
        print(f"   - Preço: {'✅' if has_price else '❌'}")
        print(f"   - Descrição: {'✅' if has_desc else '❌'} ({len(data.get('description', ''))} chars)")
        print(f"   - Imagens: {'✅' if has_images else '❌'} ({len(data.get('image_urls', []))} URLs)")
        print(f"   - SKU: {'✅' if has_sku else '❌'} ({data.get('sku_code', 'N/A')})")
        
        # Critério mais rigoroso: nome + preço + (descrição OU imagens) + SKU é ideal
        if has_name and has_price and (has_desc or has_images) and has_sku:
            print("✅ Extração considerada completa (com SKU)")
            return True
        
        # Fallback: aceitar sem SKU se tem outros dados bons
        if has_name and has_price and has_desc and has_images:
            print("⚠️ Extração boa mas sem SKU")
            return True
        
        print("❌ Extração insuficiente")
        return False

    def _save_products_enhanced(self, products: List[Dict[str, Any]]) -> int:
        """Salvar produtos com SKU"""
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
                    if has_details or not existing.description:
                        existing.name = product_data.get('name', existing.name)[:300]
                        existing.price = product_data.get('price') or existing.price
                        existing.original_price = product_data.get('original_price') or existing.original_price
                        existing.sku_code = product_data.get('sku_code') or existing.sku_code  # NOVO
                        
                        if has_details:
                            existing.description = product_data.get('description', '')
                            existing.brand = product_data.get('brand', '')[:100] if product_data.get('brand') else existing.brand
                            existing.availability = product_data.get('availability', '')[:100] or existing.availability
                        
                        existing.search_query = product_data.get('search_query', existing.search_query)
                        existing.updated_at = timezone.now()
                        existing.save()
                    
                    product_obj = existing
                else:
                    # Criar novo produto COM SKU
                    product_obj = Product.objects.create(
                        name=product_data.get('name', 'Produto sem nome')[:300],
                        price=product_data.get('price'),
                        original_price=product_data.get('original_price'),
                        description=product_data.get('description', ''),
                        url=product_data['url'],
                        brand=product_data.get('brand', '')[:100] if product_data.get('brand') else None,
                        availability=product_data.get('availability', '')[:100],
                        sku_code=product_data.get('sku_code'),  # NOVO CAMPO
                        site=self.site,
                        search_query=product_data.get('search_query', ''),
                        status=1
                    )
                
                # Salvar imagens
                if has_details and 'processed_images' in product_data:
                    self._save_product_images(product_obj, product_data['processed_images'])
                
                saved_count += 1
                extraction_method = product_data.get('extraction_method', 'unknown')
                sku_info = f"SKU: {product_data.get('sku_code', 'N/A')}"
                print(f"Produto salvo ({extraction_method}): {product_obj.name[:40]}... | {sku_info}")
                
            except Exception as e:
                print(f"Erro ao salvar produto: {str(e)}")
                continue
        
        return saved_count
    
    def _extract_product_intelligent(self, basic_product: Dict) -> Optional[Dict[str, Any]]:
        """Versão otimizada da extração inteligente"""
        product_url = basic_product['url']
        
        print("📡 Estratégia 1: Requests básico...")
        basic_result = self._extract_with_requests(product_url)
        
        if self._is_extraction_sufficient(basic_result):
            print("✅ Requests básico foi suficiente")
            result = basic_product.copy()
            result.update(basic_result)
            result['extraction_method'] = 'requests'
            return self._finalize_product_data(result)
        
        print("🌐 Estratégia 2: Selenium + JavaScript...")
        selenium_result, html_content = self._extract_with_selenium(product_url)
        
        # Combinar resultados
        combined_result = basic_product.copy()
        if basic_result:
            combined_result.update(basic_result)
        if selenium_result:
            combined_result.update(selenium_result)
        
        if self._is_extraction_sufficient(combined_result):
            print("✅ Selenium foi suficiente")
            combined_result['extraction_method'] = 'selenium'
            return self._finalize_product_data(combined_result)
        
        # Estratégia 3: IA (apenas se realmente necessário)
        if self.ai_available and html_content:
            print(f"🧠 Estratégia 3: IA ({self.configuration.model_integration})...")
            ai_result = self._extract_with_ai(product_url, html_content)
            
            if ai_result:
                combined_result.update(ai_result)
                combined_result['extraction_method'] = f'ai_{self.configuration.model_integration.lower()}_selenium'
                print("✅ IA complementou os dados")
            else:
                combined_result['extraction_method'] = 'selenium_partial'
                print("⚠️ IA não melhorou, usando dados do Selenium")
        else:
            print("⚠️ Pulando IA (não disponível ou sem HTML)")
            combined_result['extraction_method'] = 'selenium_only'
        
        return self._finalize_product_data(combined_result)
    
    def _extract_with_ai(self, url: str, html_content: str) -> Dict[str, Any]:
        """Extração com IA usando configuração flexível"""
        if not self.ai_available or not html_content or len(html_content) < 1000:
            print("IA não disponível ou HTML insuficiente")
            return {}
        
        try:
            print(f"Chamando {self.configuration.model_integration} API...")
            
            # Preparar HTML resumido
            html_summary = self._prepare_html_for_ai(html_content)
            
            # Gerar prompt baseado no modelo
            prompt = self._generate_extraction_prompt(url, html_summary)
            
            # Chamar API baseada no modelo configurado
            ai_response = self._call_ai_api(prompt)
            
            if ai_response:
                try:
                    ai_data = json.loads(ai_response)
                    print("IA extraiu dados com sucesso")
                    return self._clean_ai_response(ai_data)
                except json.JSONDecodeError as e:
                    print(f"Erro ao parsear resposta da IA: {e}")
                    print(f"Resposta: {ai_response[:200]}...")
            
        except Exception as e:
            print(f"Erro na extração com IA: {e}")
        
        return {}

    def _extract_fotorama_carousel_images(self, soup: BeautifulSoup, driver=None) -> List[str]:
        """SUBSTITUIR método _extract_fotorama_carousel_images existente por este"""
        
        print("🎠 Extraindo imagens do carrossel (versão que funcionou no teste)...")
        
        if not driver:
            print("⚠️ Selenium necessário - usando fallback")
            return self._extract_images_basic(soup)
        
        all_images = []
        
        try:
            # EXATAMENTE como funcionou no teste
            
            # PASSO 1: Aguardar carregamento
            print("⏳ Aguardando carregamento...")
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)  # Mesmo tempo do teste
            
            # PASSO 2: Capturar imagem inicial
            print("📸 Capturando imagem inicial...")
            initial_image = self._get_current_carousel_image_test_version(driver)
            if initial_image:
                all_images.append(initial_image)
                print(f"   ✅ Inicial: {initial_image[:60]}...")
            
            # PASSO 3: Encontrar botões (mesmo método do teste)
            print("🔍 Procurando botões de setas...")
            next_buttons = self._find_next_buttons_test_version(driver)
            
            if not next_buttons:
                print("   ⚠️ Nenhum botão encontrado")
                return all_images
            
            print(f"   ✅ {len(next_buttons)} botão(ões) encontrado(s)")
            
            # PASSO 4: Navegar (mesmo método do teste)
            print("🔄 Navegando por setas...")
            navigation_images = self._navigate_with_arrows_test_version(driver, next_buttons[0])
            
            # PASSO 5: Adicionar imagens únicas
            for img in navigation_images:
                if img and img not in all_images:
                    all_images.append(img)
            
            # Limitar ao máximo (mesmo do teste)
            final_images = all_images[:self.max_images_per_product]
            print(f"🎯 RESULTADO: {len(final_images)} imagens extraídas (versão teste)")
            
            return final_images
            
        except Exception as e:
            print(f"❌ Erro na extração: {e}")
            return all_images

    def _find_next_buttons_test_version(self, driver) -> List:
        """COPIAR método exato do teste que funcionou"""
        
        # Mesmos seletores que funcionaram no teste
        selectors = [
            '.fotorama__arr--next',           # Este funcionou!
            '.fotorama__arr[data-side="next"]',
            '.carousel-control-next',
            '.slick-next',                    # Este também funcionou!
            '.swiper-button-next',
            'button[class*="next"]',          # Este também funcionou!
            'button[aria-label*="next"]',
            'button[title*="next"]'
        ]
        
        found_buttons = []
        
        for selector in selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        # Mesmo filtro do teste
                        classes = (button.get_attribute('class') or '').lower()
                        aria = (button.get_attribute('aria-label') or '').lower()
                        
                        if any(word in classes + aria for word in ['prev', 'previous', 'back']):
                            continue
                        
                        found_buttons.append(button)
                        print(f"   Botão encontrado: {selector}")
                        break  # Mesmo comportamento do teste
                        
            except Exception as e:
                continue
        
        # Mesmo algoritmo de remoção de duplicatas do teste
        unique_buttons = []
        for button in found_buttons:
            try:
                location = button.location
                if not any(btn.location == location for btn in unique_buttons):
                    unique_buttons.append(button)
            except:
                unique_buttons.append(button)
        
        return unique_buttons

    def _get_current_carousel_image_test_version(self, driver) -> Optional[str]:
        """COPIAR método exato do teste que funcionou"""
        
        # Mesmos seletores que funcionaram no teste
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
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        # Mesma verificação de tamanho do teste
                        size = element.size
                        if size.get('width', 0) > 200 and size.get('height', 0) > 200:
                            
                            # Mesma ordem de atributos do teste
                            for attr in ['data-zoom-image', 'data-large-image', 'data-src', 'src']:
                                url = element.get_attribute(attr)
                                if url and self._is_valid_product_image_url(url):
                                    return self._resolve_image_url_test_version(url)
            except:
                continue
        
        return None

    def _navigate_with_arrows_test_version(self, driver, next_button) -> List[str]:
        """COPIAR método exato do teste que funcionou"""
        
        navigation_images = []
        max_clicks = 8  # Mesmo valor do teste que funcionou
        
        print(f"🔄 Navegando: máximo {max_clicks} cliques")
        
        for click_num in range(max_clicks):
            try:
                print(f"   Clique {click_num + 1}/{max_clicks}")
                
                # Mesmas verificações do teste
                if not next_button.is_displayed() or not next_button.is_enabled():
                    print("      Botão não disponível - parando")
                    break
                
                # Capturar imagem antes (mesmo método do teste)
                image_before = self._get_current_carousel_image_test_version(driver)
                
                # Mesmo scroll do teste
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", 
                    next_button
                )
                time.sleep(1)  # Mesmo timing do teste
                
                # Mesmo método de clique do teste
                clicked = self._click_button_robust_test_version(driver, next_button)
                if not clicked:
                    print("      Falha ao clicar - parando")
                    break
                
                # Mesmo tempo de espera do teste
                time.sleep(3)
                
                # Capturar nova imagem (mesmo método do teste)
                image_after = self._get_current_carousel_image_test_version(driver)
                
                # Mesma lógica de verificação do teste
                if image_after and image_after != image_before:
                    if image_after not in navigation_images:
                        navigation_images.append(image_after)
                        print("      ✅ Nova imagem capturada")
                    else:
                        print("      ⚠️ Imagem duplicada")
                elif image_after == image_before:
                    print("      ⚠️ Imagem não mudou - possível fim do carrossel")
                    if click_num >= 2:  # Mesma lógica do teste
                        break
                else:
                    print("      ❌ Erro ao capturar nova imagem")
                
            except Exception as e:
                print(f"      ❌ Erro no clique {click_num + 1}: {e}")
                continue
        
        print(f"   Resultado: {len(navigation_images)} imagens via setas")
        return navigation_images

    def _click_button_robust_test_version(self, driver, button) -> bool:
        """COPIAR método exato do teste que funcionou"""
        
        # Mesmas estratégias do teste
        strategies = [
            ('Normal', lambda: button.click()),
            ('JavaScript', lambda: driver.execute_script("arguments[0].click();", button)),
            ('ActionChains', lambda: ActionChains(driver).move_to_element(button).click().perform())
        ]
        
        for name, strategy in strategies:
            try:
                strategy()
                return True
            except Exception as e:
                continue
        
        return False

    def _resolve_image_url_test_version(self, url: str) -> str:
        """COPIAR método exato do teste que funcionou"""
        if not url:
            return url
        
        if url.startswith('//'):
            return f"https:{url}"
        elif url.startswith('/'):
            return f"https://nissei.com{url}"
        else:
            return url

    def _extract_thumbnail_images(self, driver) -> List[str]:
        """Extrai imagens de thumbnails como fallback"""
        thumb_images = []
        
        thumb_selectors = [
            '.fotorama__nav__frame img',
            '.thumbnails img',
            '.thumb img',
            '[class*="thumb"] img'
        ]
        
        for selector in thumb_selectors:
            try:
                thumbnails = driver.find_elements(By.CSS_SELECTOR, selector)
                for thumb in thumbnails[:4]:  # Máximo 4 thumbnails
                    try:
                        for attr in ['data-zoom-image', 'data-large-image', 'data-src', 'src']:
                            url = thumb.get_attribute(attr)
                            if url and self._is_valid_product_image_url(url):
                                resolved = self._resolve_image_url(url)
                                if resolved and resolved not in thumb_images:
                                    thumb_images.append(resolved)
                                break
                    except:
                        continue
            except:
                continue
        
        return thumb_images

    def _extract_all_visible_product_images(self, driver) -> List[str]:
        """Fallback: extrai todas as imagens de produto visíveis"""
        try:
            all_images = driver.find_elements(By.TAG_NAME, 'img')
            product_images = []
            
            for img in all_images:
                try:
                    if self._looks_like_product_image_element(img):
                        for attr in ['data-zoom-image', 'data-src', 'src']:
                            url = img.get_attribute(attr)
                            if url and self._is_valid_product_image_url(url):
                                resolved = self._resolve_image_url(url)
                                if resolved and resolved not in product_images:
                                    product_images.append(resolved)
                                break
                except:
                    continue
            
            return product_images[:self.max_images_per_product]
            
        except Exception as e:
            print(f"Erro no fallback: {e}")
            return []

    def _looks_like_product_image_element(self, img_element) -> bool:
        """Verifica se elemento é imagem de produto"""
        try:
            src = img_element.get_attribute('src') or ''
            data_src = img_element.get_attribute('data-src') or ''
            classes = img_element.get_attribute('class') or ''
            
            # URLs de produto
            if any(keyword in (src + data_src).lower() for keyword in ['catalog', 'media', 'product']):
                return True
            
            # Classes de produto
            if any(keyword in classes.lower() for keyword in ['product', 'gallery', 'fotorama']):
                return True
            
            return False
        except:
            return False

    def _navigate_carousel_with_arrows(self, driver, next_button) -> List[str]:
        """Navega pelo carrossel usando setas"""
        
        navigation_images = []
        max_clicks = 6  # Reduzido de 8 para 6 para produção
        
        print(f"🔄 Navegando por setas (máx {max_clicks} cliques)...")
        
        for click_num in range(max_clicks):
            try:
                # Verificar se botão ainda funciona
                if not next_button.is_displayed() or not next_button.is_enabled():
                    print(f"   Botão não disponível no clique {click_num + 1}")
                    break
                
                # Capturar imagem antes
                image_before = self._get_current_carousel_image(driver)
                
                # Scroll e clicar
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(1)
                
                # Múltiplas estratégias de clique
                clicked = self._click_button_robust(driver, next_button)
                if not clicked:
                    print(f"   Falha ao clicar no botão {click_num + 1}")
                    break
                
                # Aguardar transição
                time.sleep(2)  # Era 3, reduzido para 2 em produção
                
                # Capturar nova imagem
                image_after = self._get_current_carousel_image(driver)
                
                # Verificar mudança
                if image_after and image_after != image_before:
                    if image_after not in navigation_images:
                        navigation_images.append(image_after)
                        print(f"   ✅ Clique {click_num + 1}: nova imagem")
                    else:
                        print(f"   ⚠️ Clique {click_num + 1}: imagem duplicada")
                elif image_after == image_before:
                    print(f"   ⚠️ Clique {click_num + 1}: sem mudança")
                    if click_num >= 2:  # Parar após 3 tentativas sem mudança
                        break
                
            except Exception as e:
                print(f"   ❌ Erro no clique {click_num + 1}: {str(e)[:50]}")
                continue
        
        print(f"   Resultado: {len(navigation_images)} imagens via setas")
        return navigation_images

    def _click_button_robust(self, driver, button) -> bool:
        """Clique robusto com múltiplas estratégias"""
        
        strategies = [
            lambda: button.click(),
            lambda: driver.execute_script("arguments[0].click();", button),
            lambda: ActionChains(driver).move_to_element(button).click().perform()
        ]
        
        for strategy in strategies:
            try:
                strategy()
                return True
            except:
                continue
        
        return False

    def _extract_fotorama_data_attributes_enhanced(self, driver) -> List[str]:
        """Extrai imagens dos data attributes no HTML atual"""
        fallback_images = []
        
        try:
            # Obter HTML atual (após JavaScript)
            current_html = driver.page_source
            soup = BeautifulSoup(current_html, 'html.parser')
            
            # Procurar elementos com data attributes de imagens
            image_data_selectors = [
                '[data-src*="catalog"]',
                '[data-full*="catalog"]', 
                '[data-zoom*="catalog"]',
                '.fotorama [data-src]',
                '.fotorama__nav [data-src]'
            ]
            
            for selector in image_data_selectors:
                try:
                    elements = soup.select(selector)
                    for element in elements:
                        for attr in ['data-src', 'data-full', 'data-zoom', 'src']:
                            img_url = element.get(attr)
                            if img_url:
                                # Resolver URL
                                if img_url.startswith('//'):
                                    img_url = f"https:{img_url}"
                                elif img_url.startswith('/'):
                                    img_url = f"{self.base_url}{img_url}"
                                
                                if img_url.startswith('http') and self._is_valid_product_image_url(img_url):
                                    fallback_images.append(img_url)
                                break
                except:
                    continue
                    
        except Exception as e:
            print(f"Erro no fallback de data attributes: {e}")
        
        return list(set(fallback_images))

    def _wait_for_carousel_loading(self, driver) -> bool:
        """Aguarda carrossel carregar com múltiplas estratégias"""
        try:
            # Estratégia 1: Aguardar Fotorama específico
            for selector in ['.fotorama__stage', '.fotorama__nav', '[data-fotorama]']:
                try:
                    WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    time.sleep(3)  # Aguardar inicialização JS
                    return True
                except TimeoutException:
                    continue
            
            # Estratégia 2: Aguardar qualquer galeria
            for selector in ['.gallery img', '.product-image img', 'img[src*="catalog"]']:
                try:
                    WebDriverWait(driver, 6).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    time.sleep(2)
                    return True
                except TimeoutException:
                    continue
            
            return False
            
        except Exception as e:
            print(f"Erro ao aguardar carrossel: {e}")
            return False

    def _extract_fotorama_fallback_static(self, soup: BeautifulSoup) -> List[str]:
        """Fallback estático quando Selenium não está disponível"""
        print("🔍 Fallback: extração estática de imagens Fotorama...")
        
        static_selectors = [
            '.fotorama img[src*="catalog"]',
            '.fotorama img[data-src*="catalog"]',
            '.fotorama [data-full*="catalog"]',
            '[data-fotorama] img[src]',
            '.gallery img[src*="catalog"]'
        ]
        
        static_images = []
        for selector in static_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    for attr in ['src', 'data-src', 'data-full']:
                        url = element.get(attr)
                        if url:
                            if url.startswith('//'):
                                url = f"https:{url}"
                            elif url.startswith('/'):
                                url = f"{self.base_url}{url}"
                            
                            if url.startswith('http') and self._is_valid_product_image_url(url):
                                static_images.append(url)
                            break
            except:
                continue
        
        return list(set(static_images))[:self.max_images_per_product]

    def _process_fotorama_results(self, image_candidates: List) -> List[str]:
        """Processa e retorna os resultados finais das imagens Fotorama"""
        if not image_candidates:
            print("❌ Nenhuma imagem extraída do carrossel Fotorama")
            return []
        
        # Remover duplicatas e ordenar por score
        unique_images = {}
        for url, score, source in image_candidates:
            if url not in unique_images or score > unique_images[url][0]:
                unique_images[url] = (score, source)
        
        # Ordenar por score
        sorted_images = sorted(unique_images.items(), key=lambda x: x[1][0], reverse=True)
        
        # Retornar URLs das melhores imagens
        result = []
        for url, (score, source) in sorted_images[:self.max_images_per_product]:
            result.append(url)
            print(f"✅ Fotorama final: {source} (score: {score}) - {url[:60]}...")
        
        print(f"🎠 {len(result)} imagens extraídas do carrossel Fotorama")
        return result

    def _navigate_fotorama_with_arrows(self, driver, image_candidates: List):
        """Navega pelo Fotorama usando botões de seta"""
        try:
            # Procurar botões de navegação
            arrow_selectors = [
                '.fotorama__arr--next',
                '.fotorama__arr--prev', 
                '.fotorama__arr[data-side="next"]',
                '.fotorama__arr[data-side="prev"]'
            ]
            
            next_button = None
            for selector in arrow_selectors:
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and 'next' in selector:
                            next_button = button
                            break
                    if next_button:
                        break
                except:
                    continue
            
            if next_button:
                print("   🔍 Navegando com botões de seta...")
                for i in range(6):  # Máximo 6 navegações
                    try:
                        driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(2)
                        
                        # Extrair imagem após navegação
                        new_images = self._extract_fotorama_active_image(driver)
                        for img_url in new_images:
                            if img_url and not any(img_url == candidate[0] for candidate in image_candidates):
                                image_candidates.append((img_url, 12, f'fotorama-arrow-{i+1}'))
                                print(f"   → Seta {i+1}: {img_url[:60]}...")
                                
                    except Exception as e:
                        print(f"   ⚠️ Erro navegação {i+1}: {str(e)[:30]}")
                        break
        except Exception as e:
            print(f"Erro na navegação por setas: {e}")

    def _extract_fotorama_active_image(self, driver) -> List[str]:
        """Extrai a imagem atualmente ativa no Fotorama"""
        active_images = []
        
        # Seletores para imagem ativa
        active_image_selectors = [
            '.fotorama__stage__frame.fotorama__active img[src]',
            '.fotorama__stage__frame.fotorama__active img[data-src]',
            '.fotorama__stage .fotorama__active img',
            '.fotorama__img[src]',
            '.fotorama__stage img.fotorama__img',
            '.fotorama__stage img[src*="catalog"]'
        ]
        
        for selector in active_image_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    # Tentar múltiplos atributos
                    for attr in ['src', 'data-src', 'data-full']:
                        try:
                            img_url = element.get_attribute(attr)
                            if img_url and img_url.startswith(('http', '//')):
                                # Normalizar URL
                                if img_url.startswith('//'):
                                    img_url = f"https:{img_url}"
                                elif img_url.startswith('/'):
                                    img_url = f"{self.base_url}{img_url}"
                                
                                if self._is_valid_product_image_url(img_url):
                                    active_images.append(img_url)
                                break
                        except:
                            continue
            except:
                continue
        
        return list(set(active_images))  # Remover duplicatas

    def _extract_current_fotorama_images(self, driver) -> List[str]:
        """Extrai imagens visíveis no momento atual do Fotorama"""
        current_images = []
        
        # Seletores para imagem ativa no Fotorama
        current_image_selectors = [
            '.fotorama__stage__frame.fotorama__active img',
            '.fotorama__stage__frame.fotorama__active [data-src]',
            '.fotorama__img',
            '.fotorama__stage img[src]',
            '.fotorama__stage [data-src]'
        ]
        
        for selector in current_image_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    # Tentar múltiplos atributos
                    for attr in ['data-full', 'data-src', 'src']:
                        img_url = element.get_attribute(attr)
                        if img_url and img_url.startswith('http'):
                            # Resolver URL completa
                            if img_url.startswith('//'):
                                img_url = f"https:{img_url}"
                            elif img_url.startswith('/'):
                                img_url = f"{self.base_url}{img_url}"
                            
                            if self._is_valid_product_image_url(img_url):
                                current_images.append(img_url)
                            break
            except Exception as e:
                continue
        
        return list(set(current_images))  # Remover duplicatas

    def _extract_fotorama_data_attributes(self, soup: BeautifulSoup) -> List[str]:
        """Extrai URLs de imagens dos data attributes do Fotorama"""
        fallback_images = []
        
        # Procurar por elementos com data attributes do Fotorama
        fotorama_elements = soup.find_all(['img', 'div', 'a'], attrs={
            'data-src': True
        })
        
        fotorama_elements += soup.find_all(['img', 'div', 'a'], attrs={
            'data-full': True
        })
        
        for element in fotorama_elements:
            for attr in ['data-full', 'data-src', 'data-zoom']:
                img_url = element.get(attr)
                if img_url:
                    # Resolver URL
                    if img_url.startswith('//'):
                        img_url = f"https:{img_url}"
                    elif img_url.startswith('/'):
                        img_url = f"{self.base_url}{img_url}"
                    
                    if img_url.startswith('http') and self._is_valid_product_image_url(img_url):
                        fallback_images.append(img_url)
                    break
        
        return list(set(fallback_images))

    def _is_valid_product_image_url(self, url: str) -> bool:
        """Verificar se este método já existe na classe. Se não, adicionar."""
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

    def _extract_description_priority_fixed(self, soup: BeautifulSoup, driver=None) -> str:
        """
        Extração com prioridade CORRIGIDA:
        1° PRIORIDADE ABSOLUTA: "Más Información" 
        2° FALLBACK: "Detalles"
        3° ÚLTIMO RECURSO: Descrição genérica
        
        IMPORTANTE: Só vai para próximo nível se NÃO encontrar nada no anterior
        """
        print("📝 Extraindo descrição com prioridade FIXA: Más Información → Detalles → Genérica")
        
        # ===============================================
        # NÍVEL 1: MÁS INFORMACIÓN (PRIORIDADE ABSOLUTA)
        # ===============================================
        print("🔍 NÍVEL 1: Buscando 'Más Información'...")
        
        mas_info_description = self._extract_mas_informacion_specifically(soup, driver)
        if mas_info_description:
            print(f"✅ 'Más Información' ENCONTRADO! ({len(mas_info_description)} caracteres)")
            return mas_info_description
        
        print("❌ 'Más Información' NÃO encontrado")
        
        # ===============================================  
        # NÍVEL 2: DETALLES (FALLBACK)
        # ===============================================
        print("🔍 NÍVEL 2: Buscando 'Detalles'...")
        
        detalles_description = self._extract_detalles_specifically(soup, driver)
        if detalles_description:
            print(f"⚠️ Usando 'Detalles' como fallback ({len(detalles_description)} caracteres)")
            return detalles_description
        
        print("❌ 'Detalles' NÃO encontrado")
        
        # ===============================================
        # NÍVEL 3: GENÉRICO (ÚLTIMO RECURSO) 
        # ===============================================
        print("🔍 NÍVEL 3: Buscando descrição genérica...")
        
        generic_description = self._extract_generic_description(soup)
        if generic_description:
            print(f"⚠️ Usando descrição genérica como último recurso ({len(generic_description)} caracteres)")
            return generic_description
        
        print("❌ Nenhuma descrição encontrada")
        return ""

    def _extract_mas_informacion_specifically(self, soup: BeautifulSoup, driver=None) -> str:
        """Busca ESPECIFICAMENTE por 'Más Información' nos seletores corretos do Nissei"""
        
        print("🔍 Buscando 'Más Información' nos seletores específicos do Nissei...")
        
        # SELETORES CORRETOS baseados na estrutura real do site
        mas_info_selectors = [
            # Seletor específico identificado pelo usuário
            '#additional table#product-attribute-specs-table',
            '.data.item.content.allow#additional table.additional-attributes',
            '#additional .additional-attributes-wrapper table',
            
            # Seletores relacionados
            '[data-role="content"]#additional table',
            '.additional-attributes-wrapper table.data.table',
            '#product-attribute-specs-table',
            
            # Fallbacks
            '#additional',
            '.additional-attributes-wrapper',
            '[id="additional"]'
        ]
        
        for selector in mas_info_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    # Se é uma tabela, extrair de forma estruturada
                    if elem.name == 'table' or elem.select('table'):
                        table_content = self._extract_table_content_structured(elem)
                        if table_content and len(table_content) > 50:
                            print(f"✅ 'Más Información' extraído de tabela: {selector}")
                            return self._clean_description_content(table_content)
                    else:
                        # Extrair texto normal
                        content = elem.get_text(separator='\n', strip=True)
                        if content and len(content) > 50:
                            print(f"✅ 'Más Información' extraído: {selector}")
                            return self._clean_description_content(content)
            except Exception as e:
                print(f"Erro no seletor {selector}: {e}")
                continue
        
        # ESTRATÉGIA JAVASCRIPT: Ativar aba se necessário
        if driver:
            try:
                print("🔍 Tentando ativar aba 'Más Información' via JavaScript...")
                
                # Procurar por links/botões que ativem a seção adicional
                activation_selectors = [
                    "a[href='#additional']",
                    "button[data-target='#additional']",
                    "[data-role='tab'][href='#additional']",
                    "a[aria-controls='additional']"
                ]
                
                for selector in activation_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed():
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(2)
                                print(f"🖱️ Aba ativada: {selector}")
                                
                                # Re-extrair após ativação
                                updated_soup = BeautifulSoup(driver.page_source, 'html.parser')
                                
                                for sel in mas_info_selectors[:3]:  # Principais seletores
                                    try:
                                        elements = updated_soup.select(sel)
                                        for elem in elements:
                                            if elem.name == 'table' or elem.select('table'):
                                                table_content = self._extract_table_content_structured(elem)
                                                if table_content and len(table_content) > 50:
                                                    print(f"✅ 'Más Información' via JS: {sel}")
                                                    return self._clean_description_content(table_content)
                                            else:
                                                content = elem.get_text(separator='\n', strip=True)
                                                if content and len(content) > 50:
                                                    print(f"✅ 'Más Información' via JS: {sel}")
                                                    return self._clean_description_content(content)
                                    except:
                                        continue
                                break
                    except:
                        continue
            except Exception as e:
                print(f"Erro na ativação JS: {e}")
        
        print("❌ 'Más Información' não encontrado")
        return ""

    def _extract_table_content_structured(self, table_element) -> str:
        """Extrai conteúdo estruturado de tabelas (para Más Información)"""
        try:
            if table_element.name != 'table':
                # Se não é table, procurar table dentro
                table = table_element.select_one('table')
                if not table:
                    return table_element.get_text(separator='\n', strip=True)
                table_element = table
            
            rows = table_element.find_all('tr')
            if not rows:
                return ""
            
            table_content = []
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # Tabela com chave-valor
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        table_content.append(f"{key}: {value}")
                elif len(cells) == 1:
                    # Célula única - pode ser título ou descrição
                    cell_text = cells[0].get_text(strip=True)
                    if cell_text and len(cell_text) > 5:
                        table_content.append(cell_text)
            
            if table_content:
                return '\n'.join(table_content)
            else:
                # Fallback: extrair todo texto da tabela
                return table_element.get_text(separator='\n', strip=True)
                
        except Exception as e:
            print(f"Erro na extração de tabela: {e}")
            return table_element.get_text(separator='\n', strip=True) if table_element else ""

    def _extract_detalles_specifically(self, soup: BeautifulSoup, driver=None) -> str:
        """Busca ESPECIFICAMENTE por 'Detalles' nos seletores corretos do Nissei"""
        
        print("🔍 Buscando 'Detalles' nos seletores específicos do Nissei...")
        
        # SELETORES CORRETOS baseados na estrutura real do site
        detalles_selectors = [
            # Seletor específico identificado pelo usuário
            '.product.attribute.description',
            'div.product.attribute.description',
            
            # Seletores relacionados
            '.product.attribute.description .value',
            '.product-attribute-description',
            '.attribute.description .value',
            
            # Fallbacks
            '.product.description',
            '.attribute.description'
        ]
        
        for selector in detalles_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    content = elem.get_text(separator='\n', strip=True)
                    if content and len(content) > 50:
                        print(f"✅ 'Detalles' extraído: {selector}")
                        return self._clean_description_content(content)
            except Exception as e:
                print(f"Erro no seletor {selector}: {e}")
                continue
        
        # ESTRATÉGIA JAVASCRIPT para Detalles também
        if driver:
            try:
                print("🔍 Tentando encontrar 'Detalles' via JavaScript...")
                
                # Procurar elementos que possam conter descrição do produto
                js_selectors = [
                    '.product.attribute.description',
                    '[data-role="content"] .product.description'
                ]
                
                for sel in js_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, sel)
                        for element in elements:
                            if element.is_displayed():
                                content = element.text.strip()
                                if content and len(content) > 50:
                                    print(f"✅ 'Detalles' via JS: {sel}")
                                    return self._clean_description_content(content)
                    except:
                        continue
            except Exception as e:
                print(f"Erro na busca JS de Detalles: {e}")
        
        print("❌ 'Detalles' não encontrado")
        return ""

    def _extract_generic_description(self, soup: BeautifulSoup) -> str:
        """Busca descrição genérica como último recurso"""
        
        generic_selectors = [
            '.product-description',
            '[itemprop="description"]',
            '.product-info .value',
            '.product-attribute-description',
            '.description'
        ]
        
        for selector in generic_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    content = elem.get_text(separator='\n', strip=True)
                    if content and len(content) > 100:  # Critério mais alto para genérico
                        print(f"⚠️ Descrição genérica: {selector}")
                        return self._clean_description_content(content)
            except:
                continue
        
        return ""

    def _clean_description_content(self, content: str) -> str:
        """Limpa conteúdo da descrição"""
        if not content:
            return ""
        
        # Remover padrões inúteis
        cleanup_patterns = [
            r'Compartilhar.*?Facebook.*?Twitter.*?WhatsApp',
            r'Adicionar à lista.*?favoritos', 
            r'Comprar agora.*?Adicionar ao carrinho',
            r'Enviar para um amigo',
            r'Imprimir esta página',
            r'Añadir a favoritos',
            r'Compartir en.*?Facebook.*?Twitter',
            r'Mas información.*?Detalles.*?Especificaciones'  # Evitar texto de navegação
        ]
        
        cleaned = content
        for pattern in cleanup_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
        
        # Remover múltiplas quebras de linha
        cleaned = re.sub(r'\n\s*\n', '\n', cleaned)
        
        # Limitar tamanho
        if len(cleaned) > 2000:
            cleaned = cleaned[:2000] + "... [conteúdo truncado]"
        
        return cleaned.strip()

    def _generate_extraction_prompt(self, url: str, html_summary: str) -> str:
        """Gera prompt otimizado para extrair seções específicas"""
        
        base_prompt = f"""
    Analise este HTML de uma página de produto do Nissei.com (Paraguay) e extraia informações estruturadas.

    URL: {url}

    INSTRUÇÕES ESPECÍFICAS:
    - Procure por seções "Más Información", "Detalles", "Descripción"
    - Extraia especificações técnicas de tabelas
    - Identifique o nome exato do produto
    - Encontre o preço em Guaranis (Gs.)
    - Localize URLs de imagens de alta qualidade

    HTML da página:
    {html_summary}

    Extraia APENAS as seguintes informações se estiverem claramente presentes:

    1. Nome completo do produto (título principal)
    2. Preço atual em Guaranis (busque números com Gs. ou ₲)
    3. Preço original se houver desconto
    4. Descrição detalhada (conteúdo das seções "Más Información" ou "Detalles")
    5. URLs completas de imagens do produto (priorize imagens grandes/zoom)
    6. Especificações técnicas (tabelas com características)
    7. Disponibilidade/estoque
    8. Marca do produto

    FORMATO DE RESPOSTA (JSON válido):
    {{
        "name": "nome completo do produto",
        "price": número_decimal_ou_null,
        "original_price": número_decimal_ou_null,
        "description": "descrição completa das seções de detalhes",
        "image_urls": ["url1", "url2"],
        "specifications": {{"característica1": "valor1", "característica2": "valor2"}},
        "availability": "texto de disponibilidade",
        "brand": "marca"
    }}

    IMPORTANTE:
    - Responda APENAS com JSON válido
    - Use null para campos não encontrados
    - URLs devem ser completas (começar com http)
    - Preços devem ser apenas números
    - Priorize informações das seções "Más Información" e "Detalles"
    """
        
        # Ajustar prompt baseado no modelo
        model_type = self.configuration.model_integration.lower() if self.configuration else ""
        
        if 'claude' in model_type or 'anthropic' in model_type:
            return base_prompt
        elif 'openai' in model_type or 'gpt' in model_type:
            return f"You are a web scraping expert specialized in e-commerce sites. {base_prompt}"
        else:
            return base_prompt
    
    def _call_ai_api(self, prompt: str) -> str:
        """Chama a API de IA baseada na configuração"""
        try:
            model_type = self.configuration.model_integration.lower()
            
            if 'claude' in model_type or 'anthropic' in model_type:
                return self._call_claude_api(prompt)
            
            elif 'openai' in model_type or 'gpt' in model_type:
                return self._call_openai_api(prompt)
            
            else:
                print(f"Modelo não suportado: {self.configuration.model_integration}")
                return ""
                
        except Exception as e:
            print(f"Erro ao chamar API de IA: {e}")
            return ""
    
    def _call_claude_api(self, prompt: str) -> str:
        """Chama a API do Claude/Anthropic"""
        try:
            # Parâmetros da configuração
            params = self.configuration.parameters or {}
            model = params.get('model', 'claude-3-sonnet-20240229')
            max_tokens = params.get('max_tokens', 2000)
            
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.configuration.token,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["content"][0]["text"]
            else:
                print(f"Erro na API Claude: {response.status_code}")
                print(f"Resposta: {response.text}")
                
        except Exception as e:
            print(f"Erro ao chamar Claude API: {e}")
        
        return ""
    
    def _call_openai_api(self, prompt: str) -> str:
        """Chama a API do OpenAI"""
        try:
            # Parâmetros da configuração
            params = self.configuration.parameters or {}
            model = params.get('model', 'gpt-3.5-turbo')
            max_tokens = params.get('max_tokens', 2000)
            temperature = params.get('temperature', 0.1)
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.configuration.token}"
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": "You are a web scraping expert that extracts product data from HTML."},
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                print(f"Erro na API OpenAI: {response.status_code}")
                print(f"Resposta: {response.text}")
                
        except Exception as e:
            print(f"Erro ao chamar OpenAI API: {e}")
        
        return ""
    
    # Métodos auxiliares (mantendo os mesmos da versão anterior)
    def _extract_with_requests(self, url: str) -> Dict[str, Any]:
        """Extração básica com requests"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            return self._extract_basic_data(soup)
        except Exception as e:
            print(f"Requests falhou: {e}")
            return {}
    
    def _extract_with_selenium(self, url: str) -> tuple[Dict[str, Any], str]:
        """Extração com Selenium + JavaScript"""
        if not self.driver:
            print("Selenium não disponível")
            return {}, ""
        
        try:
            print(f"Acessando com Selenium: {url}")
            self.driver.get(url)
            
            # Aguardar carregamento básico
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Aguardar conteúdo específico carregar
            self._wait_for_dynamic_content()
            
            # Obter HTML renderizado
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extrair dados com seletores avançados
            selenium_data = self._extract_advanced_data(soup)
            
            return selenium_data, html_content
            
        except Exception as e:
            print(f"Selenium falhou: {e}")
            return {}, ""
    
    def _wait_for_dynamic_content(self):
        """Versão melhorada para aguardar carrossel"""
        
        # Aguardar carregamento básico
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass
        
        # Aguardar carrossel especificamente
        carousel_loaded = self._wait_for_carousel_loading(self.driver)
        if not carousel_loaded:
            # Aguardar imagens gerais
            try:
                WebDriverWait(self.driver, 8).until(
                    lambda d: len(d.find_elements(By.CSS_SELECTOR, "img[src]")) > 3
                )
            except:
                pass
        
        # Aguardar JavaScript inicializar
        time.sleep(3)  # Era 1, aumentado para 3
        
        # Tentar ativar abas (mantido do código original)
        try:
            self._activate_detail_tabs()
        except Exception as e:
            print(f"⚠️ Erro ao ativar abas: {str(e)[:50]}")
        
        # Aguardar final
        time.sleep(2)

    # 2. ADICIONE este novo método à classe
    def _close_overlays_and_modals(self):
        """Fecha overlays, cookies e modals que podem interceptar clicks"""
        
        # Seletores comuns para fechar overlays
        close_selectors = [
            # Cookie banners
            "button[id*='cookie'] .close",
            ".cookie-banner .close",
            ".cookie-notice button",
            "[aria-label*='close cookie']",
            # Modals genéricos
            ".modal .close",
            ".popup .close",
            ".overlay .close",
            "button[aria-label='Close']",
            "button[data-dismiss='modal']",
            # X buttons
            ".close-button",
            ".btn-close"
        ]
        
        overlays_closed = 0
        
        for selector in close_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements[:2]:  # Máximo 2 por tipo
                    try:
                        if element.is_displayed():
                            element.click()
                            overlays_closed += 1
                            time.sleep(0.5)  # Aguardar fechar
                            print(f"🗂️ Overlay fechado: {selector}")
                    except:
                        continue
            except:
                continue
        
        # Tentar pressionar ESC para fechar modals
        if overlays_closed > 0:
            try:
                from selenium.webdriver.common.keys import Keys
                self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                time.sleep(0.5)
            except:
                pass


    def _activate_detail_tabs(self):
        """Ativa abas de detalhes com handling robusto de clicks"""
        
        # PRIMEIRO: Fechar possíveis overlays/modals que podem interceptar clicks
        self._close_overlays_and_modals()
        
        tab_selectors = [
            # Texto específico das abas (mais confiáveis)
            "//a[contains(text(), 'Detalles')]",
            "//button[contains(text(), 'Detalles')]", 
            "//a[contains(text(), 'Más Información')]",
            "//button[contains(text(), 'Más Información')]",
            "//a[contains(text(), 'Descripción')]",
            # Classes comuns de abas
            ".tab[data-toggle]",
            "[role='tab']",
            ".nav-link[data-toggle]"
        ]
        
        tabs_clicked = 0
        max_tabs_to_try = 3  # Limitar para não perder tempo
        
        for selector in tab_selectors:
            if tabs_clicked >= max_tabs_to_try:
                break
                
            try:
                if selector.startswith("//"):
                    elements = self.driver.find_elements(By.XPATH, selector)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements[:2]:  # Máximo 2 por seletor
                    if tabs_clicked >= max_tabs_to_try:
                        break
                        
                    try:
                        if element.is_displayed() and element.is_enabled():
                            # Estratégia robusta de click
                            success = self._robust_click(element, selector)
                            if success:
                                tabs_clicked += 1
                                time.sleep(1)  # Só 1 segundo para carregar
                                print(f"✅ Aba ativada: {selector}")
                            
                    except Exception as e:
                        print(f"⚠️ Erro específico na aba {selector}: {str(e)[:100]}")
                        continue
                        
            except Exception as e:
                continue
        
        print(f"📊 Total de abas ativadas: {tabs_clicked}")
    
    def _robust_click(self, element, selector_info: str) -> bool:
        """Método robusto para clicar em elementos com múltiplas estratégias"""
        
        strategies = [
            self._try_normal_click,
            self._try_scroll_and_click,
            self._try_javascript_click,
            self._try_action_chains_click
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                print(f"  🎯 Tentativa {i}: {strategy.__name__}")
                success = strategy(element)
                if success:
                    return True
                time.sleep(0.5)  # Pequena pausa entre tentativas
            except Exception as e:
                print(f"    ❌ Estratégia {i} falhou: {str(e)[:50]}")
                continue
        
        print(f"  ❌ Todas as estratégias falharam para: {selector_info}")
        return False

    def _try_normal_click(self, element) -> bool:
        """Tentativa 1: Click normal"""
        element.click()
        return True

    def _try_scroll_and_click(self, element) -> bool:
        """Tentativa 2: Scroll até elemento e click"""
        # Scroll para tornar elemento visível
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(1)
        
        # Aguardar ser clicável
        from selenium.webdriver.support import expected_conditions as EC
        WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable(element))
        
        element.click()
        return True

    def _try_javascript_click(self, element) -> bool:
        """Tentativa 3: Click via JavaScript (contorna overlays)"""
        self.driver.execute_script("arguments[0].click();", element)
        return True

    def _try_action_chains_click(self, element) -> bool:
        """Tentativa 4: Action chains click"""
        from selenium.webdriver.common.action_chains import ActionChains
        
        actions = ActionChains(self.driver)
        actions.move_to_element(element).click().perform()
        return True

    def _extract_basic_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extração básica com seletores tradicionais - INCLUINDO IMAGENS"""
        data = {}
        
        # Nome básico
        name_selectors = ['h1.page-title span', 'h1.page-title', 'h1']
        name = self._extract_text_by_selectors(soup, name_selectors)
        if name:
            data['name'] = name
        
        # Preço básico
        price_selectors = ['.price-wrapper .price', '.price-box .price', '[class*="price"]']
        price_text = self._extract_text_by_selectors(soup, price_selectors)
        if price_text:
            data['price'] = self._parse_guarani_price(price_text)
        
        # Descrição básica
        desc_selectors = ['#product-description-content', '.product.attribute.description .value']
        description = self._extract_text_by_selectors(soup, desc_selectors)
        if description:
            data['description'] = description
        
        # ✅ ADICIONAR: Extração básica de imagens
        image_urls = self._extract_images_basic(soup)
        if image_urls:
            data['image_urls'] = image_urls
            print(f"📸 Encontradas {len(image_urls)} imagens via requests básico")
        else:
            print("📸 Nenhuma imagem encontrada via requests básico")
        
        return data

    def _extract_images_basic(self, soup: BeautifulSoup) -> List[str]:
        """Extração básica de imagens para o método requests"""
        image_candidates = []
        
        # Seletores básicos para imagens de produto
        basic_selectors = [
            # Nissei específico
            '.fotorama img',
            '.product-image img', 
            '.gallery-image img',
            '.main-image img',
            # Genéricos
            '[class*="product"] img[src*="catalog"]',
            '[class*="product"] img[src*="media"]',
            '[class*="gallery"] img',
            '.image-container img',
            # Por data attributes
            'img[data-zoom-image]',
            'img[data-large]',
            'img[data-src*="product"]',
            'img[data-src*="catalog"]'
        ]
        
        # Buscar imagens usando seletores básicos
        for selector in basic_selectors:
            try:
                images = soup.select(selector)
                for img in images:
                    # Tentar múltiplos atributos
                    for attr in ['data-zoom-image', 'data-large', 'data-src', 'src']:
                        url = img.get(attr)
                        if url:
                            # Resolver URL absoluta
                            if url.startswith('//'):
                                full_url = f"https:{url}"
                            elif url.startswith('/'):
                                full_url = f"{self.base_url}{url}"
                            elif url.startswith('http'):
                                full_url = url
                            else:
                                continue
                            
                            # Score básico da imagem
                            score = self._score_product_image_basic(full_url, img)
                            if score > 0:
                                image_candidates.append((full_url, score))
                            break
            except Exception as e:
                print(f"Erro ao buscar imagens com seletor {selector}: {e}")
                continue
        
        # Fallback: buscar todas as imagens e filtrar por URL
        if not image_candidates:
            print("Fallback: buscando todas as imagens...")
            all_images = soup.find_all('img')
            for img in all_images:
                for attr in ['src', 'data-src', 'data-original']:
                    url = img.get(attr)
                    if url and any(keyword in url.lower() for keyword in ['catalog', 'media', 'product', 'gallery']):
                        # Resolver URL
                        if url.startswith('//'):
                            full_url = f"https:{url}"
                        elif url.startswith('/'):
                            full_url = f"{self.base_url}{url}"
                        elif url.startswith('http'):
                            full_url = url
                        else:
                            continue
                        
                        score = self._score_product_image_basic(full_url, img)
                        if score > 0:
                            image_candidates.append((full_url, score))
                        break
        
        # Ordenar por score e retornar as melhores
        if image_candidates:
            # Remover duplicatas
            unique_candidates = {}
            for url, score in image_candidates:
                if url not in unique_candidates or score > unique_candidates[url]:
                    unique_candidates[url] = score
            
            # Ordenar por score
            sorted_images = sorted(unique_candidates.items(), key=lambda x: x[1], reverse=True)
            result = [url for url, score in sorted_images[:self.max_images_per_product]]
            
            print(f"📸 Imagens selecionadas: {result}")
            return result
        
        return []

    def _score_product_image_basic(self, url: str, img_element) -> int:
        """Score básico de relevância da imagem"""
        if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            return -10  # Não é imagem
        
        score = 0
        url_lower = url.lower()
        
        # Indicadores positivos na URL (mais simples)
        positive_keywords = ['product', 'catalog', 'media', 'gallery', 'large', 'zoom']
        score += sum(2 for keyword in positive_keywords if keyword in url_lower)
        
        # Indicadores negativos na URL
        negative_keywords = ['logo', 'icon', 'sprite', 'button', 'arrow', 'thumb', 'mini']
        score -= sum(3 for keyword in negative_keywords if keyword in url_lower)
        
        # Bonus por data attributes especiais
        if img_element.get('data-zoom-image') or img_element.get('data-large'):
            score += 3
        
        # Alt text básico
        alt_text = img_element.get('alt', '').lower()
        if any(keyword in alt_text for keyword in ['product', 'item', 'foto']):
            score += 1
        
        # Evitar imagens muito pequenas por dimensão
        width = img_element.get('width')
        height = img_element.get('height')
        if width and height:
            try:
                w, h = int(width), int(height)
                if w < 100 or h < 100:  # Muito pequena
                    score -= 2
            except:
                pass
        
        return score

    def _extract_advanced_data(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extração avançada após Selenium"""
        data = {}
        
        # NOME com scoring inteligente
        name_candidates = []
        name_selectors = [
            'h1', 'h2', 'h3',
            '[class*="title"]', '[class*="name"]', '[class*="product"]',
            '[itemprop="name"]', '.page-title', '.product-title'
        ]
        
        for selector in name_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and 5 <= len(text) <= 200:
                        score = self._score_product_name(text, elem)
                        name_candidates.append((text, score))
            except:
                continue
        
        if name_candidates:
            name_candidates.sort(key=lambda x: x[1], reverse=True)
            data['name'] = name_candidates[0][0]
        
        # PREÇO com detecção inteligente
        price_candidates = []
        price_selectors = [
            '[class*="price"]', '[data-price]', '[itemprop="price"]',
            '.money', '.amount', '.cost', '.valor', '.precio'
        ]
        
        for selector in price_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if text and any(char in text for char in ['$', '₲', 'gs', '.']):
                        parsed_price = self._parse_guarani_price(text)
                        if parsed_price:
                            price_candidates.append((parsed_price, text))
            except:
                continue
        
        if price_candidates:
            # Pegar o preço que parece mais razoável (não muito baixo/alto)
            price_candidates.sort(key=lambda x: x[0])
            data['price'] = price_candidates[0][0]
        
        # DESCRIÇÃO com busca inteligente
        description = self._extract_description_smart(soup)
        if description:
            data['description'] = description
        
        # IMAGENS com filtragem avançada
        images = self._extract_images_smart(soup)
        if images:
            data['image_urls'] = images
        
        # ESPECIFICAÇÕES
        specs = self._extract_specifications_smart(soup)
        if specs:
            data['specifications'] = specs
        
        return data
    
    def _score_product_name(self, text: str, element) -> int:
        """Score de relevância para nome do produto"""
        score = 0
        text_lower = text.lower()
        
        # Pontos por palavras-chave relevantes
        product_keywords = ['iphone', 'samsung', 'lg', 'apple', 'gb', 'pro', 'max', 'mini', 'plus']
        score += sum(3 for keyword in product_keywords if keyword in text_lower)
        
        # Pontos por tag HTML
        if element.name == 'h1':
            score += 10
        elif element.name == 'h2':
            score += 5
        
        # Pontos por classes CSS
        elem_classes = ' '.join(element.get('class', []))
        if any(keyword in elem_classes.lower() for keyword in ['main', 'primary', 'title', 'product']):
            score += 5
        
        # Penalizar textos muito longos ou muito curtos
        if len(text) < 10 or len(text) > 150:
            score -= 5
        
        return score
    
    def _extract_description_smart(self, soup: BeautifulSoup) -> str:
        """Extração melhorada focada em seções de detalhes específicas"""
        
        descriptions = []
        
        # PRIORIDADE 1: Seções específicas de "Más Información" e "Detalles"
        priority_selectors = [
            # Por ID
            "#mas-informacion", "#more-information", "#detalles", "#details",
            "#description", "#descripcion", "#product-details",
            # Por classes específicas
            ".more-info", ".mas-informacion", ".detalles", ".product-description",
            ".additional-info", ".product-specs", ".product-features",
            ".tab-content", ".tab-pane"
        ]
        
        for selector in priority_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(separator='\n', strip=True)
                    if text and len(text) > 50:
                        descriptions.append(text)
                        print(f"Descrição encontrada em: {selector}")
            except Exception as e:
                continue
        
        # PRIORIDADE 2: Procurar por textos específicos e capturar conteúdo próximo
        for element in soup.find_all(text=True):
            element_text = element.strip().lower()
            if any(keyword in element_text for keyword in ['más información', 'detalles', 'descripción']):
                try:
                    # Pegar o elemento pai e seguintes
                    parent = element.parent
                    if parent:
                        # Procurar elementos irmãos ou filhos com conteúdo
                        for sibling in parent.find_next_siblings():
                            text = sibling.get_text(separator='\n', strip=True)
                            if text and len(text) > 50:
                                descriptions.append(text)
                                print(f"Descrição encontrada próxima ao texto: {element[:50]}")
                                break
                        
                        # Se não encontrou irmãos, tentar elementos filhos
                        if not descriptions:
                            for child in parent.find_all(['div', 'p', 'span']):
                                text = child.get_text(separator='\n', strip=True)
                                if text and len(text) > 50:
                                    descriptions.append(text)
                                    print(f"Descrição encontrada em filho do elemento: {element[:50]}")
                                    break
                except:
                    continue
        
        # PRIORIDADE 3: Buscar em tabelas de especificações (comum em produtos)
        table_selectors = [
            'table.product-specs', 'table.specifications', 'table.details',
            '.spec-table', '.specification-table', '.product-attributes',
            '.additional-attributes-wrapper table'
        ]
        
        for selector in table_selectors:
            try:
                tables = soup.select(selector)
                for table in tables:
                    rows = table.find_all('tr')
                    if len(rows) > 2:  # Pelo menos algumas linhas
                        table_content = []
                        for row in rows:
                            cells = row.find_all(['td', 'th'])
                            if len(cells) >= 2:
                                key = cells[0].get_text(strip=True)
                                value = cells[1].get_text(strip=True)
                                if key and value:
                                    table_content.append(f"{key}: {value}")
                        
                        if table_content:
                            descriptions.append('\n'.join(table_content))
                            print(f"Especificações encontradas em tabela: {selector}")
            except:
                continue
        
        # PRIORIDADE 4: Buscar em elementos com atributos itemprop (dados estruturados)
        structured_selectors = [
            '[itemprop="description"]',
            '[itemprop="additionalProperty"]',
            '.product-attribute-description'
        ]
        
        for selector in structured_selectors:
            try:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(separator='\n', strip=True)
                    if text and len(text) > 50:
                        descriptions.append(text)
                        print(f"Descrição estruturada encontrada: {selector}")
            except:
                continue
        
        # PRIORIDADE 5: Divs com muito conteúdo (fallback)
        if not descriptions:
            print("Tentando fallback - buscar divs com conteúdo substancial...")
            all_divs = soup.find_all('div')
            for div in all_divs:
                text = div.get_text(strip=True)
                # Critérios mais rigorosos para descrições de produto
                if (len(text) > 200 and 
                    text.count('.') > 3 and  # Múltiplas frases
                    text.count(' ') > 30 and  # Muitas palavras
                    len(text.split()) > 40):  # Muitas palavras separadas
                    
                    # Verificar se não é apenas um menu ou lista
                    if not any(nav_word in text.lower() for nav_word in ['menu', 'navegación', 'categorías', 'enlace']):
                        descriptions.append(text)
                        print(f"Descrição encontrada em div genérica")
                        break
        
        # Combinar e limitar descrições
        if descriptions:
            # Remover duplicatas baseadas no tamanho e conteúdo similar
            unique_descriptions = []
            for desc in descriptions:
                # Verificar se não é muito similar a uma já existente
                is_duplicate = False
                for existing in unique_descriptions:
                    if len(set(desc.split()) & set(existing.split())) / len(set(desc.split())) > 0.7:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_descriptions.append(desc)
            
            # Ordenar por tamanho (mais completas primeiro)
            unique_descriptions.sort(key=len, reverse=True)
            
            # Combinar as 2 melhores descrições
            final_description = '\n\n--- DETALLES DEL PRODUCTO ---\n\n'.join(unique_descriptions[:2])
            
            # Limitar tamanho total
            if len(final_description) > 3000:
                final_description = final_description[:3000] + "... [conteúdo truncado]"
            
            return final_description
        
        return ""
    
    def _extract_images_smart(self, soup: BeautifulSoup) -> List[str]:
        """Extração inteligente de imagens"""
        image_candidates = []
        
        # Buscar todas as imagens
        images = soup.find_all('img')
        
        for img in images:
            # Tentar múltiplos atributos
            for attr in ['data-zoom-image', 'data-large', 'data-src', 'src', 'data-original']:
                url = img.get(attr)
                if url:
                    # Resolver URL absoluta
                    if url.startswith('//'):
                        full_url = f"https:{url}"
                    elif url.startswith('/'):
                        full_url = f"{self.base_url}{url}"
                    elif url.startswith('http'):
                        full_url = url
                    else:
                        continue
                    
                    # Score da imagem
                    score = self._score_product_image(full_url, img)
                    if score > 0:
                        image_candidates.append((full_url, score))
                    break
        
        # Ordenar por score e retornar as melhores
        if image_candidates:
            image_candidates.sort(key=lambda x: x[1], reverse=True)
            return [url for url, score in image_candidates[:self.max_images_per_product]]
        
        return []
    
    def _score_product_image(self, url: str, img_element) -> int:
        """Score de relevância da imagem"""
        if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            return -10  # Não é imagem
        
        score = 0
        url_lower = url.lower()
        
        # Indicadores positivos na URL
        positive_keywords = ['product', 'catalog', 'media', 'gallery', 'large', 'zoom', 'full']
        score += sum(3 for keyword in positive_keywords if keyword in url_lower)
        
        # Indicadores negativos na URL
        negative_keywords = ['logo', 'icon', 'sprite', 'button', 'arrow', 'small', 'thumb', 'mini']
        score -= sum(5 for keyword in negative_keywords if keyword in url_lower)
        
        # Alt text relevante
        alt_text = img_element.get('alt', '').lower()
        if any(keyword in alt_text for keyword in ['product', 'item', 'photo']):
            score += 2
        
        # Dimensões (se disponíveis)
        width = img_element.get('width')
        height = img_element.get('height')
        if width and height:
            try:
                w, h = int(width), int(height)
                if w >= 300 and h >= 300:  # Imagem grande
                    score += 5
                elif w < 100 or h < 100:  # Muito pequena
                    score -= 3
            except:
                pass
        
        # Atributos especiais (zoom, large, etc.)
        if img_element.get('data-zoom-image') or img_element.get('data-large'):
            score += 5
        
        return score
    
    def _extract_specifications_smart(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extração inteligente de especificações"""
        specs = {}
        
        # Buscar em tabelas
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    if key and value and len(key) < 50 and len(value) < 200:
                        specs[key] = value
        
        # Buscar em listas de definição
        dls = soup.find_all('dl')
        for dl in dls:
            terms = dl.find_all('dt')
            descriptions = dl.find_all('dd')
            for term, desc in zip(terms, descriptions):
                key = term.get_text(strip=True)
                value = desc.get_text(strip=True)
                if key and value and len(key) < 50:
                    specs[key] = value
        
        # Buscar em divs com estrutura chave: valor
        spec_divs = soup.find_all('div', class_=lambda x: x and any(
            keyword in ' '.join(x).lower() for keyword in ['spec', 'feature', 'attribute']
        ))
        
        for div in spec_divs:
            text = div.get_text()
            if ':' in text:
                parts = text.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key and value and len(key) < 50:
                        specs[key] = value
        
        return specs
    
    def _prepare_html_for_ai(self, html_content: str) -> str:
        """Prepara HTML para envio à IA (resumido)"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remover elementos desnecessários
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        
        # Focar nas seções principais
        main_content = []
        
        # Buscar seções relevantes
        relevant_selectors = [
            'main', '.main', '#main',
            '.product', '.item', '.content',
            '[class*="product"]', '[class*="detail"]'
        ]
        
        for selector in relevant_selectors:
            elements = soup.select(selector)
            for elem in elements:
                content = str(elem)
                if len(content) > 100:  # Conteúdo substancial
                    main_content.append(content)
        
        # Se não encontrou seções específicas, usar o body
        if not main_content:
            body = soup.find('body')
            if body:
                main_content = [str(body)]
        
        # Combinar e limitar tamanho
        combined = '\n'.join(main_content)
        
        # Limitar a ~8000 caracteres para não exceder limites de token
        if len(combined) > 8000:
            combined = combined[:8000] + "...[conteúdo truncado]"
        
        return combined
    
    def _clean_ai_response(self, ai_data: Dict) -> Dict[str, Any]:
        """Limpa e valida resposta da IA"""
        cleaned = {}
        
        # Nome
        if ai_data.get('name') and isinstance(ai_data['name'], str):
            cleaned['name'] = ai_data['name'][:300]
        
        # Preço
        if ai_data.get('price'):
            try:
                cleaned['price'] = Decimal(str(ai_data['price']))
            except:
                pass
        
        # Preço original
        if ai_data.get('original_price'):
            try:
                cleaned['original_price'] = Decimal(str(ai_data['original_price']))
            except:
                pass
        
        # Descrição
        if ai_data.get('description') and isinstance(ai_data['description'], str):
            cleaned['description'] = ai_data['description'][:2000]
        
        # URLs de imagem
        if ai_data.get('image_urls') and isinstance(ai_data['image_urls'], list):
            valid_urls = []
            for url in ai_data['image_urls']:
                if isinstance(url, str) and url.startswith('http'):
                    valid_urls.append(url)
            if valid_urls:
                cleaned['image_urls'] = valid_urls[:self.max_images_per_product]
        
        # Especificações
        if ai_data.get('specifications') and isinstance(ai_data['specifications'], dict):
            cleaned['specifications'] = {
                str(k)[:50]: str(v)[:200] 
                for k, v in ai_data['specifications'].items() 
                if k and v
            }
        
        # Disponibilidade
        if ai_data.get('availability') and isinstance(ai_data['availability'], str):
            cleaned['availability'] = ai_data['availability'][:100]
        
        # Marca
        if ai_data.get('brand') and isinstance(ai_data['brand'], str):
            cleaned['brand'] = ai_data['brand'][:50]
        
        return cleaned
    
    def _is_extraction_sufficient(self, data: Dict) -> bool:
        """Critérios mais flexíveis para parar extração mais cedo"""
        if not data:
            return False
        
        # Critérios relaxados - se tem nome e (preço OU descrição), já é suficiente
        has_name = bool(data.get('name')) and len(data.get('name', '')) > 5
        has_price = bool(data.get('price'))
        has_desc = bool(data.get('description')) and len(data.get('description', '')) > 30  # Era 50, agora 30
        
        # Se tem nome + preço, já é suficiente (mesmo sem imagens)
        if has_name and has_price:
            return True
        
        # Se tem nome + descrição razoável, também é suficiente
        if has_name and has_desc:
            return True
        
        return False
    
    def _finalize_product_data(self, data: Dict) -> Dict[str, Any]:
        """Finaliza dados do produto com metadados"""
        data.update({
            'scraped_at': timezone.now().isoformat(),
            'site_id': self.site.id,
            'currency': self.currency,
            'country': 'Paraguay',
            'details_extracted': True,
            'ai_model_used': self.configuration.model_integration if self.ai_available else None
        })
        return data
    
    # Métodos auxiliares restantes (mantendo os mesmos da versão anterior)
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
            
            # Normalização baseada na lógica original
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
    
    def _download_product_images(self, product_data: Dict) -> int:
        """Download de imagens"""
        image_urls = product_data.get('image_urls', [])
        if not image_urls:
            return 0
        
        downloaded_count = 0
        
        for i, img_url in enumerate(image_urls[:self.max_images_per_product]):
            try:
                print(f"  Baixando imagem {i+1}/{min(len(image_urls), self.max_images_per_product)}: {img_url}")
                
                # Headers para imagens
                image_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    'Referer': product_data.get('url', ''),
                    'Connection': 'keep-alive'
                }
                
                response = requests.get(img_url, timeout=30, stream=True, headers=image_headers)
                response.raise_for_status()
                
                # Ler conteúdo
                image_content = b''
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        image_content += chunk
                
                if not self._validate_image_content(image_content):
                    continue
                
                # Processar imagem
                processed_image = self._process_product_image_safe(image_content, img_url)
                if not processed_image:
                    continue
                
                # Salvar na estrutura do produto
                filename = self._generate_image_filename(product_data, i)
                
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
                print(f"    Imagem processada ({processed_image['width']}x{processed_image['height']})")
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"    Erro ao baixar imagem: {e}")
                continue
        
        return downloaded_count
    
    def _validate_image_content(self, content: bytes) -> bool:
        """Valida conteúdo de imagem"""
        if not content or len(content) < 10:
            return False
        
        # Verificar assinaturas
        signatures = {
            b'\xff\xd8\xff': 'JPEG',
            b'\x89PNG\r\n\x1a\n': 'PNG', 
            b'GIF87a': 'GIF',
            b'GIF89a': 'GIF',
            b'RIFF': 'WEBP',
            b'BM': 'BMP'
        }
        
        for signature in signatures:
            if content.startswith(signature):
                return True
        
        return False
    
    def _process_product_image_safe(self, image_content: bytes, original_url: str) -> Optional[Dict[str, Any]]:
        """Processamento seguro de imagens"""
        try:
            if not isinstance(image_content, bytes):
                return None
            
            # PIL processing
            image_buffer = BytesIO(image_content)
            img = Image.open(image_buffer)
            img.verify()
            
            image_buffer.seek(0)
            img = Image.open(image_buffer)
            
            width, height = img.size
            if width < 50 or height < 50:
                return None
            
            # Converter para RGB
            if img.mode not in ['RGB', 'L']:
                if img.mode == 'RGBA':
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1])
                    img = rgb_img
                else:
                    img = img.convert('RGB')
            
            # Redimensionar se necessário
            max_dimension = 1200
            if width > max_dimension or height > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                width, height = img.size
            
            # Salvar otimizado
            output_buffer = BytesIO()
            img.save(output_buffer, format='JPEG', quality=85, optimize=True)
            processed_content = output_buffer.getvalue()
            
            return {
                'content': processed_content,
                'width': width,
                'height': height,
                'format': 'JPEG',
                'content_type': 'image/jpeg'
            }
            
        except Exception as e:
            print(f"Erro no processamento de imagem: {e}")
            return None
    
    def _generate_image_filename(self, product_data: Dict, index: int) -> str:
        """Gera nome único para imagem"""
        from django.utils.text import slugify
        
        name_slug = slugify(product_data.get('name', 'produto'))[:30]
        unique_id = str(uuid.uuid4())[:8]
        
        return f"{name_slug}_{index+1}_{unique_id}.jpg"
    
    def _save_products_with_details_flag(self, products: List[Dict[str, Any]]) -> int:
        """Salva produtos com flag de detalhes extraídos"""
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
                        existing.name = product_data.get('name', existing.name)[:300]
                        existing.price = product_data.get('price') or existing.price
                        existing.original_price = product_data.get('original_price') or existing.original_price
                        
                        if has_details:
                            existing.description = product_data.get('description', '')
                            existing.brand = product_data.get('brand', '')[:100] if product_data.get('brand') else existing.brand
                            existing.availability = product_data.get('availability', '')[:100] or existing.availability
                        
                        existing.search_query = product_data.get('search_query', existing.search_query)
                        existing.updated_at = timezone.now()
                        existing.save()
                    
                    product_obj = existing
                else:
                    # Criar novo produto
                    product_obj = Product.objects.create(
                        name=product_data.get('name', 'Produto sem nome')[:300],
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
                extraction_method = product_data.get('extraction_method', 'unknown')
                print(f"Produto salvo ({extraction_method}): {product_obj.name[:50]}...")
                
            except Exception as e:
                print(f"Erro ao salvar produto: {str(e)}")
                continue
        
        return saved_count
    
    def _save_product_images(self, product: Product, processed_images: List[Dict]):
        """Salva imagens processadas no banco"""
        try:
            print(f"DEBUG: Salvando {len(processed_images)} imagens para produto {product.id}")
            print(f"DEBUG: MEDIA_ROOT = {settings.MEDIA_ROOT}")
            print(f"DEBUG: Permissões MEDIA_ROOT = {oct(os.stat(settings.MEDIA_ROOT).st_mode)}")
            
            # Verificar se diretório existe e é escribível
            if not os.path.exists(settings.MEDIA_ROOT):
                os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
                print(f"DEBUG: Criou diretório {settings.MEDIA_ROOT}")
                
            # Teste de escrita
            test_file = os.path.join(settings.MEDIA_ROOT, 'test_write.tmp')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                print("DEBUG: Teste de escrita: OK")
            except Exception as e:
                print(f"DEBUG: Erro no teste de escrita: {e}")
                
            # ... resto do código original
            
            # Remover imagens antigas
            ProductImage.objects.filter(product=product).delete()
            print(f"DEBUG: Removeu imagens antigas")
            
            for i, img_data in enumerate(processed_images):
                try:
                    content_b64 = img_data.get('content_base64', '')
                    if not content_b64:
                        print(f"DEBUG: Imagem {i} sem conteúdo base64")
                        continue
                    
                    # Decodificar base64
                    content = base64.b64decode(content_b64)
                    print(f"DEBUG: Imagem {i} decodificada: {len(content)} bytes")
                    
                    # Criar arquivo Django
                    image_file = ContentFile(content, name=img_data['filename'])
                    
                    # Criar registro
                    product_image = ProductImage.objects.create(
                        product=product,
                        image=image_file,
                        is_main=img_data.get('is_main', False),
                        alt_text=f"{product.name} - Imagem {i+1}",
                        order=i,
                        original_url=img_data['original_url']
                    )
                    
                    print(f"DEBUG: Imagem {i} salva: {product_image.image.path}")
                    
                    # Primeira imagem como principal
                    if i == 0:
                        product.main_image = product_image.image
                        product.save()
                        print(f"DEBUG: Imagem {i} definida como principal")
                    
                except Exception as e:
                    print(f"DEBUG: Erro ao salvar imagem {i}: {e}")
                    import traceback
                    print(traceback.format_exc())
                    continue
                    
        except Exception as e:
            print(f"DEBUG: Erro geral ao salvar imagens: {e}")
            import traceback
            print(traceback.format_exc())
    
    def _filter_products_with_ai(self, products: List[Dict], search_query: str) -> List[Dict]:
        """
        Usa IA para filtrar produtos realmente relevantes à busca
        Remove capas, acessórios irrelevantes, etc.
        """
        if not self.ai_available or not products:
            return products
        
        try:
            print(f"🧠 Filtrando {len(products)} produtos com IA para query: '{search_query}'")
            
            # Preparar lista de produtos para IA
            product_list = []
            for i, product in enumerate(products):
                product_list.append({
                    'index': i,
                    'name': product.get('name', ''),
                    'url': product.get('url', '')
                })
            
            # Prompt para filtrar produtos
            filter_prompt = f"""
    Analise esta lista de produtos encontrados na busca por "{search_query}" no site Nissei (Paraguai) e filtre apenas os produtos PRINCIPAIS que correspondem exatamente à busca.

    PRODUTOS ENCONTRADOS:
    {json.dumps(product_list, ensure_ascii=False, indent=2)}

    INSTRUÇÕES DE FILTRO:
    1. Se busca é "iPhone 16" → manter apenas iPhones 16, remover capas, protetores, acessórios
    2. Se busca é "Samsung Galaxy" → manter apenas celulares Samsung Galaxy, remover acessórios
    3. Se busca é "notebook" → manter apenas notebooks/laptops, remover mouses, bolsas
    4. Remover produtos que são claramente acessórios: capas, películas, carregadores, fones (a menos que seja especificamente a busca)
    5. Manter produtos que são versões/variações do item principal (diferentes cores, capacidades, modelos)

    CRITÉRIOS RIGOROSOS:
    - Manter apenas produtos que são o ITEM PRINCIPAL da busca
    - Se há dúvida, MANTER (é melhor incluir do que excluir incorretamente)
    - Priorizar produtos com nomes mais específicos e completos
    - Máximo de 10 produtos mais relevantes

    Responda APENAS com JSON:
    {{
        "filtered_indices": [0, 1, 3, 7],
        "reasoning": "Mantidos apenas iPhones 16, removidas capas e acessórios"
    }}
    """
            
            # Chamar IA
            ai_response = self._call_ai_api(filter_prompt)
            
            if ai_response:
                try:
                    # Parsear resposta
                    response_clean = ai_response.replace('```json', '').replace('```', '').strip()
                    filter_result = json.loads(response_clean)
                    
                    filtered_indices = filter_result.get('filtered_indices', [])
                    reasoning = filter_result.get('reasoning', '')
                    
                    print(f"🎯 IA filtrou: {reasoning}")
                    
                    # Aplicar filtro
                    filtered_products = []
                    for index in filtered_indices:
                        if 0 <= index < len(products):
                            filtered_products.append(products[index])
                    
                    print(f"📊 Produtos: {len(products)} → {len(filtered_products)} (filtrados)")
                    return filtered_products
                    
                except json.JSONDecodeError as e:
                    print(f"Erro ao parsear filtro IA: {e}")
                    print(f"Resposta IA: {ai_response[:200]}...")
            
        except Exception as e:
            print(f"Erro no filtro IA: {e}")
        
        # Fallback: retornar produtos originais
        print("⚠️ Usando todos os produtos (filtro IA falhou)")
        return products

    def _extract_sku_code(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Extrai o código SKU da página do produto
        Exemplo: SKU PC-128775 → retorna "PC-128775"
        """
        sku_patterns = [
            # Padrões específicos para SKU
            r'SKU[:\s]+([A-Z]{1,5}-\d{4,10})',  # SKU PC-128775
            r'SKU[:\s]+([A-Z0-9-]{5,15})',      # SKU genérico
            r'Código[:\s]+([A-Z]{1,5}-\d{4,10})', # Código alternativo
        ]
        
        # Buscar em elementos específicos primeiro
        sku_selectors = [
            # Por classes específicas
            '.sku', '.product-sku', '.item-sku', '.sku-code',
            '[class*="sku"]', '[class*="codigo"]',
            # Por data attributes
            '[data-sku]', '[data-product-sku]',
            # Em tabelas de especificações
            'table tr td', 'table tr th',
            # Elementos que podem conter SKU
            '.product-details', '.product-info', '.additional-info',
            'span', 'div', 'p'
        ]
        
        print("🏷️ Buscando código SKU...")
        
        # ESTRATÉGIA 1: Buscar por seletores específicos
        for selector in sku_selectors:
            try:
                elements = soup.select(selector)
                for element in elements:
                    text = element.get_text(strip=True)
                    
                    # Tentar cada padrão regex
                    for pattern in sku_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            sku_code = match.group(1).strip().upper()
                            print(f"✅ SKU encontrado via seletor '{selector}': {sku_code}")
                            return sku_code
                            
            except Exception as e:
                continue
        
        # ESTRATÉGIA 2: Buscar em todo texto da página
        try:
            full_text = soup.get_text()
            for pattern in sku_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    sku_code = match.group(1).strip().upper()
                    print(f"✅ SKU encontrado em texto geral: {sku_code}")
                    return sku_code
        except:
            pass
        
        # ESTRATÉGIA 3: Buscar por data attributes
        try:
            sku_attrs = ['data-sku', 'data-product-sku', 'data-item-code']
            for attr in sku_attrs:
                elements = soup.find_all(attrs={attr: True})
                for element in elements:
                    sku_value = element.get(attr, '').strip()
                    if sku_value and len(sku_value) > 3:
                        print(f"✅ SKU encontrado via atributo '{attr}': {sku_value}")
                        return sku_value.upper()
        except:
            pass
        
        print("⚠️ SKU não encontrado na página")
        return None

    def _extract_carousel_images(self, soup: BeautifulSoup, driver=None) -> List[str]:
        """SUBSTITUÍDO pelo método específico do Fotorama"""
        # Este método agora chama o método específico do Fotorama
        return self._extract_fotorama_carousel_images(soup, driver)

    def _resolve_image_url(self, url: str) -> Optional[str]:
        """Resolve URL relativa para absoluta"""
        if not url:
            return None
        
        url = url.strip()
        
        if url.startswith('//'):
            return f"https:{url}"
        elif url.startswith('/'):
            return f"{self.base_url}{url}"
        elif url.startswith('http'):
            return url
        else:
            return None

    def _is_nissei_product_image(self, url: str) -> bool:
        """Verifica se URL parece ser imagem de produto do Nissei"""
        url_lower = url.lower()
        
        # Padrões específicos do Nissei
        nissei_patterns = [
            'catalog/product',
            'media/catalog',
            '/media/cache',
            'product_image',
            '/cache/',
            '/resize/'
        ]
        
        return any(pattern in url_lower for pattern in nissei_patterns)

    def _score_carousel_image(self, url: str, img_element, source: str) -> int:
        """Score específico para imagens de carrossel"""
        if not any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            return -10
        
        score = 5  # Base score para carrossel
        url_lower = url.lower()
        
        # Bonus por fonte
        if 'js-' in source:
            score += 3  # Carregado via JavaScript
        if 'zoom' in source or 'large' in source:
            score += 5  # Imagem de zoom/large
        if 'fotorama' in source:
            score += 4  # Biblioteca Fotorama
        
        # Bonus por qualidade da URL
        quality_indicators = ['large', 'zoom', 'full', 'original', 'high', '1200', '800']
        score += sum(2 for indicator in quality_indicators if indicator in url_lower)
        
        # Bonus por atributos especiais
        if img_element.get('data-zoom-image'):
            score += 5
        if img_element.get('data-large-image'):
            score += 4
        
        # Penalizar imagens pequenas/thumbnails
        penalty_indicators = ['thumb', 'small', 'mini', 'icon', '100x', '150x']
        score -= sum(3 for indicator in penalty_indicators if indicator in url_lower)
        
        return score

    def _extract_description_enhanced(self, soup: BeautifulSoup, driver=None) -> str:
        """SUBSTITUÍDO pela versão com prioridade corrigida"""
        # Este método agora chama a versão com prioridade fixa
        return self._extract_description_priority_fixed(soup, driver)

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


# Exemplo de uso com Configuration
def example_usage():
    """Exemplo de uso com modelo Configuration"""
    
    # Buscar configuração do banco (Claude)
    claude_config = Configuration.objects.filter(
        model_integration__icontains='claude',
        name='Claude Scraping'
    ).first()
    
    # Buscar configuração do banco (OpenAI)  
    openai_config = Configuration.objects.filter(
        model_integration__icontains='openai',
        name='OpenAI Scraping'
    ).first()
    
    # Usar uma das configurações
    config = claude_config or openai_config
    
    if not config:
        print("Nenhuma configuração de IA encontrada!")
        return
    
    # Criar scraper
    site = Site.objects.get(name="Nissei")
    scraper = AISeleniumNisseiScraper(site, config)
    
    try:
        # Executar scraping
        products = scraper.scrape_products_intelligent(
            query="iPhone 15",
            max_results=20,
            max_detailed=5
        )
        
        print(f"Resultados: {len(products)} produtos processados com {config.model_integration}")
        
    finally:
        scraper.close()


# Script de configuração inicial
def setup_configurations():
    """Script para criar configurações iniciais"""
    
    # Configuração Claude
    claude_config, created = Configuration.objects.get_or_create(
        name="Claude Scraping",
        defaults={
            'description': 'Configuração do Claude para scraping inteligente',
            'model_integration': 'claude',
            'token': 'sk-ant-api03-...',  # Substitua pela sua API key
            'parameters': {
                'model': 'claude-3-sonnet-20240229',
                'max_tokens': 2000,
                'temperature': 0.1
            }
        }
    )
    
    # Configuração OpenAI
    openai_config, created = Configuration.objects.get_or_create(
        name="OpenAI Scraping",
        defaults={
            'description': 'Configuração do OpenAI para scraping inteligente',
            'model_integration': 'openai',
            'token': 'sk-...',  # Substitua pela sua API key
            'parameters': {
                'model': 'gpt-3.5-turbo',
                'max_tokens': 2000,
                'temperature': 0.1
            }
        }
    )
    
    print("Configurações criadas/atualizadas!")
    return claude_config, openai_config
