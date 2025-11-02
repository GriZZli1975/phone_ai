# Build stage
FROM node:18-alpine as build

WORKDIR /app

# Копирование package files
COPY package*.json ./

# Установка зависимостей
RUN npm ci

# Копирование исходников
COPY . .

# Build
RUN npm run build

# Production stage
FROM nginx:alpine

# Копирование build
COPY --from=build /app/dist /usr/share/nginx/html

# Nginx конфигурация
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

