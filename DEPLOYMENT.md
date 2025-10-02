# Railway Deployment Guide

This guide will help you deploy your Oxygen Concentrator monitoring application to Railway for under £5/month.

## Prerequisites

1. **GitHub Repository**: Push your code to GitHub
2. **Railway Account**: Sign up at [railway.app](https://railway.app)
3. **Domain (Optional)**: You can use Railway's provided domains for free

## Quick Deployment Steps

### 1. Create Railway Project

1. Go to [railway.app](https://railway.app) and login
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository

### 2. Configure Environment Variables

In your Railway dashboard, add these environment variables:

**For FastAPI Service:**
```
JWT_SECRET=your-super-secure-random-string-here
USERS={"admin": "your-admin-password", "user": "your-user-password"}
PORT=8000
```

**For Panel Service:**
```
FASTAPI_URL=https://your-fastapi-service.railway.app
PORT=5006
```

### 3. Add PostgreSQL Database

1. In Railway dashboard, click "New Service"
2. Select "PostgreSQL"
3. Railway will automatically set `DATABASE_URL` environment variable

### 4. Deploy Services

Railway will automatically detect your `Dockerfile` and deploy both services:

- **FastAPI Backend**: Serves the API on port 8000
- **Panel Dashboard**: Serves the web interface on port 5006

## Post-Deployment Setup

### 1. Update Dashboard URL

Once deployed, update the Panel service environment variable:
```
FASTAPI_URL=https://your-actual-fastapi-domain.railway.app
```

### 2. Custom Domain (Optional)

1. Go to your service settings
2. Click "Networking"
3. Add your custom domain
4. Update DNS records as instructed

### 3. Test Authentication

1. Visit your Panel dashboard URL
2. Login with credentials from `USERS` environment variable
3. Verify all API endpoints require authentication

## Cost Breakdown

- **Railway Hobby Plan**: £4/month
- **PostgreSQL Database**: Included
- **SSL Certificates**: Included
- **Custom Domains**: Included

**Total: £4/month** (well under your £5 budget!)

## Security Checklist

- [ ] Change default passwords in `USERS` environment variable
- [ ] Use a strong, random `JWT_SECRET`
- [ ] Enable Railway's built-in security features
- [ ] Consider adding rate limiting for production use

## Monitoring

Railway provides built-in monitoring:
- View logs in real-time
- Monitor resource usage
- Set up alerts for service health

## Troubleshooting

### Common Issues:

1. **Services won't start**: Check logs for dependency issues
2. **Database connection fails**: Verify `DATABASE_URL` is set automatically
3. **Authentication errors**: Ensure `JWT_SECRET` matches between services
4. **Dashboard can't reach API**: Update `FASTAPI_URL` with correct Railway domain

### Useful Commands:

```bash
# Check service logs
railway logs

# Connect to database
railway connect postgres

# Deploy specific service
railway up --service fastapi-backend
```

## File Structure

Your deployment includes these key files:

```
sensing/
├── railway.toml           # Railway configuration
├── .env.example          # Environment variables template
├── fastapi/
│   ├── Dockerfile        # FastAPI container config
│   ├── requirements.txt  # Python dependencies
│   └── app/             # FastAPI application
└── panel/
    ├── Dockerfile        # Panel container config
    ├── requirements.txt  # Python dependencies
    └── app/             # Panel dashboard
```

## Support

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: Community support
- **GitHub Issues**: For application-specific problems

Your oxygen concentrator monitoring system is now ready for production deployment! 🚀