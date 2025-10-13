import cx_Oracle
from django.conf import settings


def get_oracle_connection():
    """
    Retorna um objeto de conexão cx_Oracle usando as configurações definidas
    no settings.py para o banco 'oracle_db'.
    """
    db_settings = settings.DATABASES['oracle_db']
    
    # cx_Oracle usa a DSN (Data Source Name) no formato HOST:PORT/SERVICE_NAME
    dsn = cx_Oracle.makedsn(
        host=db_settings['HOST'],
        port=db_settings['PORT'],
        service_name=db_settings['NAME'] # 'NAME' contém o SERVICE_NAME no seu settings
    )

    try:
        # Tenta a conexão com o banco Oracle
        conn = cx_Oracle.connect(
            user=db_settings['USER'],
            password=db_settings['PASSWORD'],
            dsn=dsn
        )
        return conn
    except cx_Oracle.Error as e:
        error, = e.args
        print(f"Erro de Conexão Oracle: {error.code} - {error.message}")
        raise ConnectionError("Falha ao conectar ao banco de dados Oracle.")
