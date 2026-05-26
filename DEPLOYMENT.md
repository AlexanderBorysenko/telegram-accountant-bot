# Accounter Telegram Bot — Deployment Guide

## Prerequisites

- Ubuntu 22.04+ with Docker and Docker Compose installed
- CloudPanel installed and configured
- A domain name pointed to your server's IP
- Telegram Bot token (from @BotFather)
- Anthropic API key

## 1. Install Docker (if not installed)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

## 2. Clone and Configure

```bash
cd /home/your-user/htdocs
git clone <your-repo-url> buhalter
cd buhalter

cp .env.example .env
nano .env
# Fill in:
#   TELEGRAM_BOT_TOKEN=your-token-from-botfather
#   ANTHROPIC_API_KEY=your-anthropic-key
#   MONGODB_URI=mongodb://mongo:27017
#   MONGODB_DB_NAME=buhalter
```

## 3. Start the Bot

```bash
bash scripts/start.sh
```

Verify it's running:

```bash
docker compose logs -f bot
```

You should see "Starting Accounter Bot" and "Database initialized". Test by sending `/accounter test` to your bot in Telegram.

## 4. CloudPanel Reverse Proxy Setup

> **Note:** The bot uses Telegram long-polling and does NOT need a public port or reverse proxy to function. This section is only needed if you want to expose a health-check endpoint or add webhook support later.

### If you need a domain for future webhook support:

1. **Create a new site in CloudPanel:**
   - Go to CloudPanel → Sites → Add Site
   - Choose "Node.js" or "Reverse Proxy" application type
   - Set domain name (e.g., `bot.yourdomain.com`)

2. **Configure reverse proxy in Vhost:**
   - Go to the site → Vhost tab
   - Replace the Nginx config with:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name bot.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name bot.yourdomain.com;

    ssl_certificate /etc/nginx/ssl-certificates/bot.yourdomain.com.crt;
    ssl_certificate_key /etc/nginx/ssl-certificates/bot.yourdomain.com.key;

    location / {
        proxy_pass http://127.0.0.1:8443;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. **Issue SSL certificate:**
   - Go to the site → SSL/TLS tab
   - Click "New Let's Encrypt Certificate"
   - Enable auto-renewal

### Current setup (long-polling, no proxy needed):

The bot runs as a Docker container and communicates with Telegram's servers directly. No incoming connections are needed, so no reverse proxy or open ports are required. Just make sure the server has outbound HTTPS access.

## 5. Updates

To deploy new changes:

```bash
cd /home/your-user/htdocs/buhalter
bash scripts/update.sh
```

This pulls the latest code, rebuilds the Docker image, and restarts the container.

## 6. Monitoring

```bash
# View bot logs
docker compose logs -f bot

# View MongoDB logs
docker compose logs -f mongo

# Check container status
docker compose ps
```

## 7. Backup MongoDB Data

```bash
# Dump the database
docker compose exec mongo mongodump --db buhalter --out /data/backup

# Copy backup from container
docker compose cp mongo:/data/backup ./backup
```
