"""
Backend de autenticação customizado usando Oracle Database
"""
import oracledb
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.conf import settings


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
        if not username or not password:
            return None
        
        # Configurações do Oracle
        oracle_host = settings.ORACLE_HOST
        oracle_port = settings.ORACLE_PORT
        oracle_service = settings.ORACLE_SERVICE_NAME
        
        try:
            # Tenta conectar no Oracle com as credenciais fornecidas
            dsn = oracledb.makedsn(oracle_host, oracle_port, service_name=oracle_service)
            
            # Se conseguir conectar, credenciais são válidas
            connection = oracledb.connect(
                user=username,
                password=password,
                dsn=dsn
            )
            
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
                    cursor.close()
                    connection.close()
                    return None
                    
            except oracledb.DatabaseError:
                # Se não tiver permissão para acessar dba_users, tudo bem
                # O importante é que conseguiu conectar
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
            
            # Não salvamos a senha no Django por segurança
            # A autenticação sempre será via Oracle
            
            return user
            
        except oracledb.Error as e:
            # Erro de autenticação Oracle (credenciais inválidas, conta bloqueada, etc)
            error_obj, = e.args
            
            # Log do erro para debug (opcional)
            print(f"Oracle authentication failed for user '{username}': [{error_obj.code}] {error_obj.message}")
            
            return None
            
        except Exception as e:
            # Erro inesperado
            print(f"Unexpected error during Oracle authentication: {e}")
            return None
    
    def get_user(self, user_id):
        """
        Recupera o usuário pelo ID (necessário para o Django)
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
