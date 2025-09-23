#!/bin/bash

echo "=== INICIANDO CONTAINER ==="
echo "User: $(whoami)"
echo "UID: $(id -u)"
echo "GID: $(id -g)"
echo "Workdir: $(pwd)"
echo "Python version: $(python --version)"

# Verificar se Chrome está instalado
if command -v google-chrome >/dev/null 2>&1; then
    echo "Chrome version: $(google-chrome --version)"
else
    echo "WARNING: Chrome não encontrado"
fi

# Verificar ChromeDriver
if command -v chromedriver >/dev/null 2>&1; then
    echo "ChromeDriver version: $(chromedriver --version)"
else
    echo "WARNING: ChromeDriver não encontrado"
fi

# Verificar estrutura de diretórios (sem tentar criar como usuário não-root)
echo "Verificando diretórios existentes:"
ls -la /app/ | head -10

# Verificar se diretórios essenciais existem
if [ ! -d "/app/media" ]; then
    echo "ERRO: Diretório /app/media não existe"
else
    echo "Diretório media: OK"
fi

if [ ! -d "/app/static" ]; then
    echo "ERRO: Diretório /app/static não existe"
else
    echo "Diretório static: OK"
fi

# Verificar permissões de escrita (sem tentar criar se não tiver permissão)
echo "Testando permissões de escrita:"
if [ -w "/app/media" ]; then
    touch /app/media/test_write.tmp 2>/dev/null && rm /app/media/test_write.tmp 2>/dev/null && echo "Media: OK" || echo "Media: PARTIAL"
else
    echo "Media: NO_WRITE_PERMISSION"
fi

# Verificar conectividade (com timeout)
echo "Testando conectividade:"
timeout 5 ping -c 1 google.com >/dev/null 2>&1 && echo "Internet: OK" || echo "Internet: FAIL"
timeout 5 ping -c 1 nissei.com >/dev/null 2>&1 && echo "Nissei.com: OK" || echo "Nissei.com: FAIL"

# Aguardar banco de dados se necessário
if [ "$DATABASE_HOST" ]; then
    echo "Aguardando banco de dados..."
    timeout 30 bash -c 'until nc -z $DATABASE_HOST ${DATABASE_PORT:-5432}; do sleep 1; done'
    if [ $? -eq 0 ]; then
        echo "Banco de dados disponível"
    else
        echo "WARNING: Timeout aguardando banco de dados"
    fi
fi

# Executar migrações Django
echo "Executando migrações Django..."
python manage.py migrate --noinput 2>&1 || echo "WARNING: Falha nas migrações"

# Coletar arquivos estáticos (sem --clear para evitar problemas de permissão)
echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput 2>&1 || echo "WARNING: Falha nos arquivos estáticos"

# Verificar se o servidor pode iniciar
echo "Verificando configuração Django..."
python manage.py check --deploy 2>&1 || echo "WARNING: Problemas na configuração Django"

echo "=== INICIANDO SERVIDOR ==="

# Iniciar servidor Django (usando python, não python3)

if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput \
      --username "$DJANGO_SUPERUSER_USERNAME" \
      --email "$DJANGO_SUPERUSER_EMAIL" || true
fi

exec "$@"
