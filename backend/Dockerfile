# Imagem base
FROM python:3.11-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Diretório de trabalho
WORKDIR /app

# Instala netcat para o entrypoint.sh poder verificar a conexão com o banco de dados
# As flags -y e --no-install-recommends são para instalação não interativa e minimalista
RUN apt-get update && apt-get install -y netcat-traditional --no-install-recommends && rm -rf /var/lib/apt/lists/*

# Instala dependências
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copia o resto dos arquivos do projeto
COPY . .

# Copia e torna executável o script de entrada
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expondo a porta
EXPOSE 8000

# Comando padrão. O entrypoint será chamado pelo docker-compose.
# CMD ["daphne", "app.asgi:application", "-b", "0.0.0.0", "-p", "8000"]
