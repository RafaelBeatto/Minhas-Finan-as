# Imagem do Finan para a nuvem: compila o front-end e roda o servidor Python.
# Variáveis esperadas no serviço: FINAN_TOKEN (obrigatória), PLUGGY_CLIENT_ID,
# PLUGGY_CLIENT_SECRET, PLUGGY_ITEM_ID. Dados persistentes ficam em /data.

FROM node:24-slim AS front
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM python:3.13-slim
WORKDIR /app
COPY finan-servidor/requirements.txt finan-servidor/requirements.txt
RUN pip install --no-cache-dir -r finan-servidor/requirements.txt
COPY finan-servidor finan-servidor
COPY --from=front /src/dist dist

ENV FINAN_HOST=0.0.0.0 FINAN_DADOS=/data PYTHONUNBUFFERED=1
VOLUME ["/data"]
CMD ["python", "finan-servidor/servidor.py", "--sem-navegador"]
