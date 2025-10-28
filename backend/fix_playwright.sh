#!/bin/bash
# Script para corrigir Playwright no Docker

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "=== FIX PLAYWRIGHT NO DOCKER ==="
echo "=========================================="

# 1. Fazer backup
echo -e "\n${YELLOW}1. Fazendo backup dos arquivos atuais...${NC}"
cp Dockerfile Dockerfile.backup.$(date +%Y%m%d_%H%M%S) || true
cp entrypoint.sh entrypoint.sh.backup.$(date +%Y%m%d_%H%M%S) || true
echo -e "${GREEN}✓ Backups criados${NC}"

# 2. Parar containers
echo -e "\n${YELLOW}2. Parando containers...${NC}"
docker-compose down
echo -e "${GREEN}✓ Containers parados${NC}"

# 3. Informar sobre substituição manual
echo -e "\n${YELLOW}3. AÇÃO NECESSÁRIA:${NC}"
echo "   Substitua os seguintes arquivos:"
echo "   - Dockerfile → usar Dockerfile_CORRECTED"
echo "   - entrypoint.sh → usar entrypoint_CORRECTED.sh"
echo ""
echo "   Os arquivos corrigidos estão em: outputs/"
echo ""
read -p "Pressione ENTER depois de substituir os arquivos..."

# 4. Rebuildar imagem
echo -e "\n${YELLOW}4. Rebuildando imagem Docker (pode demorar ~5-10min)...${NC}"
docker-compose build --no-cache backend
echo -e "${GREEN}✓ Imagem rebuilada${NC}"

# 5. Subir containers
echo -e "\n${YELLOW}5. Subindo containers...${NC}"
docker-compose up -d
echo -e "${GREEN}✓ Containers iniciados${NC}"

# 6. Aguardar inicialização
echo -e "\n${YELLOW}6. Aguardando inicialização (30s)...${NC}"
sleep 30

# 7. Verificar Playwright
echo -e "\n${YELLOW}7. Verificando instalação do Playwright...${NC}"
docker-compose exec -T backend python -c "from playwright.sync_api import sync_playwright; print('OK')" && \
    echo -e "${GREEN}✓ Playwright funcionando!${NC}" || \
    echo -e "${RED}✗ Erro no Playwright${NC}"

# 8. Verificar browsers
echo -e "\n${YELLOW}8. Verificando browsers instalados...${NC}"
docker-compose exec backend ls -la /ms-playwright/ | grep chromium && \
    echo -e "${GREEN}✓ Chromium instalado!${NC}" || \
    echo -e "${RED}✗ Chromium não encontrado${NC}"

# 9. Ver logs
echo -e "\n${YELLOW}9. Verificando logs do entrypoint...${NC}"
docker-compose logs backend | grep -A 5 "Verificando Playwright"

echo ""
echo "=========================================="
echo -e "${GREEN}=== INSTALAÇÃO CONCLUÍDA ===${NC}"
echo "=========================================="
echo ""
echo "Teste agora fazendo uma requisição:"
echo "POST /api/products/nissei/search/"
echo '{"query": "apple watch", "max_detailed": 2}'
echo ""
echo "Para ver logs em tempo real:"
echo "docker-compose logs -f backend"
echo ""