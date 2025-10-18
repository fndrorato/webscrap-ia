import base64
from configurations.models import Configuration
from rest_framework import status as http_status
from django.shortcuts import get_object_or_404
from django.db import models
from django.utils import timezone
from products.models import Product
from products.serializers import (
    ProductSerializer, 
    ProductImageSerializer,
    IntelligentSearchSerializer,
    SiteSerializer,
    SiteAnalysisSerializer,
    ConfigurationSerializer
)
# from products.oracle_sync import sync_products_to_oracle 
from products.services.agno_manager import AgnoScrapingManager
from products.services.nissei_scraper import NisseiSpecializedScraper
from products.services.nissei_scraper_fixed import NisseiScraper
from products.services.nissei_detailed_scraper import NisseiDetailedScraper
from products.services.ai_nissei_scraper import AISeleniumNisseiScraper
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from sites.models import Site


class UpdateProductStatusView(APIView):
    def post(self, request, *args, **kwargs):
        product_id = request.data.get("id")
        new_status = request.data.get("status")

        if product_id is None or new_status is None:
            return Response(
                {"error": "id e status são obrigatórios"},
                status=http_status.HTTP_400_BAD_REQUEST
            )

        product = get_object_or_404(Product, id=product_id)

        try:
            new_status = int(new_status)
            if new_status not in dict(Product.STATUS_CHOICES):
                return Response(
                    {"error": "status inválido"},
                    status=http_status.HTTP_400_BAD_REQUEST
                )
        except ValueError:
            return Response(
                {"error": "status deve ser um número inteiro"},
                status=http_status.HTTP_400_BAD_REQUEST
            )

        product.status = new_status
        product.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "message": "Status atualizado com sucesso",
                "id": product.id,
                "status": product.get_status_display(),
            },
            status=http_status.HTTP_200_OK
        )

