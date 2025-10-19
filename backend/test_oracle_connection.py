#!/usr/bin/env python3
"""
Script de diagnóstico de conexão Oracle
Teste passo a passo para identificar onde está o problema
"""

import socket
import sys
import oracledb

# ========== CONFIGURAÇÕES DESCOBERTAS ==========
# Baseado na análise do seu servidor Oracle
ORACLE_HOST = "10.1.1.90"
ORACLE_PORT = 1521
ORACLE_SERVICE = "orcl"  # Confirmado via queries no banco

# ⚠️ AJUSTE APENAS ESTES DOIS:
ORACLE_USER = "INV"  # Oracle usa 'system', não 'root'!
ORACLE_PASSWORD = "abc1537"  # ← COLOQUE A SENHA CORRETA

# NOTA IMPORTANTE:
# Oracle NÃO tem usuário "root"!
# Usuários comuns: system, sys, scott, ou usuários customizados
# Se você não sabe a senha do 'system', peça ao DBA ou crie um novo usuário
# ===============================================

def test_step(step_num, description, func):
    """Executa um teste e mostra o resultado"""
    print(f"\n{'='*60}")
    print(f"TESTE {step_num}: {description}")
    print('='*60)
    try:
        result = func()
        print(f"  SUCESSO: {result}")
        return True
    except Exception as e:
        print(f"  FALHA: {e}")
        return False


def test_1_network():
    """Teste 1: Conectividade de rede básica via socket"""
    # Testa se consegue resolver o hostname/IP
    try:
        socket.gethostbyname(ORACLE_HOST)
        return f"Servidor {ORACLE_HOST} é acessível (DNS/IP resolvido)"
    except socket.error as e:
        raise Exception(f"Não consegue resolver {ORACLE_HOST}: {e}")


