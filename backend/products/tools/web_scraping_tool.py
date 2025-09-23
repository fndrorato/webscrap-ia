import json
import re
import requests
import time
from bs4 import BeautifulSoup
from decimal import Decimal
from typing import Dict, Any, List
from urllib.parse import urljoin, urlparse


class WebScrapingTool:
    """
    Ferramenta customizada para o Agno fazer webscraping
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def get_page_content(self, url: str, delay: int = 1) -> str:
        """
        Obtém o conteúdo HTML de uma página
        
        Args:
            url: URL da página
            delay: Tempo de delay em segundos
        
        Returns:
            Conteúdo HTML da página
        """
        try:
            time.sleep(delay)  # Rate limiting
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            return f"Erro ao acessar {url}: {str(e)}"
    
    def extract_with_selectors(self, html_content: str, selectors: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Extrai dados usando seletores CSS específicos
        
        Args:
            html_content: Conteúdo HTML
            selectors: Dicionário com seletores CSS
        
        Returns:
            Lista de produtos extraídos
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            products = []
            
            # Encontrar elementos de produto
            product_elements = soup.select(selectors.get('product_selector', '.product'))
            
            for element in product_elements:
                product_data = {}
                
                # Extrair nome
                if selectors.get('name_selector'):
                    name_elem = element.select_one(selectors['name_selector'])
                    product_data['name'] = name_elem.get_text(strip=True) if name_elem else None
                
                # Extrair preço
                if selectors.get('price_selector'):
                    price_elem = element.select_one(selectors['price_selector'])
                    if price_elem:
                        price_text = price_elem.get_text(strip=True)
                        product_data['price'] = self._extract_price(price_text)
                
                # Extrair link
                if selectors.get('link_selector'):
                    link_elem = element.select_one(selectors['link_selector'])
                    if link_elem:
                        href = link_elem.get('href', '')
                        product_data['url'] = urljoin(selectors.get('base_url', ''), href)
                
                # Extrair imagem
                if selectors.get('image_selector'):
                    img_elem = element.select_one(selectors['image_selector'])
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src')
                        if img_src:
                            product_data['image_url'] = urljoin(selectors.get('base_url', ''), img_src)
                
                # Extrair descrição
                if selectors.get('description_selector'):
                    desc_elem = element.select_one(selectors['description_selector'])
                    product_data['description'] = desc_elem.get_text(strip=True) if desc_elem else None
                
                # Filtrar produtos vazios
                if product_data.get('name'):
                    products.append(product_data)
            
            return products
            
        except Exception as e:
            return [{'error': f'Erro ao extrair dados: {str(e)}'}]
    
    def _extract_price(self, price_text: str) -> Decimal:
        """Extrai valor numérico do preço"""
        if not price_text:
            return None
        
        # Remove caracteres não numéricos, exceto vírgulas e pontos
        price_clean = re.sub(r'[^\d,.]', '', price_text)
        
        # Trata formato brasileiro (vírgula como decimal)
        if ',' in price_clean and '.' in price_clean:
            # Formato: 1.234,56
            price_clean = price_clean.replace('.', '').replace(',', '.')
        elif ',' in price_clean:
            # Formato: 1234,56
            price_clean = price_clean.replace(',', '.')
        
        try:
            return Decimal(price_clean)
        except:
            return None
