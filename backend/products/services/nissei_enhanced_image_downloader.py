from .image_downloader import ProductImageDownloader
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

class NisseiImageDownloader(ProductImageDownloader):
    """
    Downloader de imagens especializado para Nissei.com
    """
    
    def _extract_image_urls(self, soup: BeautifulSoup, product_url: str, base_url: str) -> List[str]:
        """Extrai URLs de imagens específicas do Nissei"""
        image_urls = set()
        
        # Seletores específicos para Nissei/Shopify
        nissei_selectors = [
            '.product-single__photos img',
            '.product-photo-container img', 
            '.product-images img',
            '.featured-image img',
            '.product-gallery img',
            '[data-zoom] img',
            '.slick-slide img',  # Carrossel de imagens
            '.product__media img',
            '.media img'
        ]
        
        # Buscar imagens usando seletores específicos
        for selector in nissei_selectors:
            try:
                imgs = soup.select(selector)
                for img in imgs:
                    # Tentar diferentes atributos de fonte
                    src_attrs = ['data-src', 'data-srcset', 'src', 'data-original', 'data-zoom']
                    
                    for attr in src_attrs:
                        src = img.get(attr)
                        if src:
                            # Processar srcset se necessário
                            if 'srcset' in attr and ',' in src:
                                # Pegar a imagem de maior resolução
                                srcset_urls = src.split(',')
                                for srcset_url in srcset_urls:
                                    url_part = srcset_url.strip().split(' ')[0]
                                    if url_part:
                                        abs_url = urljoin(product_url, url_part)
                                        if self._is_valid_nissei_image_url(abs_url):
                                            image_urls.add(abs_url)
                            else:
                                # URL simples
                                abs_url = urljoin(product_url, src)
                                if self._is_valid_nissei_image_url(abs_url):
                                    image_urls.add(abs_url)
                            break
            except Exception as e:
                continue
        
        # Se não encontrou muitas imagens, usar seletores genéricos
        if len(image_urls) < 2:
            generic_imgs = soup.select('img[src*="product"], img[data-src*="product"]')
            for img in generic_imgs:
                src = img.get('data-src') or img.get('src')
                if src:
                    abs_url = urljoin(product_url, src)
                    if self._is_valid_nissei_image_url(abs_url):
                        image_urls.add(abs_url)
        
        return list(image_urls)
    
    def _is_valid_nissei_image_url(self, url: str) -> bool:
        """Verifica se é uma URL de imagem válida do Nissei"""
        if not url or len(url) < 10:
            return False
        
        url_lower = url.lower()
        
        # Deve ser uma imagem
        if not any(ext in url_lower for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            return False
        
        # Excluir ícones pequenos comuns no Shopify
        exclude_patterns = [
            'icon', 'logo', 'sprite', 'badge', 'arrow', 'star',
            '_1x1', '_small', '_icon', '_thumb', '_pico',
            '1x1.', 'spacer.', 'pixel.'
        ]
        
        if any(pattern in url_lower for pattern in exclude_patterns):
            return False
        
        # Incluir apenas URLs que parecem ser de produtos
        include_patterns = ['product', 'files', 'media', 'image', 'photo']
        if not any(pattern in url_lower for pattern in include_patterns):
            return False
        
        return True
