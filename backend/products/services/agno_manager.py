from configurations.models import Configuration
from products.services.agno_scraper import AgnoIntelligentScraper
from sites.models import Site
from typing import List, Dict, Any


class AgnoScrapingManager:
    """
    Gerenciador principal para operações de scraping com Agno
    """
    
    @staticmethod
    def scrape_multiple_sites(query: str, site_ids: List[int] = None, max_results: int = 10) -> Dict[str, Any]:
        """
        Executa scraping em múltiplos sites
        """
        # Filtrar sites
        sites = Site.objects.filter(active=True)
        if site_ids:
            sites = sites.filter(id__in=site_ids)
        
        results = {
            'query': query,
            'total_sites': sites.count(),
            'sites_processed': 0,
            'total_products': 0,
            'products_by_site': {},
            'errors': []
        }
        
        for site in sites:
            try:
                scraper = AgnoIntelligentScraper(site)
                products = scraper.scrape_products(query, max_results)
                
                results['sites_processed'] += 1
                results['total_products'] += len(products)
                results['products_by_site'][site.name] = {
                    'count': len(products),
                    'products': products[:5],  # Primeiros 5 para preview
                    'confidence': products[0].get('confidence_score', 0) if products else 0
                }
                
            except Exception as e:
                results['errors'].append({
                    'site': site.name,
                    'error': str(e)
                })
        
        return results
    
    @staticmethod
    def analyze_site_structure(site_id: int) -> Dict[str, Any]:
        """
        Usa Agno para analisar a estrutura de um site
        """
        try:
            site = Site.objects.get(id=site_id)
            scraper = AgnoIntelligentScraper(site)
            
            # Fazer uma análise sem busca específica
            analysis = scraper.get_scraping_instructions("produtos em geral")
            
            return {
                'site': site.name,
                'url': site.url,
                'analysis': analysis,
                'status': 'success'
            }
            
        except Site.DoesNotExist:
            return {'error': 'Site não encontrado', 'status': 'error'}
        except Exception as e:
            return {'error': str(e), 'status': 'error'}
