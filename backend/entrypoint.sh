#!/bin/bash
set -e

# Cores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "=== INICIANDO CONTAINER ==="
echo "=========================================="

# ========== INFORMAÇÕES DO SISTEMA ==========
echo "User: $(whoami)"
echo "UID: $(id -u)"
echo "GID: $(id -g)"
echo "Workdir: $(pwd)"
echo "Python version: $(python --version)"

# Verificar se Chrome está instalado
if command -v google-chrome >/dev/null 2>&1; then
    echo -e "${GREEN}Chrome version: $(google-chrome --version)${NC}"
else
    echo -e "${RED}WARNING: Chrome não encontrado${NC}"
fi

# Verificar ChromeDriver
if command -v chromedriver >/dev/null 2>&1; then
    echo -e "${GREEN}ChromeDriver version: $(chromedriver --version)${NC}"
else
    echo -e "${YELLOW}WARNING: ChromeDriver não encontrado (será baixado pelo webdriver-manager)${NC}"
fi

# ========== VERIFICAÇÃO PLAYWRIGHT ==========
echo ""
echo "Verificando Playwright..."
if python -c "import playwright" 2>/dev/null; then
    echo -e "${GREEN}✓ Playwright Python: INSTALADO${NC}"
    
    # Verificar browsers do Playwright
    if [ -d "/ms-playwright" ]; then
        echo -e "${GREEN}✓ Playwright Browsers Path: /ms-playwright${NC}"
        
        # Verificar se chromium está instalado
        if [ -d "/ms-playwright/chromium"* ]; then
            CHROMIUM_PATH=$(ls -d /ms-playwright/chromium* 2>/dev/null | head -1)
            echo -e "${GREEN}✓ Playwright Chromium: INSTALADO${NC}"
            echo "  Path: $CHROMIUM_PATH"
        else
            echo -e "${RED}✗ Playwright Chromium: NÃO ENCONTRADO${NC}"
            echo -e "${YELLOW}  Tentando instalar browsers...${NC}"
            playwright install chromium || echo -e "${RED}  Falha na instalação${NC}"
        fi
    else
        echo -e "${RED}✗ Playwright Browsers: DIRETÓRIO NÃO EXISTE${NC}"
    fi
else
    echo -e "${RED}✗ Playwright Python: NÃO INSTALADO${NC}"
fi

# Verificar variável de ambiente
echo "PLAYWRIGHT_BROWSERS_PATH: $PLAYWRIGHT_BROWSERS_PATH"

# ========== VERIFICAÇÃO ORACLE CLIENT ==========
echo ""
echo "Verificando Oracle Instant Client..."
if [ -d "/opt/oracle/instantclient_21_15" ]; then
    echo -e "${GREEN}✓ Oracle Instant Client: INSTALADO${NC}"
    echo "  Path: /opt/oracle/instantclient_21_15"
    
    # Verificar libaio
    if ldconfig -p | grep -q libaio; then
        echo -e "${GREEN}✓ libaio: OK${NC}"
    else
        echo -e "${RED}✗ libaio: NÃO ENCONTRADA${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Oracle Instant Client: NÃO INSTALADO (modo thin será usado)${NC}"
fi

# ========== CORREÇÃO DE PERMISSÕES ==========
echo ""
echo "Verificando e corrigindo permissões..."

# Função para verificar e corrigir permissões
fix_permissions() {
    local dir=$1
    
    # Verifica se diretório existe
    if [ ! -d "$dir" ]; then
        echo -e "${YELLOW}⚠ $dir: NÃO EXISTE (tentando criar...)${NC}"
        mkdir -p "$dir" 2>/dev/null || {
            echo -e "${RED}✗ Falha ao criar $dir${NC}"
            return 1
        }
    fi
    
    # Tenta corrigir permissões (só funciona se for root ou dono)
    chmod -R 775 "$dir" 2>/dev/null || true
    
    # Verifica se tem permissão de escrita
    if [ -w "$dir" ]; then
        # Testa escrita real
        if touch "$dir/.test_write" 2>/dev/null; then
            rm -f "$dir/.test_write" 2>/dev/null
            echo -e "${GREEN}✓ $dir: OK${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠ $dir: PERMISSÃO LIMITADA${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ $dir: SEM PERMISSÃO DE ESCRITA${NC}"
        return 1
    fi
}

# Verificar e corrigir diretórios críticos
fix_permissions "/app/media"
fix_permissions "/app/media/products"
fix_permissions "/app/media/products/gallery"
fix_permissions "/app/media/products/images"
fix_permissions "/app/media/images"
fix_permissions "/app/media/uploads"
fix_permissions "/app/static"
fix_permissions "/app/staticfiles"
fix_permissions "/app/logs"
fix_permissions "/tmp/.cache/selenium"
fix_permissions "/app/.cache/selenium"

# Verificar Playwright browsers path
if [ -d "/ms-playwright" ]; then
    fix_permissions "/ms-playwright"
fi

# ========== ESTRUTURA DE DIRETÓRIOS ==========
echo ""
echo "Estrutura de diretórios:"
ls -la /app/ | head -15

# ========== TESTE DE CONECTIVIDADE ==========
echo ""
echo "Testando conectividade:"

# Internet
if timeout 5 ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    echo -e "${GREEN}Internet: OK${NC}"
else
    echo -e "${RED}Internet: FAIL${NC}"
fi

# Site específico
if timeout 5 ping -c 1 nissei.com >/dev/null 2>&1; then
    echo -e "${GREEN}Nissei.com: OK${NC}"
else
    echo -e "${YELLOW}Nissei.com: FAIL${NC}"
fi

# ========== AGUARDAR BANCO DE DADOS ==========
if [ "$DATABASE_HOST" ]; then
    echo ""
    echo "Aguardando banco de dados em $DATABASE_HOST:${DATABASE_PORT:-5432}..."
    timeout 30 bash -c "until nc -z $DATABASE_HOST ${DATABASE_PORT:-5432}; do sleep 1; done"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Banco de dados disponível${NC}"
    else
        echo -e "${RED}WARNING: Timeout aguardando banco de dados${NC}"
    fi
fi

# ========== MIGRAÇÕES DJANGO ==========
echo ""
echo "Executando migrações Django..."
if python manage.py migrate --noinput; then
    echo -e "${GREEN}Migrações executadas com sucesso${NC}"
else
    echo -e "${RED}WARNING: Falha nas migrações${NC}"
fi

# ========== COLETAR ARQUIVOS ESTÁTICOS ==========
echo ""
echo "Coletando arquivos estáticos..."
if python manage.py collectstatic --noinput 2>&1; then
    echo -e "${GREEN}Arquivos estáticos coletados${NC}"
else
    echo -e "${YELLOW}WARNING: Falha nos arquivos estáticos (pode ser normal)${NC}"
fi

# ========== VERIFICAÇÃO DJANGO ==========
echo ""
echo "Verificando configuração Django..."
python manage.py check 2>&1 || echo -e "${YELLOW}WARNING: Problemas na configuração Django${NC}"

# ========== CRIAR SUPERUSUÁRIO ==========
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo ""
    echo "Criando superusuário..."
    python manage.py createsuperuser --noinput \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" 2>/dev/null || \
        echo -e "${YELLOW}Superusuário já existe ou falha na criação${NC}"
fi

# ========== INICIAR SERVIDOR ==========
echo ""
echo "=========================================="
echo "=== INICIANDO SERVIDOR ==="
echo "=========================================="

# Executar comando passado como argumento (geralmente gunicorn ou runserver)
exec "$@"