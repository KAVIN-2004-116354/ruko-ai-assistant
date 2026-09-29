FROM node:18-bookworm
RUN apt-get update && apt-get install -y chromium
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
CMD ["node", "server.js"]
