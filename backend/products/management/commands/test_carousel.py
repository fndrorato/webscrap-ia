# Caminho: products/management/commands/test_carousel.py

import time
import requests
from typing import List, Optional
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand
from django.conf import settings

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

from sites.models import Site
from configurations.models import Configuration


class Command(BaseCommand):
    help = 'Testa a navegação por setas do carrossel Nissei'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            default='https://nissei.com/py/apple-iphone-16-pro-a3083-1',
            help='URL do produto para testar (padrão: iPhone 16 Pro)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Ativar modo debug detalhado'
        )
        parser.add_argument(
            '--keep-open',
            action='store_true',
            help='Manter navegador aberto após teste para inspeção manual'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.driver = None
        self.max_images_per_product = 6

    def handle(self, *args, **options):
        test_url = options['url']
        debug_mode = options['debug']
        keep_open = options['keep_open']
        
        self.stdout.write(
            self.style.SUCCESS('=== TESTE DE NAVEGAÇÃO POR SETAS DO CARROSSEL NISSEI ===')
        )
        self.stdout.write(f'URL de teste: {test_url}')
        self.stdout.write(f'Modo debug: {debug_mode}')
        self.stdout.write('=' * 70)

        try:
            # Configurar Selenium
            if not self.setup_selenium():
                self.stdout.write(self.style.ERROR('Falha ao configurar Selenium'))
                return

            # Executar teste
            images = self.test_carousel_navigation(test_url, debug_mode)
            
            # Exibir resultados
            self.show_results(images)
            
            # Validar imagens
            if images:
                self.validate_images(images)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro durante teste: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
        finally:
            if not keep_open and self.driver:
                self.driver.quit()
                self.stdout.write('Navegador fechado')
            elif keep_open and self.driver:
                self.stdout.write(
                    self.style.WARNING('Navegador mantido aberto para inspeção manual')
                )
                self.stdout.write('Execute Ctrl+C para fechar quando terminar')

    def setup_selenium(self) -> bool:
        """Configura Selenium otimizado para carregar imagens"""
        try:
            self.stdout.write('Configurando Selenium...')
            
            chrome_options = Options()
            
            # Configurações básicas
            chrome_options.add_argument('--headless=new')  # Usar novo headless
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            
            # IMPORTANTE: NÃO desabilitar imagens nem JavaScript
            # chrome_options.add_argument('--disable-images')  # COMENTADO!
            # chrome_options.add_argument('--disable-javascript')  # COMENTADO!
            
            # Otimizações que não quebram funcionalidade
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--disable-default-apps')
            
            # Configurações para evitar detecção
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # User agent realista
            chrome_options.add_argument(
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Timeouts generosos para JavaScript pesado
            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(10)
            
            # Remover detecção de automação
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            
            self.stdout.write(self.style.SUCCESS('Selenium configurado com sucesso'))
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro ao configurar Selenium: {e}'))
            return False

    def test_carousel_navigation(self, url: str, debug_mode: bool) -> List[str]:
        """Teste principal da navegação por setas"""
        
        all_images = []
        
        try:
            # PASSO 1: Acessar página
            self.stdout.write('Acessando página...')
            self.driver.get(url)
            
            # PASSO 2: Aguardar carregamento
            self.stdout.write('Aguardando carregamento...')
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)  # Aguardar JavaScript inicializar
            
            # PASSO 3: Debug se solicitado
            if debug_mode:
                self.debug_carousel_structure()
            
            # PASSO 4: Capturar imagem inicial
            self.stdout.write('Capturando imagem inicial...')
            initial_image = self.get_current_carousel_image()
            if initial_image:
                all_images.append(initial_image)
                self.stdout.write(f'  Inicial: {initial_image[:60]}...')
            else:
                self.stdout.write(self.style.WARNING('  Nenhuma imagem inicial encontrada'))
            
            # PASSO 5: Encontrar botões de navegação
            self.stdout.write('Procurando botões de setas...')
            next_buttons = self.find_next_buttons()
            
            if not next_buttons:
                self.stdout.write(self.style.WARNING('Nenhum botão de seta encontrado'))
                return all_images
            
            self.stdout.write(f'  {len(next_buttons)} botão(ões) encontrado(s)')
            
            # PASSO 6: Navegar pelo carrossel
            self.stdout.write('Iniciando navegação por setas...')
            navigation_images = self.navigate_with_arrows(next_buttons[0])
            
            # PASSO 7: Adicionar novas imagens
            for img in navigation_images:
                if img and img not in all_images:
                    all_images.append(img)
            
            return all_images[:self.max_images_per_product]
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro na navegação: {e}'))
            return all_images

    def debug_carousel_structure(self):
        """Debug detalhado da estrutura do carrossel"""
        
        self.stdout.write(self.style.HTTP_INFO('=== DEBUG: ESTRUTURA DO CARROSSEL ==='))
        
        # 1. Verificar elementos Fotorama
        fotorama_selectors = [
            '.fotorama',
            '[data-fotorama]',
            '.fotorama__stage',
            '.fotorama__nav',
            '.fotorama__arr'
        ]
        
        self.stdout.write('Elementos Fotorama:')
        for selector in fotorama_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                self.stdout.write(f'  {selector}: {len(elements)} elementos')
                
                for i, elem in enumerate(elements[:2]):  # Primeiros 2
                    try:
                        classes = elem.get_attribute('class')
                        visible = elem.is_displayed()
                        self.stdout.write(f'    [{i+1}] Visível: {visible}, Classe: {classes}')
                    except:
                        pass
            except:
                self.stdout.write(f'  {selector}: ERRO')
        
        # 2. Verificar botões de seta
        arrow_selectors = [
            '.fotorama__arr--next',
            '.fotorama__arr--prev',
            '.fotorama__arr[data-side="next"]',
            'button[class*="next"]',
            '.carousel-control-next',
            '.slick-next'
        ]
        
        self.stdout.write('\nBotões de seta:')
        for selector in arrow_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                self.stdout.write(f'  {selector}: {len(buttons)} botões')
                
                for i, btn in enumerate(buttons[:2]):
                    try:
                        visible = btn.is_displayed()
                        enabled = btn.is_enabled()
                        classes = btn.get_attribute('class')
                        text = btn.text.strip()
                        self.stdout.write(f'    [{i+1}] Visível: {visible}, Habilitado: {enabled}')
                        self.stdout.write(f'         Classe: {classes}')
                        self.stdout.write(f'         Texto: "{text}"')
                    except:
                        pass
            except:
                self.stdout.write(f'  {selector}: ERRO')
        
        # 3. Verificar imagens atuais
        self.stdout.write('\nImagens na página:')
        try:
            all_imgs = self.driver.find_elements(By.TAG_NAME, 'img')
            product_imgs = [img for img in all_imgs if self.looks_like_product_image(img)]
            
            self.stdout.write(f'  Total de imagens: {len(all_imgs)}')
            self.stdout.write(f'  Imagens de produto: {len(product_imgs)}')
            
            for i, img in enumerate(product_imgs[:3]):  # Primeiras 3
                try:
                    src = img.get_attribute('src')
                    data_src = img.get_attribute('data-src')
                    size = img.size
                    visible = img.is_displayed()
                    
                    self.stdout.write(f'    [{i+1}] Visível: {visible}, Tamanho: {size}')
                    self.stdout.write(f'         src: {src[:50] if src else "None"}...')
                    self.stdout.write(f'         data-src: {data_src[:50] if data_src else "None"}...')
                except:
                    pass
        except Exception as e:
            self.stdout.write(f'  ERRO ao verificar imagens: {e}')

    def find_next_buttons(self) -> List:
        """Encontra botões de próxima imagem"""
        
        # Seletores ordenados por prioridade
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
                        # Verificar se não é botão de "anterior"
                        classes = (button.get_attribute('class') or '').lower()
                        aria = (button.get_attribute('aria-label') or '').lower()
                        
                        if any(word in classes + aria for word in ['prev', 'previous', 'back']):
                            continue
                        
                        found_buttons.append(button)
                        self.stdout.write(f'  Botão encontrado: {selector}')
                        break  # Usar apenas o primeiro válido de cada tipo
                        
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

    def get_current_carousel_image(self) -> Optional[str]:
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
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        # Verificar se é imagem grande (não thumbnail)
                        size = element.size
                        if size.get('width', 0) > 200 and size.get('height', 0) > 200:
                            
                            # Buscar melhor URL disponível
                            for attr in ['data-zoom-image', 'data-large-image', 'data-src', 'src']:
                                url = element.get_attribute(attr)
                                if url and self.is_valid_product_image_url(url):
                                    return self.resolve_image_url(url)
            except:
                continue
        
        return None

    def navigate_with_arrows(self, next_button) -> List[str]:
        """Navega pelo carrossel usando setas"""
        
        navigation_images = []
        max_clicks = 8
        
        self.stdout.write(f'Navegando: máximo {max_clicks} cliques')
        
        for click_num in range(max_clicks):
            try:
                self.stdout.write(f'  Clique {click_num + 1}/{max_clicks}')
                
                # Verificar se botão ainda está disponível
                if not next_button.is_displayed() or not next_button.is_enabled():
                    self.stdout.write('    Botão não disponível - parando')
                    break
                
                # Capturar imagem antes do clique
                image_before = self.get_current_carousel_image()
                
                # Scroll até botão
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", 
                    next_button
                )
                time.sleep(1)
                
                # Clicar no botão (múltiplas estratégias)
                clicked = self.click_button_robust(next_button)
                if not clicked:
                    self.stdout.write('    Falha ao clicar - parando')
                    break
                
                # Aguardar transição
                time.sleep(3)
                
                # Capturar nova imagem
                image_after = self.get_current_carousel_image()
                
                # Verificar se mudou
                if image_after and image_after != image_before:
                    if image_after not in navigation_images:
                        navigation_images.append(image_after)
                        self.stdout.write(f'    Nova imagem capturada')
                    else:
                        self.stdout.write('    Imagem duplicada')
                elif image_after == image_before:
                    self.stdout.write('    Imagem não mudou - possível fim do carrossel')
                    if click_num >= 2:  # Parar após algumas tentativas sem mudança
                        break
                else:
                    self.stdout.write('    Erro ao capturar nova imagem')
                
            except Exception as e:
                self.stdout.write(f'    Erro no clique {click_num + 1}: {e}')
                continue
        
        self.stdout.write(f'Navegação concluída: {len(navigation_images)} novas imagens')
        return navigation_images

    def click_button_robust(self, button) -> bool:
        """Clique robusto com múltiplas estratégias"""
        
        strategies = [
            ('Normal', lambda: button.click()),
            ('JavaScript', lambda: self.driver.execute_script("arguments[0].click();", button)),
            ('ActionChains', lambda: ActionChains(self.driver).move_to_element(button).click().perform())
        ]
        
        for name, strategy in strategies:
            try:
                strategy()
                return True
            except Exception as e:
                continue
        
        return False

    def looks_like_product_image(self, img_element) -> bool:
        """Verifica se elemento parece ser imagem de produto"""
        try:
            src = img_element.get_attribute('src') or ''
            data_src = img_element.get_attribute('data-src') or ''
            classes = img_element.get_attribute('class') or ''
            
            # URLs de produto
            product_indicators = ['catalog', 'media', 'product', 'gallery']
            if any(keyword in (src + data_src).lower() for keyword in product_indicators):
                return True
            
            # Classes de produto
            if any(keyword in classes.lower() for keyword in ['product', 'gallery', 'fotorama']):
                return True
            
            return False
        except:
            return False

    def is_valid_product_image_url(self, url: str) -> bool:
        """Valida se URL é de imagem de produto"""
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

    def resolve_image_url(self, url: str) -> str:
        """Resolve URL para formato absoluto"""
        if not url:
            return url
        
        if url.startswith('//'):
            return f"https:{url}"
        elif url.startswith('/'):
            return f"https://nissei.com{url}"
        else:
            return url

    def show_results(self, images: List[str]):
        """Exibe resultados do teste"""
        
        self.stdout.write(self.style.SUCCESS('\n=== RESULTADOS ==='))
        self.stdout.write(f'Total de imagens extraídas: {len(images)}')
        
        if not images:
            self.stdout.write(self.style.ERROR('Nenhuma imagem foi extraída'))
            return
        
        for i, url in enumerate(images, 1):
            self.stdout.write(f'{i}. {url}')
        
        # Análise dos resultados
        if len(images) == 1:
            self.stdout.write(self.style.WARNING(
                'ATENÇÃO: Apenas 1 imagem extraída. Possíveis problemas:'
            ))
            self.stdout.write('- Navegação por setas não funcionou')
            self.stdout.write('- Carrossel não tem múltiplas imagens')
            self.stdout.write('- Seletores incorretos para o site')
        elif len(images) > 1:
            self.stdout.write(self.style.SUCCESS(
                f'SUCESSO: {len(images)} imagens extraídas. Navegação funcionou!'
            ))
        
    def validate_images(self, images: List[str]):
        """Valida se as URLs das imagens são acessíveis"""
        
        self.stdout.write('\nValidando URLs das imagens...')
        
        valid_count = 0
        for i, url in enumerate(images, 1):
            try:
                response = requests.head(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'image' in content_type:
                        self.stdout.write(f'  {i}. ✓ OK')
                        valid_count += 1
                    else:
                        self.stdout.write(f'  {i}. ✗ Não é imagem ({content_type})')
                else:
                    self.stdout.write(f'  {i}. ✗ Status {response.status_code}')
                    
            except Exception as e:
                self.stdout.write(f'  {i}. ✗ Erro: {e}')
        
        self.stdout.write(f'\nImagens válidas: {valid_count}/{len(images)}')
        
        if valid_count == len(images):
            self.stdout.write(self.style.SUCCESS('Todas as imagens são válidas!'))
        elif valid_count > 0:
            self.stdout.write(self.style.WARNING(f'{len(images) - valid_count} imagens com problema'))
        else:
            self.stdout.write(self.style.ERROR('Nenhuma imagem válida encontrada'))
