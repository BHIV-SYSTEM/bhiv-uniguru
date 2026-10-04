# ---------- Build stage ----------
    FROM node:20-alpine AS builder

    WORKDIR /app
    
    COPY package*.json ./
    RUN npm ci
    
    COPY . .
    
    ARG VITE_API_BASE_URL
    ARG VITE_API_URL
    ARG VITE_BACKEND_URL_V1
    ARG VITE_SANSKRIT_API_URL
    ARG VITE_APP__BACKEND_GOOGLE_OAUTH_URL
    ARG VITE_GOOGLE_CLIENT_ID
    
    ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
    ENV VITE_API_URL=$VITE_API_URL
    ENV VITE_BACKEND_URL_V1=$VITE_BACKEND_URL_V1
    ENV VITE_SANSKRIT_API_URL=$VITE_SANSKRIT_API_URL
    ENV VITE_APP__BACKEND_GOOGLE_OAUTH_URL=$VITE_APP__BACKEND_GOOGLE_OAUTH_URL
    ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
    
    RUN npm run build
    
    
    # ---------- Runtime stage ----------
    FROM nginx:1.27-alpine
    
    COPY --from=builder /app/dist /usr/share/nginx/html
    
    COPY nginx.conf /etc/nginx/conf.d/default.conf
    
    EXPOSE 80
    
    CMD ["nginx", "-g", "daemon off;"]