import os
import oracledb
import requests  # Necessário para o BLOB/URL da imagem
import traceback
from django.utils import timezone
from io import BytesIO  # Para lidar com os bytes da imagem
from .oracle_connector import get_oracle_connection  # Importa a nova função de conexão
from products.models import Product, ProductImage


COD_EMPRESA = '1' 
COD_MONEDA = 'GS.'

def sync_products_to_oracle(serialized_products, cod_usuario=None, password=None):
    """
    Sincroniza uma lista de produtos serializados para as tabelas Oracle
    ST_ARTICULOS_PROV e ST_IMAG_ARTICULOS usando oracledb.
    
    Args:
        serialized_products: Lista de produtos serializados
        cod_usuario: Username do usuário Oracle que está fazendo a sincronização
                     (deve ser o username que fez login)
    """
    # Se não informar cod_usuario, usar um padrão
    if not cod_usuario:
        cod_usuario = 'WEBSYNC'
        print("⚠️  cod_usuario não informado, usando padrão: WEBSYNC")
    else:
        print(f"👤 Sincronizando como usuário: {cod_usuario}")
    
    sync_results = {'success_count': 0, 'error_count': 0, 'errors': []}
    oracle_conn = None

    try:
        # 1. Estabelece a conexão Oracle
        oracle_conn = get_oracle_connection(cod_usuario, password)
        
    except ConnectionError as e:
        sync_results['error_count'] = len(serialized_products)
        sync_results['errors'].append(f"Falha Crítica de Conexão: {e}")
        return sync_results

    # 2. Processa cada produto
    for product_data in serialized_products:
        sku = product_data.get('sku_code')
        if not sku:
            sync_results['error_count'] += 1
            sync_results['errors'].append(f"Produto sem sku_code (ID: {product_data.get('id')}), ignorado.")
            continue
            
        try:
            with oracle_conn.cursor() as cursor:
                
                # --- Preparação dos dados ---
                price_base = product_data.get('price')
                original_price = product_data.get('original_price')
                
                # Novos campos do Oracle
                cod_proveedor = product_data.get('cod_proveedor')
                cod_marca = product_data.get('cod_marca')
                cod_rubro = product_data.get('cod_rubro')
                cod_grupo = product_data.get('cod_grupo')

                try:
                    # Converte para float (lidando com vírgula e nulos)
                    price_base_num = float(str(price_base).replace(',', '.') if price_base else 0)
                except (ValueError, TypeError):
                    price_base_num = 0.0
                
                try:
                    original_price_num = float(str(original_price).replace(',', '.') if original_price else 0)
                except (ValueError, TypeError):
                    original_price_num = 0.0

                
                # --- QUERY 1: ST_ARTICULOS_PROV (Produto Principal) ---
                
                # 1. Tenta fazer um UPDATE:
                sql_update = """
                    UPDATE ST_ARTICULOS_PROV
                    SET 
                        DESCRIPCION = :description, 
                        PRECIO_BASE = :price_base, 
                        COSTO_PROM_EXT = :original_price,
                        DESC_CORTA = :desc_corta,
                        LINK_WEB = :url,
                        PALABRA_CLAVE = :brand,
                        FEC_PROCESO = :fec_proceso,
                        COD_PROVEEDOR = :cod_proveedor,
                        COD_MARCA = :cod_marca,
                        COD_RUBRO = :cod_rubro,
                        COD_GRUPO = :cod_grupo,
                        IND_WEB = 'S', 
                        FEC_ULTIMA_COMP = :fec_proceso 
                    WHERE COD_EMPRESA = :cod_empresa AND COD_ARTICULO = :cod_articulo
                """
                params_update = {
                    'description': product_data.get('name', '')[:100],
                    'price_base': price_base_num,
                    'original_price': original_price_num,
                    'desc_corta': product_data.get('description', '')[:500],
                    'url': product_data.get('url', '')[:150],
                    'brand': product_data.get('brand', '')[:200],
                    'fec_proceso': timezone.now().date(),
                    'cod_proveedor': cod_proveedor or '',
                    'cod_marca': cod_marca or '',
                    'cod_rubro': cod_rubro or '',
                    'cod_grupo': cod_grupo or '',
                    'cod_empresa': COD_EMPRESA,
                    'cod_articulo': sku
                }
                cursor.execute(sql_update, params_update)
                
                # 2. Se nenhuma linha foi afetada, faz o INSERT:
                if cursor.rowcount == 0:
                    sql_insert = """
                        INSERT INTO ST_ARTICULOS_PROV (
                            COD_EMPRESA, COD_ARTICULO, DESCRIPCION, PRECIO_BASE, COSTO_PROM_EXT, 
                            DESC_CORTA, LINK_WEB, PALABRA_CLAVE, FEC_PROCESO, COD_PROVEEDOR, 
                            COD_MARCA, COD_RUBRO, COD_GRUPO,
                            COD_MONEDA_BASE, ESTADO, IND_WEB, IND_PRODUTO
                        ) VALUES (
                            :cod_empresa, :cod_articulo, :description, :price_base, :original_price, 
                            :desc_corta, :url, :brand, :fec_proceso, :cod_proveedor, 
                            :cod_marca, :cod_rubro, :cod_grupo,
                            :cod_moneda, :estado, 'S', 'N'
                        )
                    """
                    params_insert = {
                        'cod_empresa': COD_EMPRESA,
                        'cod_articulo': sku,
                        'description': product_data.get('name', '')[:100],
                        'price_base': price_base_num,
                        'original_price': original_price_num,
                        'desc_corta': product_data.get('description', '')[:500],
                        'url': product_data.get('url', '')[:150],
                        'brand': product_data.get('brand', '')[:200],
                        'fec_proceso': timezone.now().date(),
                        'cod_proveedor': cod_proveedor or '',
                        'cod_marca': cod_marca or '',
                        'cod_rubro': cod_rubro or '',
                        'cod_grupo': cod_grupo or '',
                        'cod_moneda': COD_MONEDA,
                        'estado': 'A'
                    }
                    
                    # 💡 INÍCIO DO CÓDIGO DE DEBUG
                    print(f"--- DEBUG INSERT SKU: {sku} ---")
                    
                    # Formata a query para visualização (SUBSTITUIÇÃO BÁSICA)
                    debug_sql = sql_insert
                    for key, value in params_insert.items():
                        # Certifica-se de que strings sejam envoltas em aspas
                        # Cuidado: isto é para DEBUG e não deve ser usado para execução real
                        if isinstance(value, str):
                            # Simplificação: usa str() para Data/Date
                            value_str = f"'{str(value)}'"
                        elif value is None:
                            value_str = 'NULL'
                        else:
                            value_str = str(value)

                        # Substitui o placeholder no SQL
                        # Usa uma regex básica para garantir que substitua apenas :key
                        import re
                        debug_sql = re.sub(r':\b' + re.escape(key) + r'\b', value_str, debug_sql)


                    # Imprime a query formatada
                    print(debug_sql)
                    print(f"--- FIM DEBUG INSERT SKU: {sku} ---")
                    # 💡 FIM DO CÓDIGO DE DEBUG
                                        
                    cursor.execute(sql_insert, params_insert)

                # --- QUERY 2: ST_IMAG_ARTICULOS (Imagens) ---
                
                # A. Deleta imagens antigas
                # sql_delete_images = """
                #     DELETE FROM ST_IMAG_ARTICULOS 
                #     WHERE COD_EMPRESA = :cod_empresa AND COD_ARTICULO = :cod_articulo
                # """
                # cursor.execute(sql_delete_images, {'cod_empresa': COD_EMPRESA, 'cod_articulo': sku})

                # B. Buscar imagens do produto no Django
                # Tentar buscar pelo SKU ou pelo ID do produto
                try:
                    django_product = Product.objects.filter(sku_code=sku).first()
                    
                    if not django_product and 'id' in product_data:
                        django_product = Product.objects.filter(id=product_data['id']).first()
                    
                    if django_product and django_product.images.exists():
                        # Pegar imagens ordenadas
                        product_images = django_product.images.all().order_by('order', 'created_at')
                        
                        print(f"📸 Encontradas {product_images.count()} imagens para SKU {sku}")
                        
                        # C. Inserir as imagens no Oracle (lendo do disco)
                        sql_insert_image = """
                            INSERT INTO ST_IMAG_ARTICULOS (
                                COD_EMPRESA, COD_ARTICULO, NRO_ORDEN, IMAGEN, COD_USUARIO
                            ) VALUES (
                                :cod_empresa, :cod_articulo, :nro_orden, EMPTY_BLOB(), :cod_usuario
                            ) RETURNING IMAGEN INTO :lob_data
                        """
                        
                        for index, product_image in enumerate(product_images, start=1):
                            try:
                                # 1. Verificar se o arquivo existe no disco
                                if not product_image.image:
                                    print(f"⚠️  Imagem {index} sem arquivo para SKU {sku}")
                                    continue
                                
                                image_path = product_image.image.path
                                
                                if not os.path.exists(image_path):
                                    print(f"⚠️  Arquivo não encontrado: {image_path}")
                                    continue
                                
                                # 2. Ler arquivo da imagem do disco
                                with open(image_path, 'rb') as img_file:
                                    image_bytes = img_file.read()
                                
                                # 3. Criar objeto LOB (Large Object) para o BLOB
                                lob_data = cursor.var(oracledb.DB_TYPE_BLOB)
                                
                                # 4. Executar INSERT, pegando o LOB handle de volta
                                cursor.execute(sql_insert_image, {
                                    'cod_empresa': COD_EMPRESA,
                                    'cod_articulo': sku,
                                    'nro_ordem': index,
                                    'cod_usuario': cod_usuario,
                                    'lob_data': lob_data
                                })
                                
                                # 5. Escrever os bytes da imagem no LOB
                                lob = lob_data.getvalue()
                                lob.write(image_bytes)
                                
                                print(f"✅ Imagem {index} inserida para SKU {sku} ({len(image_bytes)} bytes)")
                                
                            except Exception as img_e:
                                print(f"⚠️  Erro ao inserir imagem {index} para SKU {sku}: {img_e}")
                                # Continua para próxima imagem
                                continue
                    else:
                        print(f"ℹ️  Nenhuma imagem encontrada no Django para SKU {sku}")
                        
                except Exception as e:
                    print(f"⚠️  Erro ao buscar imagens no Django para SKU {sku}: {e}")
                    # Continua sem imagens
                
                # Commit das alterações no banco Oracle
                oracle_conn.commit()
                sync_results['success_count'] += 1

        except oracledb.Error as db_e:
            # Erro específico do Oracle
            oracle_conn.rollback()
            
            error_code = 'N/A'
            error_message = str(db_e)
            
            # ➡️ TRATAMENTO DE ERRO ROBUSTO: Tenta extrair código e mensagem de forma segura
            if db_e.args:
                error_obj = db_e.args[0]
                # Verifica se o objeto de erro tem os atributos esperados
                if hasattr(error_obj, 'code'):
                    error_code = error_obj.code
                if hasattr(error_obj, 'message'):
                    error_message = error_obj.message
            
            sync_results['error_count'] += 1
            
            # Imprime no log para ver imediatamente o erro do DB
            print(f"❌ Erro DB Oracle REAL para SKU {sku}: {error_code} - {error_message}")
            
            # Registra no resultado
            sync_results['errors'].append(f"Erro DB Oracle SKU {sku}: {error_code} - {error_message}")
            
        except Exception as e:
            import traceback # 👈 Importe isso no topo do arquivo
            # Outros erros (ex: erro de tipo de dados)
            oracle_conn.rollback()
            sync_results['error_count'] += 1
            
            # 💡 Imprimir o traceback completo para diagnóstico
            print(f"\n❌ ERRO GERAL CRÍTICO NO PRODUTO {sku} ❌")
            traceback.print_exc()
            
            sync_results['errors'].append(f"Erro Geral SKU {sku}: {e}")

    # 3. Fecha a conexão após processar todos os produtos
    if oracle_conn:
        oracle_conn.close()

    return sync_results
