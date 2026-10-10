
FROM node:22-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN python3 -m pip install --break-system-packages -r requirements.txt

ENV NODE_ENV=production

CMD ["npm", "start"]


