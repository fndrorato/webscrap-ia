FROM node:18-alpine

WORKDIR /app

COPY package.json ./
COPY package-lock.json ./  

RUN npm install

# Corrige qualquer binário incompatível (precaução extra)
RUN npm rebuild esbuild

COPY . .

# Copia o .env.production para o momento do build
COPY .env.production .env

RUN npm run build

RUN npm install -g serve

EXPOSE 3000

CMD [ "serve", "-s", "dist" ]
