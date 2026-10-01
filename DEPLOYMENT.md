# ShreeRide VFX - Render Deployment Guide

## Overview

This guide explains how to deploy the ShreeRide VFX Flask application to Render.com.

## Prerequisites

1. A Render.com account
2. A GitHub/GitLab repository with this code
3. A Render account with access to managed PostgreSQL; the Blueprint provisions the database.

## Optional Legacy: Deploy with External MySQL

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

| Key                 | Value                                          |
| ------------------- | ---------------------------------------------- |
| FLASK_ENV           | production                                     |
| SECRET_KEY          | (Click Generate for a secure random value)     |
| MYSQL_HOST          | Your MySQL host (e.g., aws.connect.psdb.cloud) |
| MYSQL_USER          | Your MySQL username                            |
| MYSQL_PASSWORD      | Your MySQL password                            |
| MYSQL_DATABASE      | ridex_db                                       |
| GOOGLE_MAPS_API_KEY | Your Google Maps API key (optional)            |

### Step 5: Deploy

Click Create Web Service and wait for deployment to complete.

### Step 6: Initialize Database

After deployment, run the database initialization. You can do this via Render Shell:

1. Go to your service → Shell
2. Run the database.sql script in your MySQL client

---

## Deploy with Render PostgreSQL

The root `render.yaml` is the PostgreSQL Blueprint. Connect the repository in Render and create a Blueprint Instance using that file. It provisions PostgreSQL, installs `requirements.txt`, generates `SECRET_KEY`, sets `DATABASE_URL`, runs `init_postgres.py`, then starts `app.py` with Gunicorn.

The initializer loads `database_postgres.sql` only for an empty database, so later deploys preserve existing data. Demo admin credentials are `admin` / `admin123`; demo drivers use their phone number with password `driver123`. Change demo credentials before exposing the app publicly.

For the preserved MySQL setup, use `render-mysql.yaml` and provide the external MySQL connection variables instead. `database.sql` remains the MySQL schema.

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

`database_postgres.sql` initializes the Render PostgreSQL schema. `database.sql` remains for MySQL. For ongoing schema changes, use a migration tool such as Flask-Migrate.

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
   - Verify Render created the PostgreSQL database and populated `DATABASE_URL`
   - For the optional MySQL deployment, verify the host, user, password, and database name

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
   - Confirm `psycopg2-binary` is listed in `requirements.txt` and the Render build completed successfully

---

## File Structure for Deployment

```
ShreeRide_VFX/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker configuration
├── .dockerignore          # Docker ignore rules
├── render.yaml            # PostgreSQL Render Blueprint
├── render-mysql.yaml      # Optional external-MySQL Blueprint
├── database_postgres.sql  # Render PostgreSQL schema
├── database.sql           # Preserved MySQL schema
├── init_postgres.py       # PostgreSQL bootstrap command
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
