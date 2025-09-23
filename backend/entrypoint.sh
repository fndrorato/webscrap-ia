#!/bin/bash

echo "=== INICIANDO CONTAINER ==="
echo "User: $(whoami)"
echo "Workdir: $(pwd)"
echo "Python version: $(python3 --version)"

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

# Verificar estrutura de diretórios
echo "Verificando diretórios:"
ls -la /app/
echo "Media directory:"
ls -la /app/media/ 2>/dev/null || echo "Media directory não existe, criando..."

# Criar diretórios necessários
mkdir -p /app/media /app/static /app/logs
chmod -R 755 /app/media /app/static /app/logs

# Verificar permissões de escrita
echo "Testando permissões de escrita:"
touch /app/media/test_write.tmp 2>/dev/null && rm /app/media/test_write.tmp && echo "Media: OK" || echo "Media: FAIL"

# Verificar conectividade
echo "Testando conectividade:"
ping -c 1 nissei.com >/dev/null 2>&1 && echo "Nissei.com: OK" || echo "Nissei.com: FAIL"

# Aguardar banco de dados se necessário
if [ "$DATABASE_HOST" ]; then
    echo "Aguardando banco de dados..."
    while ! nc -z $DATABASE_HOST ${DATABASE_PORT:-5432}; do
        sleep 1
    done
    echo "Banco de dados disponível"
fi

# Executar migrações Django
echo "Executando migrações Django..."
python3 manage.py migrate --noinput || echo "WARNING: Falha nas migrações"

# Coletar arquivos estáticos
echo "Coletando arquivos estáticos..."
python3 manage.py collectstatic --noinput --clear || echo "WARNING: Falha nos arquivos estáticos"

echo "=== INICIANDO SERVIDOR ==="

if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput \
      --username "$DJANGO_SUPERUSER_USERNAME" \
      --email "$DJANGO_SUPERUSER_EMAIL" || true
fi

exec "$@"
