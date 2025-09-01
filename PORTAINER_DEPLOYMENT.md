# IsoCrop Portainer Deployment Guide

This guide walks you through deploying the IsoCrop application to production using Portainer.

## Prerequisites

1. **Portainer** installed and running on your server
2. **Docker** and **Docker Compose** installed on the server
3. **Git** installed (if pulling from repository)
4. Domain name configured (optional, for production)
5. SSL certificates (optional, for HTTPS)

## Deployment Methods

### Method 1: Using Portainer Stacks (Recommended)

#### Step 1: Prepare Your Environment

1. Log into your Portainer instance
2. Navigate to **Environments** → Select your environment
3. Go to **Stacks** → **Add Stack**

#### Step 2: Configure the Stack

**Stack Name:** `isocrop-production`

**Build Method Options:**

##### Option A: Git Repository (Recommended for CI/CD)

1. Select **Git Repository**
2. Repository URL: `https://github.com/yourusername/isocrop.git`
3. Reference: `main` (or your production branch)
4. Compose path: `docker-compose.prod.yml`

##### Option B: Web Editor (Quick Deploy)

1. Select **Web editor**
2. Copy and paste the contents of `docker-compose.prod.yml`

##### Option C: Upload

1. Select **Upload**
2. Upload your `docker-compose.prod.yml` file

#### Step 3: Configure Environment Variables

In the **Environment variables** section, add:

```
# Core Settings
ENV=production
NODE_ENV=production

# Ports (adjust if needed)
BACKEND_PORT=8000
FRONTEND_PORT=3000
NGINX_PORT=80
NGINX_SSL_PORT=443

# URLs (update with your domain)
BACKEND_URL=http://your-server-ip:8000
FRONTEND_URL=http://your-server-ip:3000

# Security (IMPORTANT: Change these!)
SECRET_KEY=generate-a-secure-random-key-here
JWT_SECRET=generate-another-secure-random-key-here

# CORS
ALLOWED_ORIGINS=http://your-server-ip:3000,https://yourdomain.com

# File Settings
MAX_UPLOAD_SIZE=50MB

# Logging
LOG_LEVEL=info

# Performance
WORKERS=4
MAX_CONCURRENT_CROPS=5

# Optional: API Keys
# TINIFY_API_KEY=your-tinypng-api-key
```

#### Step 4: Deploy the Stack

1. Click **Deploy the stack**
2. Wait for deployment to complete
3. Check container logs for any errors

### Method 2: Manual Docker Build and Import

#### Step 1: Build the Docker Image

On your local machine or build server:

```bash
# Clone the repository
git clone https://github.com/yourusername/isocrop.git
cd isocrop

# Create .env file from template
cp .env.production .env
# Edit .env with your production values

# Build the Docker image
docker build -t isocrop:latest .

# Save the image to a file
docker save isocrop:latest | gzip > isocrop-latest.tar.gz
```

#### Step 2: Import to Portainer

1. Transfer `isocrop-latest.tar.gz` to your server
2. In Portainer, go to **Images** → **Import**
3. Upload the tar.gz file or import via URL
4. Image will appear in your images list

#### Step 3: Create Container from Image

1. Go to **Containers** → **Add container**
2. Name: `isocrop-production`
3. Image: `isocrop:latest`
4. Port mapping:
   - 8000:8000 (Backend API)
   - 3000:3000 (Frontend)
5. Volumes:
   - `/var/isocrop/uploads:/app/uploads`
   - `/var/isocrop/exports:/app/exports`
   - `/var/isocrop/logs:/app/logs`
6. Environment variables: Add all from Step 3 above
7. Restart policy: `Unless stopped`
8. Deploy the container

### Method 3: Using Docker Compose with Portainer Agent

#### Step 1: Prepare the Server

SSH into your server and create the project directory:

```bash
# Create project directory
sudo mkdir -p /opt/isocrop
cd /opt/isocrop

# Clone repository or copy files
git clone https://github.com/yourusername/isocrop.git .
# OR copy files via SCP/SFTP

# Create .env file
cp .env.production .env
sudo nano .env  # Edit with your values

# Create data directories
sudo mkdir -p /var/isocrop/{uploads,exports,logs,nginx-cache}
sudo chown -R 1000:1000 /var/isocrop  # Adjust UID:GID as needed
```

#### Step 2: Deploy via Portainer

1. In Portainer, go to your environment
2. Navigate to **Stacks** → **Add stack**
3. Name: `isocrop-production`
4. Build method: **Custom template**
5. Template: Select or create a custom template pointing to `/opt/isocrop/docker-compose.prod.yml`
6. Deploy the stack

## Post-Deployment Configuration

### 1. Verify Deployment

Check all containers are running:

