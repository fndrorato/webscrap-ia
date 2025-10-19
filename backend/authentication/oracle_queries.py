"""
Helper functions para executar queries no Oracle
"""
import oracledb
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_oracle_connection(username, password):
    """
    Cria uma conexão Oracle usando as credenciais fornecidas.
    
    Args:
        username: Usuário Oracle
        password: Senha Oracle
        
    Returns:
        Connection object ou None se falhar
    """
    try:
        dsn = oracledb.makedsn(
            settings.ORACLE_HOST,
            settings.ORACLE_PORT,
            service_name=settings.ORACLE_SERVICE_NAME
        )
        
        connection = oracledb.connect(
            user=username,
            password=password,
            dsn=dsn
        )
        
        return connection
        
    except Exception as e:
        logger.error(f"Erro ao conectar no Oracle: {e}")
        return None


def fetch_fornecedores(connection):
    """
    Busca dados dos fornecedores.
    
    Returns:
        Lista de dicionários com cod_proveedor e nombre
    """
    query = """
        SELECT LTRIM(pe.nombre) as nombre, pr.cod_proveedor
        FROM personas pe, cm_proveedores pr 
        WHERE pr.cod_empresa = 1
          AND pr.cod_persona = pe.cod_persona
        ORDER BY pe.nombre
    """
    
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        
        # Converter para lista de dicionários
        columns = [col[0].lower() for col in cursor.description]
        results = []
        
        for row in cursor:
            results.append(dict(zip(columns, row)))
        
        cursor.close()
        logger.info(f"✅ Fornecedores buscados: {len(results)} registros")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar fornecedores: {e}")
        return []


def fetch_marcas(connection):
    """
    Busca dados das marcas.
    
    Returns:
        Lista de dicionários com cod_marca e descripcion
    """
    query = """
        SELECT m.cod_marca, m.descripcion
        FROM st_marcas m
        WHERE m.cod_empresa = 1
        ORDER BY m.descripcion
    """
    
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        
        columns = [col[0].lower() for col in cursor.description]
        results = []
        
        for row in cursor:
            results.append(dict(zip(columns, row)))
        
        cursor.close()
        logger.info(f"✅ Marcas buscadas: {len(results)} registros")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar marcas: {e}")
        return []


def fetch_rubros(connection):
    """
    Busca dados dos rubros.
    
    Returns:
        Lista de dicionários com cod_rubro e descripcion
    """
    query = """
        SELECT ru.cod_rubro, ru.descripcion
        FROM st_rubros ru
        WHERE cod_empresa = 1
        ORDER BY ru.descripcion
    """
    
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        
        columns = [col[0].lower() for col in cursor.description]
        results = []
        
        for row in cursor:
            results.append(dict(zip(columns, row)))
        
        cursor.close()
        logger.info(f"✅ Rubros buscados: {len(results)} registros")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar rubros: {e}")
        return []


def fetch_grupos(connection):
    """
    Busca dados dos grupos.
    
    Returns:
        Lista de dicionários com cod_grupo, cod_rubro e descripcion
    """
    query = """
        SELECT gr.cod_grupo, gr.cod_rubro, gr.descripcion
        FROM st_grupos gr
        WHERE cod_empresa = 1
        ORDER BY gr.descripcion
    """
    
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        
        columns = [col[0].lower() for col in cursor.description]
        results = []
        
        for row in cursor:
            results.append(dict(zip(columns, row)))
        
        cursor.close()
        logger.info(f"✅ Grupos buscados: {len(results)} registros")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar grupos: {e}")
        return []


def fetch_all_catalog_data(username, password):
    """
    Busca todos os dados de catálogo do Oracle em uma única conexão.
    
    Args:
        username: Usuário Oracle
        password: Senha Oracle
        
    Returns:
        Dicionário com todos os dados ou None se falhar
    """
    connection = None
    
    try:
        # Criar conexão
        connection = get_oracle_connection(username, password)
        
        if not connection:
            logger.error("❌ Não foi possível conectar ao Oracle")
            return None
        
        logger.info(f"📊 Buscando dados de catálogo para usuário: {username}")
        
        # Buscar todos os dados
        data = {
            'fornecedores': fetch_fornecedores(connection),
            'marcas': fetch_marcas(connection),
            'rubros': fetch_rubros(connection),
            'grupos': fetch_grupos(connection),
        }
        
        # Adicionar contadores para o frontend
        data['counts'] = {
            'fornecedores': len(data['fornecedores']),
            'marcas': len(data['marcas']),
            'rubros': len(data['rubros']),
            'grupos': len(data['grupos']),
        }
        
        logger.info(f"✅ Dados de catálogo buscados com sucesso: {data['counts']}")
        
        return data
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar dados de catálogo: {e}")
        return None
        
    finally:
        # Sempre fechar a conexão
        if connection:
            try:
                connection.close()
                logger.debug("🔒 Conexão Oracle fechada")
            except Exception as e:
                logger.error(f"❌ Erro ao fechar conexão: {e}")