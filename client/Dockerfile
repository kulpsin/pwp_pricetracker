# ---- Build stage ----
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY src src

ARG API_BASE_URL

# Replace the local API endpoint address
RUN sed -i "s|http://localhost:5000|${API_BASE_URL}|g" src/js/config.js

# Build: copy files to dist (no bundler needed for vanilla JS, just validate)
RUN cp -r src dist

# ---- Production stage ----
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