```bash
# Via Portainer UI
Containers → Check status (should show "running" for all)

# Via SSH
docker ps | grep isocrop
```

### 2. Test the Application

```bash
# Test backend health
curl http://your-server-ip:8000/api/health

# Test frontend
curl http://your-server-ip:3000

# Test via browser
http://your-server-ip:3000
```

### 3. Configure Nginx Reverse Proxy (Optional but Recommended)

If using Portainer with Nginx Proxy Manager:

1. Go to Nginx Proxy Manager
2. Add Proxy Host:
   - Domain: `yourdomain.com`
   - Forward Hostname: `isocrop-production` or container IP
   - Forward Port: `3000`
   - Enable WebSockets
   - SSL: Request Let's Encrypt certificate

### 4. Setup Monitoring

In Portainer:

1. Navigate to container details
2. Enable **Resource limits** if needed
3. Set up **Health checks**
4. Configure **Alerts** for container status

### 5. Configure Backups

Create backup strategy for volumes:

```bash
# Backup script example
#!/bin/bash
BACKUP_DIR="/backup/isocrop/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup volumes
docker run --rm \
  -v isocrop_uploads:/data/uploads \
  -v isocrop_exports:/data/exports \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/isocrop-data.tar.gz /data

# Backup database if applicable
# Add database backup commands here
```

## Environment-Specific Configurations

### Development in Portainer

For development/staging:

```yaml
# docker-compose.dev.yml adjustments
services:
  isocrop:
    environment:
      - ENV=development
      - DEBUG=true
      - LOG_LEVEL=debug
```

### Production Optimizations

1. **Enable Redis** for caching:
```yaml
services:
  redis:
    image: redis:alpine
    restart: unless-stopped
    volumes:
      - redis-data:/data
```

2. **Add Database** for persistent storage:
```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: isocrop
      POSTGRES_USER: isocrop
      POSTGRES_PASSWORD: secure-password
    volumes:
      - postgres-data:/var/lib/postgresql/data
```

## Troubleshooting

### Common Issues

1. **Container fails to start**
   - Check logs: Containers → Select container → Logs
   - Verify environment variables
   - Check port conflicts

2. **Cannot access application**
   - Verify firewall rules
   - Check Docker network configuration
   - Ensure ports are properly mapped

3. **File upload issues**
   - Check volume permissions
   - Verify MAX_UPLOAD_SIZE setting
   - Check disk space

4. **Performance issues**
   - Adjust WORKERS count
   - Configure resource limits
   - Enable caching with Redis

### Viewing Logs

In Portainer:
1. Go to **Containers**
2. Click on container name
3. Click **Logs**
4. Use filters: `stderr`, `stdout`, timestamps

Via SSH:
```bash
docker logs isocrop-production --tail 100 --follow
```

## Security Considerations

1. **Change default secrets** in environment variables
2. **Use HTTPS** in production (Let's Encrypt via Nginx)
3. **Limit exposed ports** using firewall rules
4. **Regular updates**: Keep Docker images updated
5. **Volume permissions**: Ensure proper ownership
6. **Network isolation**: Use custom Docker networks
7. **Resource limits**: Set CPU and memory limits

## Scaling

For high-traffic scenarios:

1. **Horizontal scaling**: Deploy multiple instances behind load balancer
2. **CDN**: Use CloudFlare or similar for static assets
3. **Object storage**: Move to S3-compatible storage for files
4. **Database**: Migrate to managed database service
5. **Queue system**: Add Celery + Redis for background tasks

## Maintenance

### Regular Tasks

1. **Monitor disk usage**: Check volume sizes
2. **Log rotation**: Configure log rotation for containers
3. **Update images**: Pull latest security updates
4. **Backup verification**: Test restore procedures
5. **Performance monitoring**: Track response times

### Updating the Application

Via Portainer Stack:
1. Go to **Stacks** → Select `isocrop-production`
2. Click **Editor**
3. Update image tag or configuration
4. Click **Update the stack**

Via Git (if using Git deployment):
1. Push updates to repository
2. In Portainer: Stacks → Pull and redeploy

## Support

For issues specific to:
- **IsoCrop application**: Check application logs and documentation
- **Portainer**: Consult Portainer documentation
- **Docker**: Refer to Docker documentation
- **Deployment**: Review this guide and environment variables

## Quick Commands Reference

```bash
# View running containers
docker ps | grep isocrop

# View logs
docker logs isocrop-production --tail 50

# Enter container shell
docker exec -it isocrop-production /bin/sh

# Restart container
docker restart isocrop-production

# Check disk usage
docker system df
du -sh /var/isocrop/*

# Backup volumes
docker run --rm -v isocrop_uploads:/data -v $(pwd):/backup alpine tar czf /backup/uploads-backup.tar.gz /data
```