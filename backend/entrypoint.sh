#!/bin/sh
echo "Aguardando o banco de dados em $DB_HOST:$DB_PORT..."
MAX_ATTEMPTS=30
ATTEMPTS_LEFT=$MAX_ATTEMPTS

while ! nc -z $DB_HOST $DB_PORT; do
  sleep 2
  ATTEMPTS_LEFT=$((ATTEMPTS_LEFT-1))
  if [ $ATTEMPTS_LEFT -eq 0 ]; then
    echo "Erro: Banco de dados não respondeu após $MAX_ATTEMPTS tentativas."
    exit 1
  fi
done

echo "Banco de dados está disponível!"

echo "Executando migrations..."
python manage.py migrate --noinput

echo "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput
if [ $? -ne 0 ]; then
  echo "Erro no collectstatic. Encerrando."
  exit 1
fi

if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput \
      --username "$DJANGO_SUPERUSER_USERNAME" \
      --email "$DJANGO_SUPERUSER_EMAIL" || true
fi

exec "$@"
