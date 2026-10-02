# UniGuru Frontend Deployment Guide

## 🚀 Fixing CORS Issues

The CORS errors you're experiencing happen because your deployed frontend is trying to connect to `localhost:8000`, which doesn't exist in the production environment.

## ✅ Solution: Environment-Based Configuration

### 1. Environment Variables Setup

The frontend now uses environment variables to determine the API endpoint:

- **Local Development**: Uses `http://localhost:8000`
- **Production**: Uses your deployed backend URL

### 2. Environment Files

- `.env.local` - Local development settings
- `.env.production` - Production settings
- `.env.example` - Template for environment variables

### 3. Deployment Steps

#### For Vercel Deployment:

1. **Deploy your backend first** to a service like:
   - Railway
   - Render
   - Heroku
   - DigitalOcean App Platform
   - AWS/GCP/Azure

2. **Update the production environment variable**:
   ```bash
   # In .env.production
   VITE_API_BASE_URL=https://your-backend-domain.com
   ```

3. **Set environment variables in Vercel**:
   - Go to your Vercel project dashboard
   - Navigate to Settings → Environment Variables
   - Add: `VITE_API_BASE_URL` = `https://your-backend-domain.com`

4. **Redeploy your frontend** on Vercel

### 4. Backend Deployment Requirements

Your backend needs to be deployed and accessible from the internet. The current CORS configuration already includes `https://uni-guru.vercel.app`.

### 5. Testing

After deployment:
1. Check browser console for API requests
2. Verify the API base URL is correct
3. Test authentication and other API calls

## 🔧 Quick Fix for Testing

If you need a quick test, you can temporarily:

1. Deploy your backend to a free service like Railway or Render
2. Update the environment variable in Vercel
3. Redeploy the frontend

## 📝 Notes

- Never commit `.env.local` or `.env.production` with real credentials
- The frontend will automatically use the correct API URL based on the environment
- CORS is already configured on the backend for your Vercel domain
