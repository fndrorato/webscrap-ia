# products/management/commands/debug_fotorama.py

from django.core.management.base import BaseCommand
from playwright.sync_api import sync_playwright
import json


class Command(BaseCommand):
    help = 'Diagnostica estrutura do Fotorama para encontrar URLs das imagens'

    def add_arguments(self, parser):
        parser.add_argument('--url', type=str, default='https://nissei.com/py/apple-iphone-14-a2884')

    def handle(self, *args, **options):
        url = options['url']
        
        self.stdout.write(self.style.SUCCESS('🔍 DIAGNÓSTICO FOTORAMA'))
        self.stdout.write(f'URL: {url}')
        self.stdout.write('=' * 70)
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Abre navegador visível
            page = browser.new_page()
            
            self.stdout.write('🌐 Acessando página...')
            page.goto(url, timeout=30000)
            page.wait_for_timeout(3000)
            
            self.stdout.write('\n📸 MÉTODO 1: Dados JavaScript do Fotorama')
            self.stdout.write('-' * 70)
            
            # Tentar extrair dados do Fotorama via JavaScript
            fotorama_data = page.evaluate("""
                () => {
                    // Procurar instância do Fotorama
                    const fotoramaElement = document.querySelector('.fotorama');
                    if (!fotoramaElement) return null;
                    
                    // Tentar acessar dados do Fotorama
                    const fotoramaData = fotoramaElement.fotorama;
                    if (fotoramaData && fotoramaData.data) {
                        return fotoramaData.data.map(item => ({
                            img: item.img,
                            thumb: item.thumb,
                            full: item.full,
                            caption: item.caption
                        }));
                    }
                    return null;
                }
            """)
            
            if fotorama_data:
                self.stdout.write('✅ Dados encontrados via JavaScript!')
                for i, img in enumerate(fotorama_data, 1):
                    self.stdout.write(f'\n   Imagem {i}:')
                    for key, value in img.items():
                        if value:
                            self.stdout.write(f'      {key}: {value[:100]}...' if len(str(value)) > 100 else f'      {key}: {value}')
            else:
                self.stdout.write('❌ Dados não encontrados via JavaScript')
            
            self.stdout.write('\n\n📸 MÉTODO 2: Atributos data-* das miniaturas')
            self.stdout.write('-' * 70)
            
            thumbs = page.query_selector_all('.fotorama__nav__frame')
            self.stdout.write(f'✅ {len(thumbs)} miniaturas encontradas\n')
            
            for i, thumb in enumerate(thumbs[:5], 1):  # Primeiras 5
                self.stdout.write(f'   Miniatura {i}:')
                
                # Pegar todos os atributos data-*
                attributes = page.evaluate("""
                    (element) => {
                        const attrs = {};
                        for (let attr of element.attributes) {
                            if (attr.name.startsWith('data-')) {
                                attrs[attr.name] = attr.value;
                            }
                        }
                        return attrs;
                    }
                """, thumb)
                
                if attributes:
                    for key, value in attributes.items():
                        display_value = value[:100] + '...' if len(value) > 100 else value
                        self.stdout.write(f'      {key}: {display_value}')
                else:
                    self.stdout.write('      (sem atributos data-*)')
                
                # Verificar img dentro da miniatura
                img = thumb.query_selector('img')
                if img:
                    img_attrs = page.evaluate("""
                        (element) => {
                            return {
                                src: element.src,
                                'data-src': element.getAttribute('data-src'),
                                'data-full': element.getAttribute('data-full'),
                                'data-img': element.getAttribute('data-img')
                            };
                        }
                    """, img)
                    
                    self.stdout.write('      IMG dentro da miniatura:')
                    for key, value in img_attrs.items():
                        if value:
                            display_value = value[:100] + '...' if len(value) > 100 else value
                            self.stdout.write(f'         {key}: {display_value}')
                
                self.stdout.write('')
            
            self.stdout.write('\n📸 MÉTODO 3: HTML do elemento .fotorama')
            self.stdout.write('-' * 70)
            
            fotorama_html = page.query_selector('.fotorama')
            if fotorama_html:
                html_attrs = page.evaluate("""
                    (element) => {
                        const attrs = {};
                        for (let attr of element.attributes) {
                            attrs[attr.name] = attr.value;
                        }
                        return attrs;
                    }
                """, fotorama_html)
                
                self.stdout.write('Atributos do elemento .fotorama:')
                for key, value in html_attrs.items():
                    display_value = value[:100] + '...' if len(value) > 100 else value
                    self.stdout.write(f'   {key}: {display_value}')
            
            self.stdout.write('\n\n📸 MÉTODO 4: Tags <a> dentro das miniaturas')
            self.stdout.write('-' * 70)
            
            links = page.query_selector_all('.fotorama__nav__frame a')
            self.stdout.write(f'✅ {len(links)} links encontrados\n')
            
            for i, link in enumerate(links[:5], 1):
                href = link.get_attribute('href')
                data_attrs = page.evaluate("""
                    (element) => {
                        const attrs = {};
                        for (let attr of element.attributes) {
                            if (attr.name.startsWith('data-') || attr.name === 'href') {
                                attrs[attr.name] = attr.value;
                            }
                        }
                        return attrs;
                    }
                """, link)
                
                self.stdout.write(f'   Link {i}:')
                for key, value in data_attrs.items():
                    if value:
                        display_value = value[:100] + '...' if len(value) > 100 else value
                        self.stdout.write(f'      {key}: {display_value}')
                self.stdout.write('')
            
            self.stdout.write('\n📸 MÉTODO 5: Script tags no HTML')
            self.stdout.write('-' * 70)
            
            # Procurar por variáveis JavaScript que podem conter as URLs
            scripts = page.evaluate("""
                () => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    return scripts
                        .map(s => s.textContent)
                        .filter(text => text.includes('fotorama') || text.includes('gallery'))
                        .map(text => text.substring(0, 500)); // Primeiros 500 chars
                }
            """)
            
            if scripts:
                self.stdout.write(f'✅ {len(scripts)} scripts relevantes encontrados\n')
                for i, script in enumerate(scripts[:3], 1):
                    self.stdout.write(f'   Script {i}:')
                    self.stdout.write(f'   {script}...')
                    self.stdout.write('')
            else:
                self.stdout.write('❌ Nenhum script relevante encontrado')
            
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write('✅ Diagnóstico concluído!')
            self.stdout.write('\nPressione ENTER para fechar o navegador...')
            input()
            
            browser.close()