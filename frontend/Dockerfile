# ---- Build stage: compile the React app ----
FROM node:22-alpine AS build
WORKDIR /app
 
COPY package.json package-lock.json ./
RUN npm ci
 
COPY . .
# Empty by default: the browser calls /api on the same origin and nginx proxies it.
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build
 
# ---- Serve stage: static files + proxy to the backend ----
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80