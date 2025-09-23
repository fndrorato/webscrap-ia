import json
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.tools.duckduckgo import DuckDuckGoTools
from configurations.models import Configuration
from products.models import Product
from products.tools.web_scraping_tool import WebScrapingTool
from products.services.image_downloader import ProductImageDownloader
from sites.models import Site
from typing import Dict, Any, List, Optional


class AgnoIntelligentScraper:
    """
    Sistema de webscraping inteligente usando Agno Framework
    """
    
    def __init__(self, site: Site):
        self.site = site
        self.config = site.configuration
        self.web_tool = WebScrapingTool()
        self.image_downloader = ProductImageDownloader()  # Novo serviço
        self.agent = self._create_agent()
    
    # ... [métodos anteriores permanecem iguais] ...
    
    def _save_products(self, products: List[Dict[str, Any]]):
        """Salva produtos no banco de dados COM download de imagens"""
        for product_data in products:
            try:
                # Verificar se produto já existe
                existing = Product.objects.filter(
                    url=product_data.get('url', ''),
                    site=self.site
                ).first()
                
                if existing:
                    # Atualizar produto existente
                    for key, value in product_data.items():
                        if key not in ['site_id', 'scraping_instructions'] and hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.scraped_data = product_data.get('scraping_instructions', {})
                    existing.save()
                    
                    # Baixar imagens se não tem imagem principal
                    if not existing.main_image:
                        self._download_product_images(existing)
                else:
                    # Criar novo produto
                    new_product = Product.objects.create(
                        name=product_data.get('name', '')[:300],
                        price=product_data.get('price'),
                        description=product_data.get('description', '')[:1000] if product_data.get('description') else None,
                        url=product_data.get('url', ''),
                        site=self.site,
                        search_query=product_data.get('search_query', ''),
                        scraped_data=product_data.get('scraping_instructions', {}),
                        status=1  # Aguardando Sincronização
                    )
                    
                    # Baixar imagens para o novo produto
                    self._download_product_images(new_product)
                    
            except Exception as e:
                print(f"Erro ao salvar produto: {str(e)}")
                continue
    
    def _download_product_images(self, product: Product):
        """Baixa imagens do produto em background"""
        try:
            downloaded_images = self.image_downloader.download_product_images(
                product=product,
                max_images=5  # Máximo 5 imagens por produto
            )
            
            if downloaded_images:
                print(f"✅ Baixadas {len(downloaded_images)} imagens para {product.name}")
            else:
                print(f"⚠️  Nenhuma imagem encontrada para {product.name}")
                
        except Exception as e:
            print(f"❌ Erro ao baixar imagens para {product.name}: {str(e)}")