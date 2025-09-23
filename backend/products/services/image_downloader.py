import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from bs4 import BeautifulSoup
import time
import logging
from PIL import Image
from io import BytesIO
import uuid
from ..models import Product, ProductImage

logger = logging.getLogger(__name__)

class ProductImageDownloader:
    """
    Serviço para baixar e processar imagens de produtos
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.max_image_size = 5 * 1024 * 1024  # 5MB
        self.min_image_size = 1024  # 1KB
        self.supported_formats = ['jpeg', 'jpg', 'png', 'webp']
    
    def download_product_images(self, product: Product, max_images: int = 5) -> List[Dict[str, Any]]:
        """
        Baixa imagens da página específica do produto
        
        Args:
            product: Instância do produto
            max_images: Máximo de imagens para baixar
        
        Returns:
            Lista com informações das imagens baixadas
        """
        try:
            # Acessar página específica do produto
            response = self.session.get(product.url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Encontrar URLs das imagens
            image_urls = self._extract_image_urls(soup, product.url, product.site.url)
            
            # Filtrar e ordenar imagens por qualidade
            filtered_urls = self._filter_and_rank_images(image_urls)
            
            # Baixar imagens
            downloaded_images = []
            for i, img_url in enumerate(filtered_urls[:max_images]):
                try:
                    image_data = self._download_single_image(img_url, product)
                    if image_data:
                        downloaded_images.append(image_data)
                        
                    # Rate limiting
                    time.sleep(1)
                    
                except Exception as e:
                    logger.warning(f"Erro ao baixar imagem {img_url}: {str(e)}")
                    continue
            
            # Definir imagem principal se ainda não foi definida
            if downloaded_images and not product.main_image:
                main_image_data = downloaded_images[0]
                product.main_image = main_image_data['file']
                product.save()
            
            return downloaded_images
            
        except Exception as e:
            logger.error(f"Erro ao baixar imagens do produto {product.id}: {str(e)}")
            return []
    
    def _extract_image_urls(self, soup: BeautifulSoup, product_url: str, base_url: str) -> List[str]:
        """Extrai URLs de imagens da página do produto"""
        image_urls = set()  # Usar set para evitar duplicatas
        
        # Seletores específicos por site
        selectors = {
            'amazon.com': [
                '#landingImage',
                '.a-dynamic-image',
                '#altImages img',
                '[data-a-dynamic-image]'
            ],
            'mercadolivre.com': [
                '.ui-pdp-gallery img',
                '.ui-pdp-image img',
                '.carousel-item img'
            ],
            'magazineluiza.com': [
                '.photo-gallery img',
                '.product-image img',
                '.carousel img'
            ],
            'shopee.com': [
                '.item-images img',
                '.product-image img'
            ]
        }
        
        # Detectar tipo de site
        domain = urlparse(base_url).netloc.lower()
        site_selectors = []
        
        for site_key, site_sel in selectors.items():
            if site_key in domain:
                site_selectors = site_sel
                break
        
        # Se não encontrou seletores específicos, usar genéricos
        if not site_selectors:
            site_selectors = [
                '.product img',
                '.gallery img',
                '.carousel img',
                '[class*="image"] img',
                '[class*="photo"] img'
            ]
        
        # Adicionar seletores genéricos sempre
        site_selectors.extend([
            'img[src*="product"]',
            'img[data-src*="product"]',
            'img[alt*="product" i]'
        ])
        
        # Buscar imagens usando seletores
        for selector in site_selectors:
            try:
                imgs = soup.select(selector)
                for img in imgs:
                    # Tentar diferentes atributos de fonte
                    src_attrs = ['src', 'data-src', 'data-lazy-src', 'data-original']
                    
                    for attr in src_attrs:
                        src = img.get(attr)
                        if src:
                            # Resolver URL absoluta
                            abs_url = urljoin(product_url, src)
                            if self._is_valid_image_url(abs_url):
                                image_urls.add(abs_url)
                            break
            except Exception as e:
                logger.warning(f"Erro ao processar seletor {selector}: {str(e)}")
                continue
        
        return list(image_urls)
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Verifica se a URL é válida para imagem"""
        if not url or len(url) < 10:
            return False
        
        # Verificar se contém extensão de imagem
        url_lower = url.lower()
        extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
        has_extension = any(ext in url_lower for ext in extensions)
        
        # Verificar se não é ícone pequeno
        small_indicators = ['icon', 'logo', 'sprite', 'thumb', 'badge', '1x1', 'pixel']
        is_small = any(indicator in url_lower for indicator in small_indicators)
        
        return has_extension and not is_small
    
    def _filter_and_rank_images(self, urls: List[str]) -> List[str]:
        """Filtra e ordena URLs por qualidade esperada"""
        scored_urls = []
        
        for url in urls:
            score = 0
            url_lower = url.lower()
            
            # Pontuação por tamanho indicado na URL
            if any(size in url_lower for size in ['large', 'big', 'main', 'primary']):
                score += 10
            if any(size in url_lower for size in ['medium', 'mid']):
                score += 5
            if any(size in url_lower for size in ['small', 'thumb', 'mini']):
                score -= 5
            
            # Pontuação por números que indicam tamanho
            import re
            size_numbers = re.findall(r'(\d{3,4})[x_](\d{3,4})', url)
            if size_numbers:
                width, height = map(int, size_numbers[0])
                if width >= 800 or height >= 800:
                    score += 15
                elif width >= 400 or height >= 400:
                    score += 10
                elif width >= 200 or height >= 200:
                    score += 5
            
            # Penalizar URLs muito longas (podem ser dados encoded)
            if len(url) > 300:
                score -= 5
            
            scored_urls.append((score, url))
        
        # Ordenar por score decrescente
        scored_urls.sort(reverse=True, key=lambda x: x[0])
        return [url for score, url in scored_urls]
    
    def _download_single_image(self, url: str, product: Product) -> Optional[Dict[str, Any]]:
        """Baixa uma única imagem e retorna informações"""
        try:
            # Download da imagem
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Verificar tamanho
            content_length = response.headers.get('content-length')
            if content_length:
                size = int(content_length)
                if size > self.max_image_size:
                    logger.warning(f"Imagem muito grande: {size} bytes")
                    return None
                if size < self.min_image_size:
                    logger.warning(f"Imagem muito pequena: {size} bytes")
                    return None
            
            # Ler conteúdo
            image_content = response.content
            
            # Verificar e processar imagem
            processed_image = self._process_image(image_content, url)
            if not processed_image:
                return None
            
            # Gerar nome único para o arquivo
            filename = self._generate_filename(product, url)
            
            # Salvar arquivo
            image_file = ContentFile(processed_image['content'], name=filename)
            
            # Criar registro ProductImage
            product_image = ProductImage.objects.create(
                product=product,
                image=image_file,
                original_url=url,
                alt_text=f"{product.name} - Imagem",
                is_main=(not ProductImage.objects.filter(product=product).exists())
            )
            
            return {
                'id': product_image.id,
                'file': product_image.image,
                'url': product_image.image.url,
                'original_url': url,
                'width': processed_image['width'],
                'height': processed_image['height'],
                'format': processed_image['format']
            }
            
        except Exception as e:
            logger.error(f"Erro ao baixar imagem {url}: {str(e)}")
            return None
    
    def _process_image(self, image_content: bytes, original_url: str) -> Optional[Dict[str, Any]]:
        """Processa e valida a imagem"""
        try:
            # Abrir imagem com PIL
            img = Image.open(BytesIO(image_content))
            
            # Verificar formato
            if img.format.lower() not in self.supported_formats:
                logger.warning(f"Formato não suportado: {img.format}")
                return None
            
            # Verificar dimensões mínimas
            width, height = img.size
            if width < 100 or height < 100:
                logger.warning(f"Imagem muito pequena: {width}x{height}")
                return None
            
            # Converter para RGB se necessário (para compatibilidade)
            if img.mode in ['RGBA', 'P']:
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = rgb_img
            
            # Redimensionar se muito grande (otimização)
            max_size = 1200
            if width > max_size or height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                width, height = img.size
            
            # Salvar processada
            output = BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            processed_content = output.getvalue()
            
            return {
                'content': processed_content,
                'width': width,
                'height': height,
                'format': 'JPEG'
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar imagem: {str(e)}")
            return None
    
    def _generate_filename(self, product: Product, original_url: str) -> str:
        """Gera nome único para o arquivo"""
        from django.utils.text import slugify
        
        # Nome base do produto
        base_name = slugify(product.name)[:50]
        
        # ID único
        unique_id = str(uuid.uuid4())[:8]
        
        # Extensão
        extension = 'jpg'  # Sempre JPG após processamento
        
        return f"{base_name}_{unique_id}.{extension}"
