# Usar versão específica e estável
FROM selenium/standalone-chrome:4.15.0-20231129

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Instalar Python e dependências como root
USER root

# Instalar dependências em um único comando (otimizado)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    netcat-traditional \
    ca-certificates \
    curl \
    wget \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Criar diretório de trabalho e estrutura
WORKDIR /app

# Criar diretórios necessários com permissões corretas
RUN mkdir -p /app/media /app/static /app/logs && \
    chown -R seluser:seluser /app && \
    chmod -R 755 /app/media /app/static

# Atualizar pip
RUN python3 -m pip install --upgrade pip

# Copiar e instalar dependências Python
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copiar arquivos do projeto
COPY . .

# Configurar permissões finais
RUN chown -R seluser:seluser /app

# Copiar e configurar entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    chown seluser:seluser /entrypoint.sh

# Voltar para usuário não-root para segurança
USER seluser

# Expor porta
EXPOSE 8000

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]