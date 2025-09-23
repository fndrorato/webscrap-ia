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
        """Configuração otimizada do Selenium para performance"""
        try:
            chrome_options = Options()
            
            # Configurações básicas
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # OTIMIZAÇÕES DE PERFORMANCE
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Não carregar imagens (mais rápido)
            chrome_options.add_argument('--disable-javascript')  # Desabilitar JS desnecessário
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            
            # Configurações de memória
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--max_old_space_size=2048')  # Reduzir de 4096
            
            # User agent
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # TIMEOUTS OTIMIZADOS
            self.driver.set_page_load_timeout(15)  # Era 30, agora 15
            self.driver.implicitly_wait(5)         # Era 10, agora 5
            
            print("✅ Selenium configurado (modo otimizado)")
            
        except Exception as e:
            print(f"❌ Erro ao configurar Selenium: {e}")
            self.driver = None
    
    def scrape_products_intelligent(self, query: str, max_results: int = 10, max_detailed: int = 5) -> List[Dict[str, Any]]:
        """
        Scraping inteligente com IA + Selenium configurável
        """
        try:
            print(f"SCRAPING INTELIGENTE com {self.configuration.model_integration}")
            print(f"Busca: '{query}' | Max listagem: {max_results} | Max detalhes: {max_detailed}")
            print("=" * 60)
            
            # FASE 1: Obter lista básica de produtos
            print("FASE 1: Obtendo lista de produtos...")
            basic_products = self._get_basic_product_list(query, max_results)
            
            if not basic_products:
                print("Nenhum produto encontrado na listagem")
                return []
            
            print(f"{len(basic_products)} produtos encontrados na listagem")
            
            # FASE 2: Processar produtos selecionados com IA + Selenium
            products_for_details = basic_products[:max_detailed]
            print(f"Processando {len(products_for_details)} produtos com IA + Selenium")
            print("=" * 60)
            
            detailed_products = []
            
            for i, basic_product in enumerate(products_for_details, 1):
                try:
                    print(f"\nPRODUTO {i}/{len(products_for_details)}: {basic_product.get('name', '')[:50]}...")
                    print(f"URL: {basic_product.get('url', '')}")
                    
                    # Usar estratégia inteligente: Requests → Selenium → IA
                    detailed_product = self._extract_product_intelligent(basic_product)
                    
                    if detailed_product:
                        detailed_products.append(detailed_product)
                        print(f"Produto processado com IA + Selenium")
                        
                        # Baixar imagens
                        print(f"Baixando até {self.max_images_per_product} imagens...")
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
            
            # FASE 3: Adicionar produtos restantes (apenas básicos)
            remaining_products = basic_products[max_detailed:]
            if remaining_products:
                print(f"\nFASE 3: Adicionando {len(remaining_products)} produtos básicos...")
                for basic_product in remaining_products:
                    basic_product.update({
                        'scraped_at': timezone.now().isoformat(),
                        'site_id': self.site.id,
                        'currency': self.currency,
                        'country': 'Paraguay',
                        'extraction_method': 'basic',
                        'details_extracted': False,
                        'description': 'Detalhes não extraídos - produto da listagem básica',
                        'categories': [],
                        'specifications': {},
                        'image_urls': [],
                        'processed_images': []
                    })
                    detailed_products.append(basic_product)
            
            # FASE 4: Salvar no banco de dados
            print(f"\nFASE 4: Salvando {len(detailed_products)} produtos...")
            saved_count = self._save_products_with_details_flag(detailed_products)
            
            print(f"SCRAPING INTELIGENTE CONCLUÍDO!")
            print(f"Total encontrados: {len(basic_products)}")
            print(f"Com IA + Selenium: {len(products_for_details)}")
            print(f"Apenas básicos: {len(remaining_products)}")
            print(f"Produtos salvos: {saved_count}")
            
            return detailed_products
            
        except Exception as e:
            print(f"Erro geral no scraping inteligente: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return []
        finally:
            self._cleanup_selenium()
    
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
        """Versão otimizada - mais rápida e eficiente"""
        
        # Aguardar carregamento básico (timeout reduzido)
        try:
            WebDriverWait(self.driver, 5).until(  # Era 10, agora 5
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass
        
        # Estratégias rápidas - tentar em paralelo
        quick_selectors = [
            (By.CSS_SELECTOR, "img[src*='product'], img[src*='catalog']"),  # Imagens primeiro
            (By.CSS_SELECTOR, "[class*='price'], [data-price]"),           # Preços
            (By.CSS_SELECTOR, "h1, [class*='title']"),                     # Título
        ]
        
        # Aguardar qualquer um aparecer (mais rápido)
        content_loaded = False
        for selector_type, selector in quick_selectors:
            try:
                WebDriverWait(self.driver, 3).until(  # Timeout bem baixo
                    EC.presence_of_element_located((selector_type, selector))
                )
                print(f"✅ Conteúdo básico carregado: {selector}")
                content_loaded = True
                break
            except TimeoutException:
                continue
        
        # Aguardar mínimo para JavaScript (reduzido)
        time.sleep(1)  # Era 3, agora 1
        
        # Tentar ativar abas (em background, não bloquear)
        try:
            self._activate_detail_tabs()
        except Exception as e:
            print(f"⚠️ Erro ao ativar abas (continuando): {str(e)[:50]}")
        
        # Aguardar final mínimo (reduzido)
        time.sleep(1)  # Era 2, agora 1

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
