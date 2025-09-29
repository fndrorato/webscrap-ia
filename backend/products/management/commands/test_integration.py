# Caminho: products/management/commands/test_integration_fixed.py

import time
from typing import List, Optional
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand
from django.conf import settings

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from sites.models import Site
from configurations.models import Configuration

# AJUSTAR ESTE IMPORT PARA SEU MÓDULO
try:
    from products.services.ai_nissei_scraper import AISeleniumNisseiScraper
except ImportError:
    try:
        from scrapers.ai_selenium_nissei_scraper import AISeleniumNisseiScraper
    except ImportError:
        try:
            from ai_selenium_nissei_scraper import AISeleniumNisseiScraper
        except ImportError:
            AISeleniumNisseiScraper = None


class Command(BaseCommand):
    help = 'Testa integração do carrossel - verifica Sites existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            default='https://nissei.com/py/apple-iphone-16-pro-a3083-1',
            help='URL do produto para testar'
        )
        parser.add_argument(
            '--site-name',
            type=str,
            help='Nome específico do Site para usar'
        )
        parser.add_argument(
            '--create-site',
            action='store_true',
            help='Criar Site "Nissei" se não existir'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Mostrar logs detalhados'
        )

    def handle(self, *args, **options):
        test_url = options['url']
        site_name = options['site_name']
        create_site = options['create_site']
        verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS('🧪 TESTE DE INTEGRAÇÃO: Carrossel em Produção (Corrigido)')
        )
        self.stdout.write(f'URL: {test_url}')
        self.stdout.write('=' * 70)

        try:
            # PASSO 1: Verificar classe do scraper
            if AISeleniumNisseiScraper is None:
                self.stdout.write(
                    self.style.ERROR('❌ ERRO: Classe AISeleniumNisseiScraper não encontrada')
                )
                self.stdout.write('Ajuste o import na linha 15 do arquivo test_integration_fixed.py')
                return

            # PASSO 2: Verificar/configurar Site
            site = self.get_or_create_site(site_name, create_site)
            if not site:
                return

            # PASSO 3: Verificar Configuration
            config = self.get_configuration()
            if not config:
                return

            # PASSO 4: Executar teste
            success = self.run_integration_test(site, config, test_url, verbose)
            
            # PASSO 5: Resultado final
            if success:
                self.stdout.write(
                    self.style.SUCCESS('\n🎉 INTEGRAÇÃO FUNCIONOU!')
                )
                self.stdout.write('A versão de produção está extraindo múltiplas imagens')
                self.stdout.write('Pode usar o scraper normalmente')
            else:
                self.stdout.write(
                    self.style.ERROR('\n❌ INTEGRAÇÃO COM PROBLEMA')
                )
                self.stdout.write('Verificar se os métodos foram substituídos corretamente')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro durante teste: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())

    def get_or_create_site(self, site_name: Optional[str], create_site: bool) -> Optional[Site]:
        """Obtém ou cria Site para teste"""
        
        # Listar Sites existentes
        self.stdout.write('\n📋 Verificando Sites existentes...')
        sites = Site.objects.all()
        
        if not sites.exists():
            self.stdout.write(self.style.WARNING('⚠️ Nenhum Site encontrado no banco'))
            
            if create_site:
                return self.create_nissei_site()
            else:
                self.stdout.write('Use --create-site para criar Site "Nissei" automaticamente')
                return None
        
        # Mostrar Sites disponíveis
        self.stdout.write(f'Sites disponíveis ({sites.count()}):')
        for i, site in enumerate(sites, 1):
            self.stdout.write(f'  {i}. {site.name} - {site.url}')
        
        # Selecionar Site
        if site_name:
            # Site específico solicitado
            try:
                site = sites.get(name__icontains=site_name)
                self.stdout.write(f'✅ Site selecionado: {site.name}')
                return site
            except Site.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Site "{site_name}" não encontrado')
                )
                return None
        else:
            # Tentar encontrar Nissei
            nissei_sites = sites.filter(name__icontains='nissei')
            if nissei_sites.exists():
                site = nissei_sites.first()
                self.stdout.write(f'✅ Site Nissei encontrado: {site.name}')
                return site
            
            # Usar primeiro Site disponível
            site = sites.first()
            self.stdout.write(f'✅ Usando primeiro Site: {site.name}')
            self.stdout.write('⚠️ Para site específico, use --site-name="Nome do Site"')
            return site

    def create_nissei_site(self) -> Site:
        """Cria Site Nissei para teste"""
        
        self.stdout.write('🔧 Criando Site "Nissei"...')
        
        site = Site.objects.create(
            name="Nissei",
            url="https://nissei.com",
            description="Site Nissei - Paraguai",
            status=1
        )
        
        self.stdout.write(f'✅ Site criado: {site.name}')
        return site

    def get_configuration(self) -> Optional[Configuration]:
        """Obtém Configuration para teste"""
        
        self.stdout.write('\n⚙️ Verificando Configurations...')
        configs = Configuration.objects.all()
        
        if not configs.exists():
            self.stdout.write(self.style.WARNING('⚠️ Nenhuma Configuration encontrada'))
            self.stdout.write('Criando Configuration básica para teste...')
            
            config = Configuration.objects.create(
                name="Teste Carrossel",
                description="Configuration para teste do carrossel",
                model_integration="teste",
                token="teste_token",
                parameters={}
            )
            
            self.stdout.write(f'✅ Configuration criada: {config.name}')
            return config
        
        # Procurar por Configuration com IA
        ai_configs = configs.filter(
            model_integration__icontains='claude'
        ) or configs.filter(
            model_integration__icontains='openai'
        ) or configs.filter(
            model_integration__icontains='anthropic'
        )
        
        if ai_configs:
            config = ai_configs.first()
            self.stdout.write(f'✅ Configuration IA: {config.name} ({config.model_integration})')
        else:
            config = configs.first()
            self.stdout.write(f'✅ Configuration: {config.name}')
        
        return config

    def run_integration_test(self, site: Site, config: Configuration, test_url: str, verbose: bool) -> bool:
        """Executa o teste de integração"""
        
        # PASSO 1: Criar scraper
        self.stdout.write('\n🤖 Criando scraper...')
        
        try:
            scraper = AISeleniumNisseiScraper(site, config)
            self.stdout.write('✅ Scraper criado')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro ao criar scraper: {e}'))
            return False

        # PASSO 2: Verificar métodos (antes de configurar Selenium)
        self.stdout.write('\n🔍 Verificando métodos na classe...')
        
        # Verificar se métodos principais existem
        main_methods = [
            'setup_selenium',
            '_extract_fotorama_carousel_images'
        ]
        
        missing_main = []
        for method_name in main_methods:
            if not hasattr(scraper, method_name):
                missing_main.append(method_name)
        
        if missing_main:
            self.stdout.write(self.style.ERROR('❌ Métodos principais faltando:'))
            for method in missing_main:
                self.stdout.write(f'   - {method}')
            return False
        
        # Verificar métodos auxiliares do teste
        auxiliary_methods = [
            '_find_next_buttons_test_version',
            '_get_current_carousel_image_test_version', 
            '_navigate_with_arrows_test_version',
            '_click_button_robust_test_version'
        ]
        
        missing_auxiliary = []
        for method_name in auxiliary_methods:
            if not hasattr(scraper, method_name):
                missing_auxiliary.append(method_name)
        
        if missing_auxiliary:
            self.stdout.write(self.style.WARNING('⚠️ Métodos auxiliares faltando:'))
            for method in missing_auxiliary:
                self.stdout.write(f'   - {method}')
            self.stdout.write('   Isso pode causar problemas na navegação do carrossel')
        else:
            self.stdout.write('✅ Todos os métodos auxiliares presentes')

        # PASSO 3: Testar Selenium
        self.stdout.write('\n🌐 Configurando Selenium...')
        
        try:
            scraper.setup_selenium()
            if not scraper.driver:
                self.stdout.write(self.style.ERROR('❌ Selenium não inicializou'))
                return False
            self.stdout.write('✅ Selenium configurado')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro no Selenium: {e}'))
            return False

        # PASSO 4: Acessar página
        self.stdout.write('\n📡 Acessando página de teste...')
        
        try:
            scraper.driver.get(test_url)
            
            # Aguardar carregamento
            WebDriverWait(scraper.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)
            self.stdout.write('✅ Página carregada')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro ao acessar página: {e}'))
            scraper.close()
            return False

        # PASSO 5: Testar extração do carrossel
        self.stdout.write('\n🎠 Testando extração do carrossel...')
        
        try:
            # Obter HTML renderizado
            soup = BeautifulSoup(scraper.driver.page_source, 'html.parser')
            
            # Testar método específico do carrossel
            if verbose:
                self.stdout.write('   Chamando _extract_fotorama_carousel_images...')
            
            images = scraper._extract_fotorama_carousel_images(soup, scraper.driver)
            
            if verbose:
                self.stdout.write(f'   Debug: Método retornou {type(images)} com {len(images) if images else 0} items')
                if images:
                    self.stdout.write(f'   Debug: Primeira imagem: {images[0][:50] if images[0] else "None"}...')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erro na extração: {e}'))
            import traceback
            if verbose:
                self.stdout.write(traceback.format_exc())
            scraper.close()
            return False

        # PASSO 6: Analisar resultados
        self.stdout.write(f'\n📊 RESULTADO: {len(images)} imagens extraídas')
        
        success = False
        
        if len(images) > 1:
            self.stdout.write(self.style.SUCCESS('✅ SUCESSO! Múltiplas imagens extraídas'))
            success = True
            
            # Mostrar imagens
            for i, url in enumerate(images[:5], 1):
                self.stdout.write(f'   {i}. {url[:70]}...')
                
            if len(images) > 5:
                self.stdout.write(f'   ... e mais {len(images) - 5} imagens')
                
        elif len(images) == 1:
            self.stdout.write(self.style.WARNING('⚠️ PARCIAL: Apenas 1 imagem extraída'))
            self.stdout.write('   Possível problema: navegação por setas não funcionou')
            self.stdout.write(f'   1. {images[0][:70]}...')
            
        else:
            self.stdout.write(self.style.ERROR('❌ FALHA: Nenhuma imagem extraída'))
            self.stdout.write('   Problema: método não está funcionando')

        # Cleanup
        try:
            scraper.close()
            self.stdout.write('\n🔧 Recursos liberados')
        except:
            pass

        return success