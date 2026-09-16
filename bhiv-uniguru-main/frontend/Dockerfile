# Stage 1: Build the React application
FROM node:20-alpine AS build

WORKDIR /app

# Declare build-time env vars so Vite can bake them into the bundle
ARG VITE_API_BASE_URL
ARG VITE_BACKEND_URL_V1
ARG VITE_APP__BACKEND_GOOGLE_OAUTH_URL
ARG VITE_GOOGLE_CLIENT_ID

ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_BACKEND_URL_V1=$VITE_BACKEND_URL_V1
ENV VITE_APP__BACKEND_GOOGLE_OAUTH_URL=$VITE_APP__BACKEND_GOOGLE_OAUTH_URL
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve the static files using Node serve
FROM node:20-alpine

WORKDIR /app

RUN npm install -g serve && \
    apk add --no-cache curl

COPY --from=build /app/dist /app/dist

EXPOSE 3000

CMD ["serve", "-s", "dist", "-l", "3000"]
