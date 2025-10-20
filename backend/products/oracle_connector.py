import oracledb
from django.conf import settings
import os


# Inicializa o modo "thick" do oracledb (necessário para Oracle < 12.1)
# Isso deve ser chamado UMA VEZ antes de qualquer conexão
def _init_thick_mode():
    """Inicializa o thick mode do oracledb uma única vez."""
    if not hasattr(_init_thick_mode, '_initialized'):
        try:
            # Caminho do Oracle Instant Client no Docker
            lib_dir = os.environ.get('ORACLE_HOME', '/opt/oracle/instantclient_21_15')
            
            print(f"Inicializando Oracle Client em modo THICK...")
            print(f"Caminho do Instant Client: {lib_dir}")
            
            # Verifica se o diretório existe
            if not os.path.exists(lib_dir):
                raise Exception(f"Diretório do Instant Client não encontrado: {lib_dir}")
            
            # Inicializa com o caminho explícito
            oracledb.init_oracle_client(lib_dir=lib_dir)
            print("✅ Oracle Client inicializado com sucesso em modo THICK!")
            
            _init_thick_mode._initialized = True
            
        except Exception as e:
            print(f"❌ ERRO ao inicializar Oracle Client: {e}")
            raise


# Chama a inicialização quando o módulo é importado
_init_thick_mode()


def get_oracle_connection(user, password):
    """
    Retorna um objeto de conexão oracledb usando as configurações definidas
    no settings.py para o banco 'oracle_db'.
    """ 
    
    # oracledb usa a DSN (Data Source Name) no formato HOST:PORT/SERVICE_NAME
    dsn = oracledb.makedsn(
        host=settings.ORACLE_HOST,
        port=settings.ORACLE_PORT,
        service_name=settings.ORACLE_SERVICE_NAME  # 'NAME' contém o SERVICE_NAME no seu settings
    )
    
    try:
        # Tenta a conexão com o banco Oracle
        conn = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn
        )
        return conn
    except oracledb.Error as e:
        error_obj, = e.args
        print(f"Erro de Conexão Oracle: {error_obj.code} - {error_obj.message}")
        raise ConnectionError("Falha ao conectar ao banco de dados Oracle.")
