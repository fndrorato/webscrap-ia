# Usar imagem Python base
FROM python:3.11-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências como root
USER root

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    netcat-openbsd \
    xvfb \
    ca-certificates \
    --no-install-recommends

# Instalar Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

# Limpar cache
RUN apt-get autoremove -y && apt-get clean

# Criar usuário app
RUN groupadd -r app --gid=1000 && \
    useradd -r -g app --uid=1000 --home-dir=/app --shell=/bin/bash app

# Configurar diretório de trabalho
WORKDIR /app

# Criar estrutura de diretórios
RUN mkdir -p /app/media /app/static /app/staticfiles /app/logs && \
    chown -R app:app /app && \
    chmod -R 755 /app

# Atualizar pip
RUN python -m pip install --upgrade pip

# Copiar requirements primeiro
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Instalar webdriver-manager (gerencia ChromeDriver automaticamente)
RUN pip install webdriver-manager

# Copiar código do projeto
COPY . /app/

# Ajustar permissões
RUN chown -R app:app /app && \
    chmod -R 755 /app

# Copiar entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    chown app:app /entrypoint.sh

# Trocar para usuário não-root
USER app

# Expor porta
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]