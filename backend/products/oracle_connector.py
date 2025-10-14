import oracledb
from django.conf import settings


def get_oracle_connection():
    """
    Retorna um objeto de conexão oracledb usando as configurações definidas
    no settings.py para o banco 'oracle_db'.
    """
    db_settings = settings.DATABASES['oracle_db']
    
    # oracledb usa a DSN (Data Source Name) no formato HOST:PORT/SERVICE_NAME
    dsn = oracledb.makedsn(
        host=db_settings['HOST'],
        port=db_settings['PORT'],
        service_name=db_settings['NAME']  # 'NAME' contém o SERVICE_NAME no seu settings
    )
    
    try:
        # Tenta a conexão com o banco Oracle
        conn = oracledb.connect(
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            dsn=dsn
        )
        return conn
    except oracledb.Error as e:
        error_obj, = e.args
        print(f"Erro de Conexão Oracle: {error_obj.code} - {error_obj.message}")
        raise ConnectionError("Falha ao conectar ao banco de dados Oracle.")