class ProductByStatusView(APIView):
    def get(self, request, status_code, *args, **kwargs):
        try:
            status_code = int(status_code)
        except ValueError:
            return Response({"error": "status inválido"}, status=http_status.HTTP_400_BAD_REQUEST)

        if status_code not in dict(Product.STATUS_CHOICES):
            return Response({"error": "status inválido"}, status=http_status.HTTP_400_BAD_REQUEST)

        products = Product.objects.filter(status=status_code).prefetch_related("images")
        serializer = ProductSerializer(products, many=True, context={"request": request})

        return Response({"products": serializer.data}, status=http_status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nissei_search_detailed(request):
    """
    Busca detalhada no Nissei.com com IA + Selenium configurável
    """
    try:
        # Validar parâmetros
        query = request.data.get('query')
        if not query or len(query.strip()) < 2:
            return Response({
                'error': 'Query deve ter pelo menos 2 caracteres'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parâmetros de scraping
        max_results = int(request.data.get('max_results', 20))  # Total de produtos da busca
        max_detailed = int(request.data.get('max_detailed', 5))  # Máximo para acessar detalhes com IA
        max_images = int(request.data.get('max_images', 3))     # Máximo de imagens por produto
        
        # Configuração de IA (opcional - pode ser específica ou automática)
        ai_config_name = request.data.get('ai_config', 'auto')  # Nome da config ou 'auto'

        # ← ADICIONE ESTA LINHA AQUI
        enhanced_extraction = request.data.get('enhanced_extraction', True)  # Usar extração melhorada        
        
        # Validar limites
        max_results = min(max(max_results, 1), 50)    # Entre 1 e 50
        max_detailed = min(max(max_detailed, 1), 10)  # Entre 1 e 10  
        max_images = min(max(max_images, 1), 8)       # Entre 1 e 8
        
        print(f"PARÂMETROS:")
        print(f"   Query: {query}")
        print(f"   Buscar na listagem: {max_results} produtos")
        print(f"   Acessar detalhes de: {max_detailed} produtos")
        print(f"   Baixar até: {max_images} imagens por produto")
        print(f"   Configuração IA: {ai_config_name}")
        print(f"   Extração melhorada: {enhanced_extraction}") 
        
        # 1. BUSCAR CONFIGURAÇÃO DE IA
        configuration = None
        
        if ai_config_name != 'none':  # Permitir scraping sem IA
            if ai_config_name == 'auto':
                # Buscar configuração ativa automaticamente (prioridade: Claude > OpenAI)
                configuration = Configuration.objects.filter(
                    model_integration__in=['claude', 'anthropic', 'openai'],
                    token__isnull=False,
                    token__gt=''
                ).order_by(
                    # Prioridade: claude/anthropic primeiro, depois openai
                    models.Case(
                        models.When(model_integration__icontains='claude', then=1),
                        models.When(model_integration__icontains='anthropic', then=1), 
                        models.When(model_integration__icontains='openai', then=2),
                        default=3
                    )
                ).first()
            else:
                # Buscar configuração específica por nome
                configuration = Configuration.objects.filter(
                    name__icontains=ai_config_name,
                    token__isnull=False,
                    token__gt=''
                ).first()
            
            if not configuration:
                # Fallback: qualquer configuração válida
                configuration = Configuration.objects.filter(
                    model_integration__in=['claude', 'anthropic', 'openai'],
                    token__isnull=False,
                    token__gt=''
                ).first()
                
                if not configuration:
                    return Response({
                        'error': 'Nenhuma configuração de IA válida encontrada',
                        'suggestion': 'Configure uma IA (Claude ou OpenAI) no Django Admin',
                        'available_configs': list(Configuration.objects.values_list('name', flat=True))
                    }, status=status.HTTP_400_BAD_REQUEST)

            else:
                max_results = min(max(configuration.max_results or 10, 1), 50)
                max_detailed = min(max(configuration.max_detailed or 10, 1), 10)
                max_images = min(max(configuration.max_images or 3, 1), 8)                
        
        # 2. BUSCAR OU CRIAR SITE NISSEI
        site, created = Site.objects.get_or_create(
            url="https://nissei.com",
            defaults={
                'name': 'Casa Nissei Paraguay',
                'description': 'Loja de eletrônicos do Paraguai',
                'active': True
            }
        )
        
        # 3. CRIAR SCRAPER COM CONFIGURAÇÃO
        if configuration:
            print(f"Usando IA: {configuration.name} ({configuration.model_integration})")
            scraper = AISeleniumNisseiScraper(site, configuration)
        else:
            print("Executando sem IA (apenas Selenium)")
            # Para modo sem IA, você pode criar uma configuração dummy ou modificar a classe
            dummy_config = Configuration(
                name="Selenium Only",
                model_integration="none",
                token="",
                parameters={}
            )
            scraper = AISeleniumNisseiScraper(site, dummy_config)
        
        # 4. APLICAR CONFIGURAÇÕES PERSONALIZADAS
        scraper.max_images_per_product = max_images
        
        try:
            # 5. EXECUTAR SCRAPING INTELIGENTE
            detailed_products = scraper.scrape_products_intelligent(
                query=query.strip(),
                max_results=max_results,
                max_detailed=max_detailed
            )
            
            print(f"Produtos processados: {len(detailed_products)}")
            
            # 6. SANITIZAR DADOS E SUBSTITUIR BASE64 POR URLs
            for product in detailed_products:
                # Remover processed_images com base64 se existir
                if 'processed_images' in product:
                    del product['processed_images']
                
                # Buscar URLs das imagens salvas no banco
                if 'url' in product:
                    try:
                        # Buscar produto salvo no banco pela URL
                        saved_product = Product.objects.filter(
                            url=product['url'],
                            site=site
                        ).prefetch_related('images').first()
                        
                        if saved_product and saved_product.images.exists():
                            # Adicionar URLs das imagens salvas
                            product['saved_images'] = []
                            for img in saved_product.images.all():
                                try:
                                    product['saved_images'].append({
                                        'url': request.build_absolute_uri(img.image.url) if img.image else None,
                                        'alt_text': img.alt_text,
                                        'is_main': img.is_main,
                                        'order': img.order,
                                        'original_url': img.original_url
                                    })
                                except:
                                    # Se houver erro na URL da imagem, pular
                                    continue
                            
                            # Adicionar imagem principal se existir
                            if saved_product.main_image:
                                try:
                                    product['main_image_url'] = request.build_absolute_uri(saved_product.main_image.url)
                                except:
                                    product['main_image_url'] = None
                    except:
                        # Se não encontrar produto no banco, manter image_urls originais
                        pass
                
                # Sanitizar outros campos bytes
                for key, value in product.items():
                    if isinstance(value, bytes):
                        try:
                            product[key] = value.decode('utf-8', errors='ignore')
                        except:
                            product[key] = str(value)
            
            # 7. BUSCAR PRODUTOS SALVOS RELACIONADOS
            saved_products = Product.objects.filter(
                search_query__icontains=query,
                site=site,
                status__in=[1, 2]
            ).prefetch_related('images').order_by('-created_at')[:10]

            print(f"Produtos salvos no banco: {saved_products.count()}")
            
            # 8. Chame a função de sincronização para o Oracle
            serialized_products_data = ProductSerializer(
                saved_products, 
                many=True, 
                context={'request': request}
            ).data  
                      
            # print("Iniciando sincronização com o banco de dados Oracle...")
            # oracle_sync_report = sync_products_to_oracle(serialized_products_data)
            # print(f"Sincronização Oracle finalizada. Sucesso: {oracle_sync_report['success_count']}, Erros: {oracle_sync_report['error_count']}")
                    
                    
            # 9. PREPARAR RESPOSTA         
            response_data = {
                'query': query.strip(),
                'parameters': {
                    'max_results_requested': max_results,
                    'max_detailed_requested': max_detailed,
                    'max_images_per_product': max_images,
                    'actual_detailed_processed': len([p for p in detailed_products if p.get('details_extracted', False)]),
                    'ai_config_used': configuration.name if configuration else 'none',
                    'enhanced_extraction': enhanced_extraction  # ← ADICIONE ESTA LINHA
                },
                'ai_configuration': {
                    'name': configuration.name if configuration else 'none',
                    'model': configuration.model_integration if configuration else 'selenium_only',
                    'available': bool(configuration)
                },
                'site': {
                    'name': site.name,
                    'url': site.url,
                    'country': 'Paraguay'
                },
                'scraping_results': {
                    'total_products_found': len(detailed_products),
                    'products_with_ai_details': len([p for p in detailed_products if p.get('extraction_method', '').startswith('ai')]),
                    'products_with_selenium_details': len([p for p in detailed_products if p.get('extraction_method') == 'selenium']),
                    'products_basic_only': len([p for p in detailed_products if p.get('extraction_method') == 'basic']),
                    'products': detailed_products
                },
                'database_results': {
                    'saved_products_count': saved_products.count(),
                    'products': ProductSerializer(saved_products, many=True, context={'request': request}).data
                },
                'currency': 'Gs.',
                'timestamp': timezone.now().isoformat(),
                'performance': {
                    'ai_assisted_products': len([p for p in detailed_products if 'ai' in p.get('extraction_method', '')]),
                    'selenium_assisted_products': len([p for p in detailed_products if 'selenium' in p.get('extraction_method', '')]),
                    'basic_products': len([p for p in detailed_products if p.get('extraction_method') == 'basic']),
                    'total_time_saved': f"Processou detalhes inteligentes de {max_detailed} produtos ao invés de todos os {max_results}",
                    'estimated_time_seconds': max_detailed * 8
                },
                'success': True
            }

            print(f"View nissei_search_detailed finalizada com sucesso")


            return Response(response_data, status=status.HTTP_200_OK)
            
        finally:
            # 9. LIMPAR RECURSOS SELENIUM
            scraper.close()
        
    except Exception as e:
        print(f"Erro na view: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return Response({
            'error': f'Erro interno: {str(e)}',
            'query': request.data.get('query', ''),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nissei_search_fixed(request):
    """
    Busca de produtos no Nissei.com - versão corrigida e independente
    """
    try:
        # Validar parâmetros
        query = request.data.get('query')
        if not query or len(query.strip()) < 2:
            return Response({
                'error': 'Query deve ter pelo menos 2 caracteres'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        max_results = int(request.data.get('max_results', 15))
        if max_results < 1 or max_results > 50:
            max_results = 15
        
        # Buscar ou criar site Nissei
        site, created = Site.objects.get_or_create(
            url="https://nissei.com",
            defaults={
                'name': 'Casa Nissei Paraguay',
                'description': 'Loja de eletrônicos do Paraguai',
                'active': True
            }
        )
        
        if created:
            print(f"✅ Site Nissei criado automaticamente")
        
        # Usar scraper independente
        scraper = NisseiScraper(site)
        max_results = 10
        new_products = scraper.scrape_products(query, max_results)
        
        # Buscar produtos salvos relacionados
        saved_products = Product.objects.filter(
            search_query__icontains=query,
            site=site,
            status__in=[1, 2]  # Aguardando sincronização ou aprovado
        ).order_by('-created_at')[:10]
        
        # Preparar resposta
        response_data = {
            'query': query.strip(),
            'site': {
                'name': site.name,
                'url': site.url,
                'country': 'Paraguay'
            },
            'scraping_results': {
                'new_products_found': len(new_products),
                'products': new_products
            },
            'database_results': {
                'saved_products_count': saved_products.count(),
                'products': ProductSerializer(saved_products, many=True, context={'request': request}).data
            },
            'currency': 'Gs.',
            'timestamp': timezone.now().isoformat(),
            'success': True
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response({
            'error': f'Erro de validação: {str(e)}',
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        print(f"❌ Erro interno: {str(e)}")
        return Response({
            'error': f'Erro interno do servidor: {str(e)}',
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ConfigurationViewSet(viewsets.ModelViewSet):
    queryset = Configuration.objects.all()
    serializer_class = ConfigurationSerializer
    permission_classes = [IsAuthenticated]

class SiteViewSet(viewsets.ModelViewSet):
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def analyze_structure(self, request, pk=None):
        """Analisa a estrutura do site usando Agno"""
        try:
            result = AgnoScrapingManager.analyze_site_structure(pk)
            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Product.objects.select_related('site').all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        site_id = self.request.query_params.get('site')
        if site_id:
            queryset = queryset.filter(site_id=site_id)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def intelligent_search(self, request):
        """
        Busca inteligente usando Agno Framework
        """
        serializer = IntelligentSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        validated_data = serializer.validated_data
        
        try:
            # Executar busca inteligente
            results = AgnoScrapingManager.scrape_multiple_sites(
                query=validated_data['query'],
                site_ids=validated_data.get('site_ids'),
                max_results=validated_data['max_results']
            )
            
            # Buscar produtos salvos no banco também
            saved_products = Product.objects.filter(
                search_query__icontains=validated_data['query']
            ).select_related('site')[:20]
            
            response_data = {
                **results,
                'saved_products_count': saved_products.count(),
                'saved_products': ProductSerializer(saved_products, many=True).data[:10]
            }
            
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {'error': f'Erro na busca inteligente: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def nissei_search(self, request):
        """
        Busca específica no Nissei.com com otimizações
        """
        try:
            query = request.data.get('query')
            max_results = int(request.data.get('max_results', 15))
            
            if not query:
                return Response({'error': 'Query é obrigatória'}, status=400)
            
            # Buscar site Nissei
            nissei_site = Site.objects.filter(url__icontains='nissei.com').first()
            if not nissei_site:
                return Response({'error': 'Site Nissei não configurado'}, status=404)
            
            print(f'Busca Nissei para: {query}')
            # Usar scraper especializado
            scraper = NisseiSpecializedScraper(nissei_site)
            products = scraper.scrape_products(query, max_results)
            
            # Buscar produtos salvos também
            saved_products = Product.objects.filter(
                search_query__icontains=query,
                site=nissei_site
            )[:10]
            
            return Response({
                'query': query,
                'site': nissei_site.name,
                'new_products_found': len(products),
                'new_products': products,
                'saved_products_count': saved_products.count(),
                'saved_products': ProductSerializer(saved_products, many=True).data,
                'currency': 'Gs.',
                'country': 'Paraguay'
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)

# NOVA VIEW ADICIONAL: Listar configurações disponíveis
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_ai_configurations(request):
    """
    Lista configurações de IA disponíveis para scraping
    """
    try:
        configurations = Configuration.objects.filter(
            model_integration__in=['claude', 'anthropic', 'openai']
        ).values('id', 'name', 'model_integration', 'description', 'created_at')
        
        # Verificar quais têm token válido
        config_list = []
        for config in configurations:
            config_obj = Configuration.objects.get(id=config['id'])
            config_list.append({
                **config,
                'has_valid_token': bool(config_obj.token and len(config_obj.token.strip()) > 10),
                'parameters': config_obj.parameters,
                'status': 'ready' if config_obj.token else 'needs_token'
            })
        
        return Response({
            'configurations': config_list,
            'total': len(config_list),
            'active_count': len([c for c in config_list if c['has_valid_token']])
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# NOVA VIEW ADICIONAL: Testar configuração específica
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_ai_configuration(request):
    """
    Testa uma configuração de IA específica
    """
    try:
        config_id = request.data.get('config_id')
        if not config_id:
            return Response({
                'error': 'config_id é obrigatório'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        configuration = Configuration.objects.get(id=config_id)
        
        # Criar scraper de teste
        site, _ = Site.objects.get_or_create(
            url="https://nissei.com",
            defaults={'name': 'Casa Nissei Paraguay', 'active': True}
        )
        
        scraper = AISeleniumNisseiScraper(site, configuration)
        
        try:
            if scraper.ai_available:
                # Teste básico - prompt simples
                test_prompt = 'Responda apenas com: {"status": "ok", "test": true}'
                response = scraper._call_ai_api(test_prompt)
                
                return Response({
                    'success': True,
                    'config_name': configuration.name,
                    'model': configuration.model_integration,
                    'test_response': response[:100] + '...' if len(response) > 100 else response,
                    'ai_available': True
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Configuração não está válida',
                    'config_name': configuration.name,
                    'ai_available': False
                })
                
        finally:
            scraper.close()
        
    except Configuration.DoesNotExist:
        return Response({
            'error': 'Configuração não encontrada'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        return Response({
            'error': str(e),
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# FUNÇÃO AUXILIAR: Buscar melhor configuração
def get_best_ai_configuration():
    """
    Busca a melhor configuração de IA disponível
    Prioridade: Claude > OpenAI GPT-4 > OpenAI GPT-3.5
    """
    from django.db import models
    
    return Configuration.objects.filter(
        model_integration__in=['claude', 'anthropic', 'openai'],
        token__isnull=False,
        token__gt=''
    ).annotate(
        priority=models.Case(
            # Claude/Anthropic = prioridade 1
            models.When(
                models.Q(model_integration__icontains='claude') | 
                models.Q(model_integration__icontains='anthropic'), 
                then=1
            ),
            # GPT-4 = prioridade 2
            models.When(
                models.Q(model_integration__icontains='openai') & 
                models.Q(parameters__model__icontains='gpt-4'),
                then=2
            ),
            # GPT-3.5 = prioridade 3
            models.When(
                models.Q(model_integration__icontains='openai') & 
                models.Q(parameters__model__icontains='gpt-3.5'),
                then=3
            ),
            # Outros OpenAI = prioridade 4
            models.When(model_integration__icontains='openai', then=4),
            default=5
        )
    ).order_by('priority').first()

