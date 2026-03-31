# syntax=docker/dockerfile:1

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY . .
ARG PUBLIC_API_BASE_URL=http://localhost:8000
ENV PUBLIC_API_BASE_URL=${PUBLIC_API_BASE_URL}
RUN npx svelte-kit sync && npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
