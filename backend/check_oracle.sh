#!/bin/bash
# Script para verificar a instalação do Oracle Instant Client

echo "========================================="
echo "Verificando Oracle Instant Client"
echo "========================================="

# 1. Verificar se o diretório existe
if [ -d "/opt/oracle/instantclient_21_15" ]; then
    echo "✅ Diretório do Instant Client encontrado"
    ls -la /opt/oracle/instantclient_21_15
else
    echo "❌ Diretório do Instant Client NÃO encontrado!"
    exit 1
fi

# 2. Verificar variáveis de ambiente
echo ""
echo "Variáveis de ambiente:"
echo "ORACLE_HOME = $ORACLE_HOME"
echo "LD_LIBRARY_PATH = $LD_LIBRARY_PATH"

# 3. Verificar se as bibliotecas estão acessíveis
echo ""
echo "Verificando bibliotecas:"
if ldconfig -p | grep -q libclntsh; then
    echo "✅ libclntsh encontrada no cache do ldconfig"
else
    echo "⚠️  libclntsh NÃO encontrada no cache"
fi

# 4. Testar Python oracledb
echo ""
echo "Testando python-oracledb:"
python3 << EOF
import oracledb
print(f"Versão oracledb: {oracledb.__version__}")

try:
    oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient_21_15")
    print("✅ Thick mode inicializado com sucesso!")
except Exception as e:
    print(f"❌ Erro ao inicializar thick mode: {e}")
EOF

echo ""
echo "========================================="
echo "Verificação concluída"
echo "========================================="