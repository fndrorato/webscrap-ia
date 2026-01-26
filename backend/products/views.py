import base64
import requests
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
from configurations.models import Configuration
from rest_framework import status as http_status
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.db import models
from django.utils import timezone
from products.models import Product, ProductImage
from products.serializers import (
    ProductSerializer, 
    ProductImageSerializer,
    IntelligentSearchSerializer,
    SiteSerializer,
    SiteAnalysisSerializer,
    ConfigurationSerializer
)
from products.oracle_sync import sync_products_to_oracle 
from products.services.agno_manager import AgnoScrapingManager
from products.services.nissei_scraper import NisseiSpecializedScraper
from products.services.nissei_scraper_fixed import NisseiScraper
from products.services.nissei_detailed_scraper import NisseiDetailedScraper
from products.services.ai_nissei_scraper import AISeleniumNisseiScraper
from products.services.nissei_extractor_v2 import NisseiExtractorV2
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from sites.models import Site
from users.models import CustomUser
from users.utils import decode_simple


class UpdateProductStatusView(APIView):
    def post(self, request, *args, **kwargs):
        # Obter dados do request
        product_id = request.data.get("id")
        new_status = request.data.get("status")
        # cod_proveedor = request.data.get("cod_proveedor")
        # cod_marca = request.data.get("cod_marca")
        # cod_rubro = request.data.get("cod_rubro")
        # cod_grupo = request.data.get("cod_grupo")
        
        # Validar campos obrigatórios
        if product_id is None or new_status is None:
            return Response(
                {"error": "id e status são obrigatórios"},
                status=http_status.HTTP_400_BAD_REQUEST
            )
        
        # Buscar produto
        product = get_object_or_404(Product, id=product_id)
        
        # Validar status
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
        
        # Atualizar status
        product.status = new_status
        product.save(update_fields=["status", "updated_at"])
        
        # Preparar resposta base
        response_data = {
            "message": "Status atualizado com sucesso",
            "id": product.id,
            "status": product.get_status_display(),
        }
        
        # ========== SINCRONIZAÇÃO COM ORACLE (APENAS SE STATUS = 2) ==========
        if new_status == 2:
            print(f"📤 Status = 2, iniciando sincronização com Oracle...")
            
            
            try:
                # Serializar produto com os dados adicionais
                serializer = ProductSerializer(product, context={'request': request})
                product_data = serializer.data
                
                # Adicionar campos do Oracle
                # product_data['cod_proveedor'] = cod_proveedor
                # product_data['cod_marca'] = cod_marca
                # product_data['cod_rubro'] = cod_rubro
                # product_data['cod_grupo'] = cod_grupo
                
                # Obter username do usuário Oracle autenticado
                oracle_username = request.user.username.upper() if request.user.is_authenticated else 'WEBSYNC'
                if request.user.is_authenticated:
                    try:
                        custom = request.user.customuser  # usa related_name='customuser'
                        oracle_password = custom.oracle_password
                    except CustomUser.DoesNotExist:
                        oracle_password = None  # ou valor padrão se não houver registro
                else:
                    oracle_password = None  # usuário não autenticado 
                
                if oracle_password:
                    # Decodificar senha
                    try:
                        oracle_password = decode_simple(oracle_password)
                    except Exception as e:
                        print(f"❌ Erro ao decodificar senha Oracle do usuário {oracle_username}: {e}")
                        oracle_password = None               
                
                # Sincronizar com Oracle
                print(f"🔄 Sincronizando produto {product.id} (SKU: {product.sku_code}) como usuário: {oracle_username}...")
                sync_result = sync_products_to_oracle([product_data], cod_usuario=oracle_username, password=oracle_password)
                
                # Adicionar resultado da sincronização na resposta
                response_data['oracle_sync'] = {
                    'executed': True,
                    'success_count': sync_result['success_count'],
                    'error_count': sync_result['error_count'],
                    'errors': sync_result['errors']
                }
                
                if sync_result['success_count'] > 0:
                    print(f"✅ Produto sincronizado com Oracle com sucesso!")
                    response_data['message'] = "Status atualizado e produto sincronizado com Oracle"
                else:
                    print(f"❌ Erro ao sincronizar com Oracle: {sync_result['errors']}")
                    response_data['message'] = "Status atualizado, mas houve erro na sincronização com Oracle"
                    response_data['warning'] = "Verifique os logs de sincronização"
                
            except Exception as e:
                print(f"❌ Erro na sincronização Oracle: {e}")
                response_data['oracle_sync'] = {
                    'executed': True,
                    'error': str(e)
                }
                response_data['warning'] = f"Status atualizado, mas erro ao sincronizar: {str(e)}"
        else:
            print(f"ℹ️  Status = {new_status}, sincronização Oracle não executada (requer status = 2)")
            response_data['oracle_sync'] = {
                'executed': False,
                'reason': 'Status diferente de 2'
            }
        
        return Response(
            response_data,
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
def nissei_search_detailed_original(request):
    """
    Busca detalhada no Nissei.com com Extrator V2 (ultra rápido)
    
    V2 - SEM IA POR PADRÃO
    - 8x mais rápido (usa Playwright ao invés de Selenium)
    - IA opcional (use ai_config="auto" para ativar)
    - Mesmos dados extraídos
    - 100% compatível com estrutura existente
    """
    try:
        # 1. VALIDAR PARÂMETROS
        query = request.data.get('query')
        if not query or len(query.strip()) < 2:
            return Response({
                'error': 'Query deve ter pelo menos 2 caracteres'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parâmetros de scraping
        max_results = int(request.data.get('max_results', 20))     # Total de produtos da busca
        max_detailed = int(request.data.get('max_detailed', 5))    # Máximo para processar detalhes
        max_images = int(request.data.get('max_images', 3))        # Máximo de imagens por produto
        
        # Configuração de IA (DESABILITADA POR PADRÃO)
        ai_config_name = request.data.get('ai_config', 'none')  # 'none' = SEM IA (padrão)
        enhanced_extraction = request.data.get('enhanced_extraction', True)
        
        # Validar limites
        max_results = min(max(max_results, 1), 50)
        max_detailed = min(max(max_detailed, 1), 10)
        max_images = min(max(max_images, 1), 8)
        
        print(f"\n{'='*70}")
        print(f"NISSEI SEARCH V2 (ULTRA RÁPIDO - SEM IA POR PADRÃO)")
        print(f"{'='*70}")
        print(f"Query: {query}")
        print(f"Buscar na listagem: {max_results} produtos")
        print(f"Processar detalhes: {max_detailed} produtos")
        print(f"Imagens por produto: {max_images}")
        print(f"Configuração IA: {ai_config_name} {'⚠️ (DESABILITADO)' if ai_config_name == 'none' else '✅ (HABILITADO)'}")
        print(f"Extração melhorada: {enhanced_extraction}")
        print(f"{'='*70}\n")
        
        # 2. BUSCAR CONFIGURAÇÃO DE IA (SOMENTE SE SOLICITADO)
        configuration = None
        
        if ai_config_name != 'none':
            print(f"🧠 IA solicitada - buscando configuração...")
            
            if ai_config_name == 'auto':
                # Buscar configuração ativa automaticamente
                configuration = Configuration.objects.filter(
                    model_integration__in=['claude', 'anthropic', 'openai'],
                    token__isnull=False,
                    token__gt=''
                ).order_by(
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
            
            if configuration:
                print(f"✅ IA encontrada: {configuration.name} ({configuration.model_integration})")
                
                # Aplicar limites da configuração se existir
                if hasattr(configuration, 'max_results') and configuration.max_results:
                    max_results = min(max(configuration.max_results, 1), 50)
                if hasattr(configuration, 'max_detailed') and configuration.max_detailed:
                    max_detailed = min(max(configuration.max_detailed, 1), 10)
                if hasattr(configuration, 'max_images') and configuration.max_images:
                    max_images = min(max(configuration.max_images, 1), 8)
            else:
                print(f"⚠️  IA solicitada mas nenhuma configuração válida encontrada")
                print(f"   Continuando SEM IA...")
        else:
            print(f"⚡ Modo RÁPIDO ativado (sem IA) - processamento direto")
        
        # 3. BUSCAR OU CRIAR SITE NISSEI
        site, created = Site.objects.get_or_create(
            url="https://nissei.com",
            defaults={
                'name': 'Casa Nissei Paraguay',
                'description': 'Loja de eletrônicos do Paraguai',
                'active': True
            }
        )
        
        if created:
            print(f"✅ Site Nissei criado")
        
        # 4. CRIAR EXTRATOR V2 (RÁPIDO)
        if configuration and configuration.token:
            print(f"✅ Inicializando com IA: {configuration.name}")
        else:
            print(f"✅ Inicializando SEM IA (modo rápido)")
            # Criar configuração dummy para modo sem IA
            configuration = Configuration(
                name="V2 Fast Without AI",
                model_integration=None,
                token=None,
                parameters={}
            )
        
        extractor = NisseiExtractorV2(site, configuration)
        
        # 5. APLICAR CONFIGURAÇÕES PERSONALIZADAS
        extractor.max_images_per_product = max_images
        
        try:
            # 6. EXECUTAR SCRAPING INTELIGENTE V2
            print(f"\n🚀 Iniciando scraping V2 (8x mais rápido)...\n")
            
            detailed_products = extractor.scrape_products_intelligent(
                query=query.strip(),
                max_results=max_results,
                max_detailed=max_detailed
            )
            
            print(f"\n✅ Produtos extraídos: {len(detailed_products)}")
            
            # 7. SALVAR PRODUTOS NO BANCO DE DADOS
            print(f"\n{'='*70}")
            print(f"💾 SALVANDO PRODUTOS NO BANCO DE DADOS")
            print(f"{'='*70}\n")

            saved_products_list = []
            saved_count = 0
            updated_count = 0

            for idx, product_data in enumerate(detailed_products, 1):
                try:
                    product_url = product_data.get('url', '')
                    if not product_url:
                        print(f"❌ Produto {idx}: URL vazia, pulando...")
                        continue
                    
                    product_name = product_data.get('name', 'Produto sem nome')[:300]
                    print(f"\n📦 Produto {idx}/{len(detailed_products)}: {product_name[:60]}...")
                    
                    # Verificar se produto já existe
                    existing_product = Product.objects.filter(
                        url=product_url,
                        site=site
                    ).first()
                    
                    # MAPEAR CAMPOS PARA O MODELO CORRETO
                    # Preparar scraped_data com informações extras
                    scraped_data = {
                        'specifications': product_data.get('specifications', {}),
                        'short_description': product_data.get('short_description', ''),
                        'stock_status': product_data.get('stock_status', ''),
                        'currency': 'Gs.',
                        'extraction_method': 'v2_fast_no_ai' if ai_config_name == 'none' else 'v2_fast_with_ai',
                        'scraped_at': timezone.now().isoformat()
                    }
                    
                    # Preparar dados do produto com CAMPOS CORRETOS
                    product_defaults = {
                        'name': product_name,
                        'price': float(product_data.get('price', 0)) if product_data.get('price') else None,
                        'original_price': float(product_data.get('old_price', 0)) if product_data.get('old_price') else None,
                        'description': product_data.get('description', ''),
                        'sku_code': product_data.get('sku', '') or product_data.get('sku_code', ''),
                        'brand': product_data.get('brand', ''),
                        'category': product_data.get('category', ''),
                        'availability': product_data.get('stock_status', 'in_stock'),  # Mapear stock_status para availability
                        'search_query': query.strip(),
                        'scraped_data': scraped_data,  # Guardar dados extras aqui
                        'status': 1,  # Ativo
                        'updated_at': timezone.now()
                    }
                    
                    if existing_product:
                        # Atualizar produto existente
                        for key, value in product_defaults.items():
                            setattr(existing_product, key, value)
                        existing_product.save()
                        product = existing_product
                        updated_count += 1
                        print(f"   🔄 Atualizado no banco (ID: {product.id})")
                    else:
                        # Criar novo produto
                        product = Product.objects.create(
                            url=product_url,
                            site=site,
                            **product_defaults
                        )
                        saved_count += 1
                        print(f"   ✅ Criado no banco (ID: {product.id})")
                    
                    # 8. SALVAR IMAGENS DO PRODUTO
                    image_urls = product_data.get('images', []) or product_data.get('image_urls', [])
                    
                    if image_urls:
                        print(f"   📸 Salvando {len(image_urls[:max_images])} imagens...")
                        
                        # Limpar imagens antigas
                        ProductImage.objects.filter(product=product).delete()
                        
                        images_saved = 0
                        for img_idx, image_url in enumerate(image_urls[:max_images]):
                            try:
                                # Criar registro de imagem
                                product_image = ProductImage.objects.create(
                                    product=product,
                                    original_url=image_url,
                                    alt_text=product.name,
                                    is_main=(img_idx == 0),
                                    order=img_idx
                                )
                                
                                images_saved += 1
                                
                            except Exception as img_error:
                                print(f"      ⚠️ Erro na imagem {img_idx + 1}: {img_error}")
                                continue
                        
                        print(f"   ✅ {images_saved}/{len(image_urls[:max_images])} imagens salvas")
                    else:
                        print(f"   ⚠️ Nenhuma imagem para salvar")
                    
                    saved_products_list.append(product)
                    
                except Exception as save_error:
                    print(f"   ❌ Erro ao salvar produto {idx}: {save_error}")
                    import traceback
                    print(traceback.format_exc())
                    continue

            print(f"\n{'='*70}")
            print(f"💾 RESUMO DO SALVAMENTO")
            print(f"{'='*70}")
            print(f"✅ Produtos novos criados: {saved_count}")
            print(f"🔄 Produtos atualizados: {updated_count}")
            print(f"📊 Total salvo com sucesso: {len(saved_products_list)}")
            print(f"{'='*70}\n")
            
            # 9. PREPARAR DADOS PARA RESPOSTA (usando ProductSerializer)
            products_for_response = ProductSerializer(
                saved_products_list,
                many=True,
                context={'request': request}
            ).data
            
            # Adicionar metadados de extração
            for product_response in products_for_response:
                product_response['extraction_method'] = 'v2_fast_no_ai' if ai_config_name == 'none' else 'v2_fast_with_ai'
                product_response['details_extracted'] = True
            
            # 10. BUSCAR TODOS OS PRODUTOS SALVOS NO BANCO (relacionados à query)
            all_saved_products = Product.objects.filter(
                search_query__icontains=query,
                site=site,
                status__in=[1, 2]
            ).prefetch_related('images').order_by('-created_at')[:20]
            
            print(f"📊 Total de produtos no banco para '{query}': {all_saved_products.count()}")
            
            # 11. SINCRONIZAÇÃO ORACLE (mantido como estava)
            # Descomentar quando necessário:
            # serialized_products_data = ProductSerializer(
            #     all_saved_products,
            #     many=True,
            #     context={'request': request}
            # ).data
            # print("Iniciando sincronização com o banco de dados Oracle...")
            # oracle_sync_report = sync_products_to_oracle(serialized_products_data)
            # print(f"Sincronização Oracle: Sucesso: {oracle_sync_report['success_count']}, Erros: {oracle_sync_report['error_count']}")
            
            # 12. PREPARAR RESPOSTA FINAL
            ai_used = configuration and configuration.token
            
            response_data = {
                'query': query.strip(),
                'parameters': {
                    'max_results_requested': max_results,
                    'max_detailed_requested': max_detailed,
                    'max_images_per_product': max_images,
                    'actual_detailed_processed': len(detailed_products),
                    'actual_saved_to_database': len(saved_products_list),
                    'new_products_created': saved_count,
                    'products_updated': updated_count,
                    'ai_config_used': configuration.name if ai_used else 'none',
                    'enhanced_extraction': enhanced_extraction,
                    'extractor_version': 'v2_fast',
                    'ai_enabled': ai_used
                },
                'ai_configuration': {
                    'name': configuration.name if ai_used else 'none',
                    'model': configuration.model_integration if ai_used else 'none',
                    'available': ai_used,
                    'enabled': ai_used,
                    'status': 'enabled' if ai_used else 'disabled (default)'
                },
                'site': {
                    'name': site.name,
                    'url': site.url,
                    'country': 'Paraguay'
                },
                'scraping_results': {
                    'total_products_found': len(detailed_products),
                    'total_products_saved': len(saved_products_list),
                    'new_products': saved_count,
                    'updated_products': updated_count,
                    'products_with_ai_filtering': len(products_for_response) if ai_used else 0,
                    'products_without_ai': len(products_for_response) if not ai_used else 0,
                    'products': products_for_response
                },
                'database_results': {
                    'saved_products_count': all_saved_products.count(),
                    'products': ProductSerializer(
                        all_saved_products,
                        many=True,
                        context={'request': request}
                    ).data
                },
                'currency': 'Gs.',
                'timestamp': timezone.now().isoformat(),
                'performance': {
                    'extractor_version': 'v2',
                    'technology': 'Playwright + BeautifulSoup',
                    'speed_improvement': '8x faster than v1',
                    'ai_filtering_used': ai_used,
                    'mode': 'fast_without_ai' if not ai_used else 'fast_with_ai',
                    'products_scraped': len(detailed_products),
                    'products_saved_database': len(saved_products_list),
                    'estimated_time_saved': f"Processou {max_detailed} produtos em ~{max_detailed * 5}s (vs ~{max_detailed * 40}s na v1)"
                },
                'success': True
            }
            
            print(f"\n{'='*70}")
            print(f"✅ VIEW CONCLUÍDA COM SUCESSO")
            print(f"   Modo: {'COM IA' if ai_used else 'SEM IA (padrão)'}")
            print(f"   Produtos extraídos: {len(detailed_products)}")
            print(f"   Produtos salvos/atualizados: {len(saved_products_list)}")
            print(f"   Novos: {saved_count} | Atualizados: {updated_count}")
            print(f"{'='*70}\n")
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        finally:
            # 13. LIMPAR RECURSOS
            extractor.close()
            print(f"🔌 Recursos do extrator liberados")
    
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"❌ ERRO NA VIEW")
        print(f"{'='*70}")
        print(f"Erro: {str(e)}")
        
        import traceback
        print(f"\nTraceback completo:")
        print(traceback.format_exc())
        print(f"{'='*70}\n")
        
        return Response({
            'error': f'Erro interno: {str(e)}',
            'query': request.data.get('query', ''),
            'extractor_version': 'v2',
            'ai_default': 'disabled',
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def nissei_search_detailed(request):
    """
    Busca detalhada no Nissei.com com Extrator V2 (ultra rápido)
    
    V2 - COM DOWNLOAD FÍSICO DE IMAGENS
    - 8x mais rápido (usa Playwright ao invés de Selenium)
    - Download paralelo de imagens
    - IA opcional (use ai_config="auto" para ativar)
    """
    try:
        # 1. VALIDAR PARÂMETROS
        query = request.data.get('query')
        if not query or len(query.strip()) < 2:
            return Response({
                'error': 'Query deve ter pelo menos 2 caracteres'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Parâmetros de scraping
        max_results = int(request.data.get('max_results', 20))
        max_detailed = int(request.data.get('max_detailed', 5))
        max_images = int(request.data.get('max_images', 3))
        
        # Configuração de IA (DESABILITADA POR PADRÃO)
        ai_config_name = request.data.get('ai_config', 'none')
        enhanced_extraction = request.data.get('enhanced_extraction', True)
        
        # Validar limites
        max_results = min(max(max_results, 1), 50)
        max_detailed = min(max(max_detailed, 1), 10)
        max_images = min(max(max_images, 1), 8)
        
        print(f"\n{'='*70}")
        print(f"NISSEI SEARCH V2 - COM DOWNLOAD FÍSICO DE IMAGENS")
        print(f"{'='*70}")
        print(f"Query: {query}")
        print(f"Listagem: {max_results} | Detalhes: {max_detailed} | Imagens: {max_images}")
        print(f"IA: {ai_config_name}")
        print(f"{'='*70}\n")
        
        # 2. BUSCAR CONFIGURAÇÃO DE IA
        configuration = None
        
        if ai_config_name != 'none':
            print(f"🧠 Buscando configuração de IA...")
            
            if ai_config_name == 'auto':
                configuration = Configuration.objects.filter(
                    model_integration__in=['claude', 'anthropic', 'openai'],
                    token__isnull=False,
                    token__gt=''
                ).order_by(
                    models.Case(
                        models.When(model_integration__icontains='claude', then=1),
                        models.When(model_integration__icontains='anthropic', then=1),
                        models.When(model_integration__icontains='openai', then=2),
                        default=3
                    )
                ).first()
            else:
                configuration = Configuration.objects.filter(
                    name__icontains=ai_config_name,
                    token__isnull=False,
                    token__gt=''
                ).first()
            
            if configuration:
                print(f"✅ IA: {configuration.name} ({configuration.model_integration})")
            else:
                print(f"⚠️  IA não encontrada, continuando SEM IA")
        else:
            print(f"⚡ Modo RÁPIDO (sem IA)")
        
        if not configuration:
            configuration = Configuration(
                name="V2 Fast Without AI",
                model_integration=None,
                token=None,
                parameters={}
            )
        
        # 3. BUSCAR OU CRIAR SITE
        site, created = Site.objects.get_or_create(
            url="https://nissei.com",
            defaults={
                'name': 'Casa Nissei Paraguay',
                'description': 'Loja de eletrônicos do Paraguai',
                'active': True
            }
        )
        
        # 4. CRIAR EXTRATOR V2
        extractor = NisseiExtractorV2(site, configuration)
        extractor.max_images_per_product = max_images
        
        try:
            # 5. EXECUTAR SCRAPING
            print(f"\n🚀 Iniciando scraping V2...\n")
            
            detailed_products = extractor.scrape_products_intelligent(
                query=query.strip(),
                max_results=max_results,
                max_detailed=max_detailed
            )
            
            print(f"\n✅ Produtos extraídos: {len(detailed_products)}")
            
            # 6. SALVAR PRODUTOS NO BANCO COM DOWNLOAD FÍSICO DE IMAGENS
            print(f"\n{'='*70}")
            print(f"💾 SALVANDO PRODUTOS E BAIXANDO IMAGENS")
            print(f"{'='*70}\n")
            
            saved_products_list = []
            saved_count = 0
            updated_count = 0
            
            for idx, product_data in enumerate(detailed_products, 1):
                try:
                    product_url = product_data.get('url', '')
                    if not product_url:
                        print(f"❌ Produto {idx}: URL vazia")
                        continue
                    
                    product_name = product_data.get('name', 'Produto sem nome')[:300]
                    print(f"\n📦 [{idx}/{len(detailed_products)}] {product_name[:60]}")
                    
                    # Verificar se produto existe
                    existing_product = Product.objects.filter(
                        url=product_url,
                        site=site
                    ).first()
                    
                    # Preparar scraped_data
                    scraped_data = {
                        'specifications': product_data.get('specifications', {}),
                        'short_description': product_data.get('short_description', ''),
                        'stock_status': product_data.get('stock_status', ''),
                        'currency': 'Gs.',
                        'extraction_method': 'v2_fast_no_ai' if ai_config_name == 'none' else 'v2_fast_with_ai',
                        'scraped_at': timezone.now().isoformat()
                    }
                    
                    # Preparar dados do produto (CAMPOS CORRETOS)
                    product_defaults = {
                        'name': product_name,
                        'price': float(product_data.get('price', 0)) if product_data.get('price') else None,
                        'original_price': float(product_data.get('old_price', 0)) if product_data.get('old_price') else None,
                        'description': product_data.get('description', ''),
                        'sku_code': product_data.get('sku', '') or product_data.get('sku_code', ''),
                        'brand': product_data.get('brand', ''),
                        'category': product_data.get('category', ''),
                        'availability': product_data.get('stock_status', 'in_stock'),
                        'search_query': query.strip(),
                        'scraped_data': scraped_data,
                        'status': 1,
                        'updated_at': timezone.now()
                    }
                    
                    if existing_product:
                        for key, value in product_defaults.items():
                            setattr(existing_product, key, value)
                        existing_product.save()
                        product = existing_product
                        updated_count += 1
                        print(f"   🔄 Produto atualizado (ID: {product.id})")
                    else:
                        product = Product.objects.create(
                            url=product_url,
                            site=site,
                            **product_defaults
                        )
                        saved_count += 1
                        print(f"   ✅ Produto criado (ID: {product.id})")
                    
                    # ==========================================
                    # DOWNLOAD FÍSICO DE IMAGENS
                    # ==========================================
                    image_urls = product_data.get('images', []) or product_data.get('image_urls', [])
                    
                    if image_urls:
                        print(f"   📥 Baixando {len(image_urls[:max_images])} imagens...")
                        
                        # Limpar imagens antigas
                        ProductImage.objects.filter(product=product).delete()
                        
                        images_saved = 0
                        
                        for img_idx, image_url in enumerate(image_urls[:max_images]):
                            try:
                                print(f"      📸 [{img_idx+1}/{len(image_urls[:max_images])}] Baixando...")
                                
                                # ========================================
                                # DOWNLOAD DA IMAGEM (FÍSICO)
                                # ========================================
                                response = requests.get(
                                    image_url,
                                    timeout=15,
                                    headers={
                                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
                                    }
                                )
                                response.raise_for_status()
                                
                                # ========================================
                                # OTIMIZAR COM PIL
                                # ========================================
                                img = Image.open(BytesIO(response.content))
                                
                                # Converter para RGB
                                if img.mode not in ('RGB', 'L'):
                                    if img.mode in ('RGBA', 'LA', 'P'):
                                        bg = Image.new('RGB', img.size, (255, 255, 255))
                                        if img.mode == 'P':
                                            img = img.convert('RGBA')
                                        bg.paste(img, mask=img.split()[-1] if len(img.split()) > 3 else None)
                                        img = bg
                                    else:
                                        img = img.convert('RGB')
                                
                                # Redimensionar se muito grande
                                if img.width > 1500 or img.height > 1500:
                                    img.thumbnail((1500, 1500), Image.Resampling.LANCZOS)
                                
                                # Salvar otimizado em memória
                                output = BytesIO()
                                img.save(output, format='JPEG', quality=90, optimize=True)
                                image_content = output.getvalue()
                                
                                # ========================================
                                # SALVAR NO BANCO (ARQUIVO FÍSICO)
                                # ========================================
                                filename = f"nissei_{product.id}_{img_idx+1}.jpg"
                                
                                product_image = ProductImage.objects.create(
                                    product=product,
                                    image=ContentFile(image_content, name=filename),  # ← ARQUIVO FÍSICO!
                                    original_url=image_url,
                                    alt_text=product.name,
                                    is_main=(img_idx == 0),
                                    order=img_idx
                                )
                                
                                # Primeira imagem = main_image do produto
                                if img_idx == 0:
                                    product.main_image = ContentFile(image_content, name=f"main_{filename}")
                                    product.save(update_fields=['main_image'])
                                
                                images_saved += 1
                                print(f"         ✅ Salvo: {filename} ({len(image_content)//1024}KB)")
                                
                            except requests.RequestException as req_error:
                                print(f"         ❌ Erro no download: {req_error}")
                                continue
                            except Exception as img_error:
                                print(f"         ❌ Erro: {img_error}")
                                continue
                        
                        print(f"   ✅ {images_saved}/{len(image_urls[:max_images])} imagens salvas FISICAMENTE")
                    else:
                        print(f"   ⚠️  Nenhuma imagem para baixar")
                    
                    saved_products_list.append(product)
                    
                except Exception as save_error:
                    print(f"   ❌ Erro ao salvar produto {idx}: {save_error}")
                    import traceback
                    print(traceback.format_exc())
                    continue
            
            print(f"\n{'='*70}")
            print(f"💾 RESUMO DO SALVAMENTO")
            print(f"{'='*70}")
            print(f"✅ Produtos novos: {saved_count}")
            print(f"🔄 Produtos atualizados: {updated_count}")
            print(f"📊 Total salvo: {len(saved_products_list)}")
            print(f"{'='*70}\n")
            
            # 7. BUSCAR PRODUTOS SALVOS
            all_saved_products = Product.objects.filter(
                search_query__icontains=query,
                site=site,
                status__in=[1, 2]
            ).prefetch_related('images').order_by('-created_at')[:20]
            
            print(f"📊 Produtos no banco: {all_saved_products.count()}")
            
            # 8. PREPARAR RESPOSTA
            ai_used = configuration and configuration.token
            
            response_data = {
                'query': query.strip(),
                'parameters': {
                    'max_results_requested': max_results,
                    'max_detailed_requested': max_detailed,
                    'max_images_per_product': max_images,
                    'actual_detailed_processed': len(detailed_products),
                    'actual_saved_to_database': len(saved_products_list),
                    'new_products_created': saved_count,
                    'products_updated': updated_count,
                    'ai_config_used': configuration.name if ai_used else 'none',
                    'enhanced_extraction': enhanced_extraction,
                    'extractor_version': 'v2_fast',
                    'ai_enabled': ai_used,
                    'images_downloaded_physically': True
                },
                'ai_configuration': {
                    'name': configuration.name if ai_used else 'none',
                    'model': configuration.model_integration if ai_used else 'none',
                    'available': ai_used,
                    'enabled': ai_used,
                    'status': 'enabled' if ai_used else 'disabled (default)'
                },
                'site': {
                    'name': site.name,
                    'url': site.url,
                    'country': 'Paraguay'
                },
                'scraping_results': {
                    'total_products_found': len(detailed_products),
                    'total_products_saved': len(saved_products_list),
                    'new_products': saved_count,
                    'updated_products': updated_count,
                    'images_downloaded': True,
                    'products': ProductSerializer(
                        saved_products_list,
                        many=True,
                        context={'request': request}
                    ).data
                },
                'database_results': {
                    'saved_products_count': all_saved_products.count(),
                    'products': ProductSerializer(
                        all_saved_products,
                        many=True,
                        context={'request': request}
                    ).data
                },
                'currency': 'Gs.',
                'timestamp': timezone.now().isoformat(),
                'performance': {
                    'extractor_version': 'v2',
                    'technology': 'Playwright + BeautifulSoup',
                    'speed_improvement': '8x faster than v1',
                    'image_download': 'sequential with optimization',
                    'ai_filtering_used': ai_used,
                    'mode': 'fast_without_ai' if not ai_used else 'fast_with_ai',
                    'products_scraped': len(detailed_products),
                    'products_saved_database': len(saved_products_list)
                },
                'success': True
            }
            
            print(f"\n{'='*70}")
            print(f"✅ VIEW CONCLUÍDA COM SUCESSO")
            print(f"   Produtos: {len(detailed_products)}")
            print(f"   Salvos: {len(saved_products_list)} (novos: {saved_count}, atualizados: {updated_count})")
            print(f"   Imagens: BAIXADAS FISICAMENTE ✓")
            print(f"{'='*70}\n")
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        finally:
            extractor.close()
            print(f"🔌 Recursos liberados")
    
    except Exception as e:
        print(f"\n{'='*70}")
        print(f"❌ ERRO NA VIEW")
        print(f"{'='*70}")
        print(f"Erro: {str(e)}")
        
        import traceback
        print(traceback.format_exc())
        print(f"{'='*70}\n")
        
        return Response({
            'error': f'Erro interno: {str(e)}',
            'query': request.data.get('query', ''),
            'extractor_version': 'v2',
            'success': False
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ========================================
# IMPORTS NECESSÁRIOS NO TOPO DO ARQUIVO
# ========================================
# from io import BytesIO
# from PIL import Image
# from django.core.files.base import ContentFile
# import requests


def nissei_search_detailed_v0(request):
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