def test_2_tcp_connection():
    """Teste 2: Conexão TCP na porta do Oracle"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)

    result = sock.connect_ex((ORACLE_HOST, ORACLE_PORT))
    sock.close()

    if result == 0:
        return f"Porta {ORACLE_PORT} está ABERTA no servidor {ORACLE_HOST}"
    else:
        raise Exception(f"Porta {ORACLE_PORT} está FECHADA ou BLOQUEADA (firewall?)")

def test_3_oracle_listener():
    """Teste 3: Testar se o listener Oracle está respondendo"""
    try:
        # Tenta conectar sem credenciais (só para ver se listener responde)
        dsn = oracledb.makedsn(ORACLE_HOST, ORACLE_PORT, service_name=ORACLE_SERVICE)

        # Tenta com credenciais inválidas de propósito
        conn = oracledb.connect(
            user="usuario_invalido_teste",
            password="senha_invalida_teste",
            dsn=dsn
        )
        conn.close()
        return "Listener respondeu (não deveria chegar aqui)"

    except oracledb.Error as e:
        error_obj, = e.args
        error_code = error_obj.code
        error_msg = error_obj.message

        # ORA-01017 = credenciais inválidas (MAS O LISTENER RESPONDEU!)
        if error_code == 1017:
            return f"Listener Oracle está FUNCIONANDO! (erro esperado: {error_msg})"

        # ORA-12541 = Listener não encontrado
        elif error_code == 12541:
            raise Exception("Listener Oracle NÃO está rodando ou não está acessível")

        # ORA-12514 = Serviço não encontrado
        elif error_code == 12514:
            raise Exception(f"Listener respondeu, mas SERVICE_NAME '{ORACLE_SERVICE}' não existe")

        # Outros erros
        else:
            raise Exception(f"Erro do Oracle [{error_code}]: {error_msg}")


def test_4_oracle_connection():
    """Teste 4: Conexão completa com credenciais reais"""
    dsn = oracledb.makedsn(ORACLE_HOST, ORACLE_PORT, service_name=ORACLE_SERVICE)

    conn = oracledb.connect(
        user=ORACLE_USER,
        password=ORACLE_PASSWORD,
        dsn=dsn
    )

    # Testa uma query simples
    cursor = conn.cursor()
    cursor.execute("SELECT SYSDATE FROM DUAL")
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    return f"Conexão COMPLETA bem-sucedida! Data do servidor: {result[0]}"

def test_5_thick_mode_check():
    """Teste 5: Verificar se está usando Thick Mode"""
    try:
        oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient_21_15")
        return "Thick mode ATIVADO (Oracle Instant Client encontrado)"
    except Exception as e:
        return f"Rodando em Thin mode (sem Instant Client): {e}"


# ========== EXECUÇÃO DOS TESTES ==========
def main():
    print("\n" + "="*60)
    print("DIAGNÓSTICO DE CONEXÃO ORACLE")
    print("="*60)
    print(f"Servidor Oracle: {ORACLE_HOST}:{ORACLE_PORT}")
    print(f"Service Name: {ORACLE_SERVICE}")
    print(f"Usuário: {ORACLE_USER}")

    # Aviso se estiver usando 'root'
    if ORACLE_USER.lower() == 'root':
        print("\n" + "⚠️ " * 20)
        print("⚠️  ATENÇÃO: Oracle NÃO tem usuário 'root'!")
        print("⚠️  Usuários Oracle comuns: system, sys, scott")
        print("⚠️  Altere ORACLE_USER no script antes de continuar!")
        print("⚠️ " * 20)
        sys.exit(1)

    print("="*60)

    # Teste 5 primeiro (verificar modo)
    test_step(5, "Verificar modo Thick/Thin", test_5_thick_mode_check)

    # Teste 1: Rede
    if not test_step(1, "Verificar conectividade de rede", test_1_network):
        print("\n⚠️  PROBLEMA DE REDE: Servidor não está acessível")
        print("Possíveis causas:")
        print("  - Servidor está desligado")
        print("  - IP errado")
        print("  - Problema de roteamento de rede")
        sys.exit(1)

    # Teste 2: Porta TCP
    if not test_step(2, "Testar porta TCP do Oracle", test_2_tcp_connection):
        print("\n⚠️  PROBLEMA DE FIREWALL/PORTA:")
        print("Possíveis causas:")
        print("  - Firewall bloqueando porta 1521")
        print("  - Oracle Listener não está rodando")
        print("  - Porta Oracle diferente de 1521")
        print("\nComo verificar no servidor Oracle:")
        print("  lsnrctl status")
        sys.exit(1)

    # Teste 3: Listener
    if not test_step(3, "Testar Oracle Listener", test_3_oracle_listener):
        print("\n⚠️  PROBLEMA COM ORACLE LISTENER OU SERVICE_NAME")
        print("Possíveis causas:")
        print("  - SERVICE_NAME está errado")
        print("  - Listener Oracle não está configurado corretamente")
        print("\nComo verificar no servidor Oracle:")
        print("  lsnrctl status")
        print("  lsnrctl services")
        sys.exit(1)
    # Teste 4: Conexão completa
    if not test_step(4, "Conexão completa com credenciais", test_4_oracle_connection):
        print("\n⚠️  PROBLEMA DE AUTENTICAÇÃO")
        print("Possíveis causas:")
        print("  - Usuário ou senha incorretos")
        print("  - Conta Oracle bloqueada ou expirada")
        print("  - Falta de privilégios")
        print("\nComo verificar no servidor Oracle:")
        print("  SELECT username, account_status FROM dba_users WHERE username='SEU_USUARIO';")
        sys.exit(1)

    print("\n" + "="*60)
    print("  TODOS OS TESTES PASSARAM!")
    print("="*60)
    print("\nSua conexão Oracle está funcionando perfeitamente!")
    print("\n  Use estas configurações no seu Django settings.py:")
    print("-" * 60)
    print("DATABASES = {")
    print("    'oracle_db': {")
    print("        'ENGINE': 'django.db.backends.oracle',")
    print(f"        'NAME': '{ORACLE_SERVICE}',  # SERVICE_NAME")
    print(f"        'USER': '{ORACLE_USER}',")
    print("        'PASSWORD': 'sua_senha',")
    print(f"        'HOST': '{ORACLE_HOST}',")
    print(f"        'PORT': '{ORACLE_PORT}',")
    print("    }")
    print("}")
    print("-" * 60)
    print("\n  Dica: Use variáveis de ambiente para senha em produção!")
    print("   'PASSWORD': os.getenv('ORACLE_PASSWORD'),")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTeste interrompido pelo usuário")
        sys.exit(1)

