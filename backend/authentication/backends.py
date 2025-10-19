"""
Backend de autenticação customizado usando Oracle Database
"""
import oracledb
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.conf import settings
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Flag para garantir que thick mode é inicializado apenas uma vez
_thick_mode_initialized = False


def _init_thick_mode():
    """Inicializa o thick mode do oracledb uma única vez."""
    global _thick_mode_initialized
    
    if not _thick_mode_initialized:
        try:
            # Caminho do Oracle Instant Client no Docker
            lib_dir = "/opt/oracle/instantclient_21_15"
            
            logger.info(f"Inicializando Oracle Client em modo THICK: {lib_dir}")
            print(f"🔧 Inicializando Oracle Client em modo THICK: {lib_dir}")
            
            # Inicializa com o caminho explícito
            oracledb.init_oracle_client(lib_dir=lib_dir)
            
            logger.info("✅ Oracle Client inicializado com sucesso em modo THICK!")
            print("✅ Oracle Client inicializado com sucesso em modo THICK!")
            
            _thick_mode_initialized = True
            
        except Exception as e:
            logger.error(f"❌ ERRO ao inicializar Oracle Client: {e}")
            print(f"❌ ERRO ao inicializar Oracle Client: {e}")
            # Não lança exceção - deixa tentar em thin mode
            # (embora não vá funcionar com Oracle antigo)


# Inicializa o thick mode quando o módulo é importado
_init_thick_mode()


class OracleAuthBackend(BaseBackend):
    """
    Autentica usuários validando credenciais diretamente no banco Oracle.
    Se a conexão for bem-sucedida, o usuário é válido.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Tenta autenticar conectando no Oracle com as credenciais fornecidas.
        
        Args:
            request: HttpRequest object
            username: Nome de usuário Oracle
            password: Senha do usuário Oracle
            
        Returns:
            User object se autenticação bem-sucedida, None caso contrário
        """
        # LOG: Backend foi chamado
        logger.info(f"🔐 OracleAuthBackend.authenticate() chamado para username: {username}")
        print(f"🔐 OracleAuthBackend.authenticate() chamado para username: {username}")
        
        if not username or not password:
            logger.warning("⚠️  Username ou password não fornecidos")
            print("⚠️  Username ou password não fornecidos")
            return None
        
        # Configurações do Oracle
        oracle_host = settings.ORACLE_HOST
        oracle_port = settings.ORACLE_PORT
        oracle_service = settings.ORACLE_SERVICE_NAME
        
        logger.info(f"📡 Tentando conectar: {username}@{oracle_host}:{oracle_port}/{oracle_service}")
        print(f"📡 Tentando conectar: {username}@{oracle_host}:{oracle_port}/{oracle_service}")
        
        try:
            # Tenta conectar no Oracle com as credenciais fornecidas
            dsn = oracledb.makedsn(oracle_host, oracle_port, service_name=oracle_service)
            
            # Se conseguir conectar, credenciais são válidas
            connection = oracledb.connect(
                user=username,
                password=password,
                dsn=dsn
            )
            
            logger.info(f"✅ Conexão Oracle bem-sucedida para usuário: {username}")
            print(f"✅ Conexão Oracle bem-sucedida para usuário: {username}")
            
            # Buscar informações adicionais do usuário no Oracle (opcional)
            cursor = connection.cursor()
            
            try:
                # Tenta pegar informações do usuário
                cursor.execute("""
                    SELECT username, account_status, created 
                    FROM dba_users 
                    WHERE username = :username
                """, {'username': username.upper()})
                
                user_info = cursor.fetchone()
                
                if user_info and user_info[1] != 'OPEN':
                    # Conta Oracle não está ativa
                    logger.warning(f"⚠️  Conta Oracle '{username}' não está ativa: {user_info[1]}")
                    print(f"⚠️  Conta Oracle '{username}' não está ativa: {user_info[1]}")
                    cursor.close()
                    connection.close()
                    return None
                    
            except oracledb.DatabaseError as db_err:
                # Se não tiver permissão para acessar dba_users, tudo bem
                # O importante é que conseguiu conectar
                logger.debug(f"ℹ️  Não foi possível acessar dba_users (normal): {db_err}")
                pass
            
            cursor.close()
            connection.close()
            
            # Usuário válido no Oracle!
            # Criar ou atualizar usuário no Django (para compatibilidade com JWT)
            user, created = User.objects.get_or_create(
                username=username.lower(),
                defaults={
                    'is_active': True,
                    'is_staff': False,
                    'is_superuser': False,
                }
            )
            
            if created:
                logger.info(f"✨ Novo usuário Django criado para: {username}")
                print(f"✨ Novo usuário Django criado para: {username}")
            else:
                logger.info(f"♻️  Usuário Django existente: {username}")
                print(f"♻️  Usuário Django existente: {username}")
            
            # Não salvamos a senha no Django por segurança
            # A autenticação sempre será via Oracle
            
            return user
            
        except oracledb.Error as e:
            # Erro de autenticação Oracle (credenciais inválidas, conta bloqueada, etc)
            error_obj, = e.args
            
            # Log do erro para debug
            logger.error(f"❌ Oracle authentication failed for user '{username}': [{error_obj.code}] {error_obj.message}")
            print(f"❌ Oracle authentication failed for user '{username}': [{error_obj.code}] {error_obj.message}")
            
            return None
            
        except Exception as e:
            # Erro inesperado
            logger.error(f"❌ Unexpected error during Oracle authentication: {e}")
            print(f"❌ Unexpected error during Oracle authentication: {e}")
            return None
    
    def get_user(self, user_id):
        """
        Recupera o usuário pelo ID (necessário para o Django)
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None