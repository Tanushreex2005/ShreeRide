# ShreeRide VFX - Render Deployment Guide

## Overview
This guide explains how to deploy the ShreeRide VFX Flask application to Render.com.

## Prerequisites
1. A Render.com account
2. A GitHub/GitLab repository with this code
3. A MySQL database (Render does not provide managed MySQL)

## Option 1: Deploy with External MySQL (Recommended)

### Step 1: Set up a MySQL Database
Choose one of these MySQL providers:
- **PlanetScale** (Free tier available) - https://planetscale.com
- **Railway** - https://railway.app
- **Aiven** - https://aiven.io
- **Supabase** (MySQL via PostgreSQL wrapper)
- **Your own VPS MySQL**

Create a database named ridex_db and note the connection details.

### Step 2: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit for Render deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 3: Create Render Web Service
1. Go to https://dashboard.render.com
2. Click New → Web Service
3. Connect your GitHub repository
4. Configure:
   - Name: shreeride-vfx
   - Runtime: Docker
   - Dockerfile Path: ./Dockerfile
   - Plan: Starter (or higher)
   - Health Check Path: /

### Step 4: Set Environment Variables
In Render dashboard → Environment, add these variables:

| Key | Value |
|-----|-------|
| FLASK_ENV | production |
| SECRET_KEY | (Click Generate for a secure random value) |
| MYSQL_HOST | Your MySQL host (e.g., aws.connect.psdb.cloud) |
| MYSQL_USER | Your MySQL username |
| MYSQL_PASSWORD | Your MySQL password |
| MYSQL_DATABASE | ridex_db |
| GOOGLE_MAPS_API_KEY | Your Google Maps API key (optional) |

### Step 5: Deploy
Click Create Web Service and wait for deployment to complete.

### Step 6: Initialize Database
After deployment, run the database initialization. You can do this via Render Shell:
1. Go to your service → Shell
2. Run the database.sql script in your MySQL client

---

## Option 2: Deploy with Render PostgreSQL (Requires Code Changes)

Render provides managed PostgreSQL. To use this:

1. In render.yaml, uncomment the pserv database section
2. Remove the MYSQL_* environment variables
3. The app will automatically use DATABASE_URL for PostgreSQL

Note: The current SQL queries use MySQL-specific syntax:
- TIMESTAMP(date, time) → Use date + time in PostgreSQL
- DATE_ADD(ts, INTERVAL n DAY) → Use ts + INTERVAL n days
- AUTO_INCREMENT → Use SERIAL or GENERATED ALWAYS AS IDENTITY
- LAST_INSERT_ID() → Use RETURNING id

You would need to modify the queries in app.py to be PostgreSQL-compatible.

---

## Docker Deployment (Alternative)

If you prefer not to use render.yaml, you can deploy manually:

1. Build the Docker image locally:
   ```bash
   docker build -t shreeride-vfx .
   ```

2. Test locally:
   ```bash
   docker run -p 5000:5000 --env-file .env shreeride-vfx
   ```

3. Push to a container registry (Docker Hub, GHCR, etc.) and deploy via Render's Container Registry option.

---

## Important Notes

### Security
- Never commit .env file to version control
- Use Render's Environment Variables for all secrets
- Generate a strong SECRET_KEY using: python -c "import secrets; print(secrets.token_urlsafe(32))"

### Database Migrations
The database.sql file contains the full schema. For production, consider using a migration tool like Flask-Migrate.

### Static Files
Static files are served by Flask in development. For production, consider using a CDN or nginx reverse proxy.

### Scaling
- The Dockerfile uses 2 gunicorn workers
- Adjust --workers in Dockerfile based on your plan's memory
- For higher traffic, upgrade to Render's Standard or Pro plans

### Monitoring
- Check Render's Logs tab for application logs
- Set up Health Checks for uptime monitoring
- Consider adding application performance monitoring (APM)

---

## Troubleshooting

### Common Issues

1. Database Connection Failed
   - Verify MySQL host, user, password, and database name
   - Check if MySQL allows connections from Render's IPs (0.0.0.0/0 for most providers)
   - Ensure SSL is configured correctly (some providers require SSL)

2. SECRET_KEY Error
   - Make sure SECRET_KEY is set in Render environment variables
   - Generate a new one if needed

3. Static Files Not Loading
   - Check static/ folder is included in Docker build
   - Verify FLASK_ENV=production is set

4. Port Binding Error
   - The app uses PORT environment variable (Render sets this automatically)
   - Dockerfile exposes port 5000

5. Module Not Found (psycopg2)
   - This is only needed for PostgreSQL deployment
   - For MySQL deployment, it's not required

---

## File Structure for Deployment
```
ShreeRide_VFX/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker configuration
├── .dockerignore          # Docker ignore rules
├── render.yaml            # Render service configuration
├── database.sql           # Database schema
├── .env.example           # Environment variable template
├── static/                # Static assets (CSS, JS, images)
└── templates/             # Jinja2 templates
```

---

## Support
For issues with this deployment, check:
1. Render logs: Dashboard → Your Service → Logs
2. Application errors: Check browser console and network tab
3. Database connectivity: Test with a MySQL client
