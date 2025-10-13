# Seu_App/oracle_sync.py
import cx_Oracle
import requests # Necessário para o BLOB/URL da imagem
from django.utils import timezone
from io import BytesIO # Para lidar com os bytes da imagem
from .oracle_connector import get_oracle_connection # Importa a nova função de conexão


COD_EMPRESA = '1' 
COD_MONEDA = 'GS.'
COD_USUARIO_DB = 'RINV' 

def sync_products_to_oracle(serialized_products):
    """
    Sincroniza uma lista de produtos serializados para as tabelas Oracle
    ST_ARTICULOS_PROV e ST_IMAG_ARTICULOS usando cx_Oracle.
    """
    sync_results = {'success_count': 0, 'error_count': 0, 'errors': []}
    oracle_conn = None

    try:
        # 1. Estabelece a conexão Oracle
        oracle_conn = get_oracle_connection()
        
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
                    'cod_proveedor': product_data.get('site_name', 'WEB')[:30],
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
                            COD_MONEDA_BASE, ESTADO, IND_WEB, IND_PRODUCTO
                        ) VALUES (
                            :cod_empresa, :cod_articulo, :description, :price_base, :original_price, 
                            :desc_corta, :url, :brand, :fec_proceso, :cod_proveedor, 
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
                        'cod_proveedor': product_data.get('site_name', 'WEB')[:30],
                        'cod_moneda': COD_MONEDA,
                        'estado': 'A'
                    }
                    cursor.execute(sql_insert, params_insert)

                # --- QUERY 2: ST_IMAG_ARTICULOS (Imagens) ---
                
                # A. Deleta imagens antigas
                sql_delete_images = """
                    DELETE FROM ST_IMAG_ARTICULOS 
                    WHERE COD_EMPRESA = :cod_empresa AND COD_ARTICULO = :cod_articulo
                """
                cursor.execute(sql_delete_images, {'cod_empresa': COD_EMPRESA, 'cod_articulo': sku})

                # B. Lista de URLs de imagens
                image_urls = []
                if product_data.get('main_image_url'):
                    image_urls.append({'url': product_data['main_image_url'], 'order': 1})
                if product_data.get('images'):
                    for img in product_data['images']:
                        if img.get('image_url'):
                            # Garante que a ordem não se sobreponha à principal
                            image_urls.append({'url': img['image_url'], 'order': img.get('order', len(image_urls) + 1) + 1})
                
                # C. Insere as novas imagens (Lidando com BLOB)
                sql_insert_image = """
                    INSERT INTO ST_IMAG_ARTICULOS (
                        COD_EMPRESA, COD_ARTICULO, NRO_ORDEN, IMAGEN, COD_USUARIO
                    ) VALUES (
                        :cod_empresa, :cod_articulo, :nro_orden, EMPTY_BLOB(), :cod_usuario
                    ) RETURNING IMAGEN INTO :lob_data
                """

                for index, img_data in enumerate(image_urls):
                    image_url = img_data['url']
                    
                    try:
                        # 1. Baixa a imagem
                        response = requests.get(image_url, timeout=10)
                        response.raise_for_status() # Levanta HTTPError para códigos 4xx/5xx
                        image_bytes = response.content
                        
                        # 2. Cria um objeto LOB (Large Object) para o BLOB
                        lob_data = cursor.var(cx_Oracle.BLOB)
                        
                        # 3. Executa o INSERT, pegando o LOB handle de volta
                        cursor.execute(sql_insert_image, {
                            'cod_empresa': COD_EMPRESA,
                            'cod_articulo': sku,
                            'nro_orden': index + 1,
                            'cod_usuario': COD_USUARIO_DB,
                            'lob_data': lob_data # O bind variable que receberá o BLOB handle
                        })
                        
                        # 4. Escreve os bytes da imagem no LOB
                        lob = lob_data.getvalue()
                        lob.write(image_bytes)
                        
                    except requests.exceptions.RequestException as req_e:
                        print(f"AVISO: Falha ao baixar imagem para SKU {sku}, URL {image_url}: {req_e}")
                        # Não registra como erro fatal de sincronização, apenas ignora a imagem.
                    except Exception as img_e:
                        print(f"AVISO: Erro ao inserir BLOB para SKU {sku}: {img_e}")
                        # Continua o loop para o próximo produto/imagem
                
                # Commit das alterações no banco Oracle
                oracle_conn.commit()
                sync_results['success_count'] += 1

        except cx_Oracle.Error as db_e:
            # Erro específico do Oracle
            oracle_conn.rollback()
            error, = db_e.args
            sync_results['error_count'] += 1
            sync_results['errors'].append(f"Erro DB Oracle SKU {sku}: {error.code} - {error.message}")
            
        except Exception as e:
            # Outros erros (ex: erro de tipo de dados)
            oracle_conn.rollback()
            sync_results['error_count'] += 1
            sync_results['errors'].append(f"Erro Geral SKU {sku}: {e}")

    # 3. Fecha a conexão após processar todos os produtos
    if oracle_conn:
        oracle_conn.close()

    return sync_results