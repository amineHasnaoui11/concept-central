# 🚢 Guide de déploiement

Trois scénarios sont couverts : **local Docker**, **VPS Linux**, **plateforme PaaS**.

---

## 1️⃣ Déploiement Docker (local ou VPS)

C'est le plus simple. Fonctionne identiquement sur Windows, macOS, Linux.

### Pré-requis

- [Docker](https://www.docker.com/) ≥ 20.10
- [Docker Compose](https://docs.docker.com/compose/) (inclus dans Docker Desktop)

### Étapes

```bash
git clone <votre-repo> concept-central
cd concept-central

# Créer le .env
cp .env.example .env
# Éditer .env : SECRET_KEY, DEBUG=False (si prod), SMTP, etc.

# Lancer
docker compose up -d --build

# Initialiser
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demo  # optionnel
docker compose exec web python manage.py createsuperuser

# Voir les logs
docker compose logs -f web
```

L'application est disponible sur **http://localhost:8000**.

### Avec PostgreSQL (production)

Décommentez le service `db` dans `docker-compose.yml`, puis dans `.env` :

```bash
DATABASE_URL=postgres://django:changeme@db:5432/concept_central
```

### Mise à jour

```bash
git pull
docker compose up -d --build
docker compose exec web python manage.py migrate
```

---

## 2️⃣ Déploiement VPS Linux (Ubuntu 22.04)

### Préparation du serveur

```bash
# Mise à jour
sudo apt update && sudo apt upgrade -y

# Dépendances système
sudo apt install -y python3.12 python3.12-venv python3-pip \
    postgresql postgresql-contrib nginx git certbot python3-certbot-nginx

# Utilisateur dédié
sudo useradd -m -s /bin/bash django
sudo -u django bash
```

### Installation de l'application

```bash
# En tant qu'utilisateur `django`
cd ~
git clone <votre-repo> concept-central
cd concept-central
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration PostgreSQL

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE concept_central;
CREATE USER django WITH PASSWORD 'mot-de-passe-fort';
GRANT ALL PRIVILEGES ON DATABASE concept_central TO django;
\q
```

Dans `.env` :

```bash
DATABASE_URL=postgres://django:mot-de-passe-fort@localhost:5432/concept_central
SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
DEBUG=False
ALLOWED_HOSTS=votre-domaine.tn,www.votre-domaine.tn
CSRF_TRUSTED_ORIGINS=https://votre-domaine.tn
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
```

### Migrations + statics

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### Gunicorn comme service systemd

Créer `/etc/systemd/system/concept-central.service` :

```ini
[Unit]
Description=Concept Central Gunicorn
After=network.target postgresql.service

[Service]
User=django
Group=www-data
WorkingDirectory=/home/django/concept-central
Environment="PATH=/home/django/concept-central/.venv/bin"
ExecStart=/home/django/concept-central/.venv/bin/gunicorn \
          --workers 3 \
          --bind unix:/run/concept-central.sock \
          --access-logfile - \
          --error-logfile - \
          concept_central.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable concept-central
sudo systemctl start concept-central
sudo systemctl status concept-central
```

### Nginx en reverse proxy

Créer `/etc/nginx/sites-available/concept-central` :

```nginx
server {
    listen 80;
    server_name votre-domaine.tn www.votre-domaine.tn;

    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.tn www.votre-domaine.tn;

    # SSL (rempli par certbot)
    ssl_certificate /etc/letsencrypt/live/votre-domaine.tn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/votre-domaine.tn/privkey.pem;

    client_max_body_size 10M;

    location /static/ {
        alias /home/django/concept-central/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /home/django/concept-central/media/;
        # Restreindre l'accès aux fichiers sensibles (dossiers psy)
        internal;
    }

    location / {
        proxy_pass http://unix:/run/concept-central.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/concept-central /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### HTTPS avec Let's Encrypt

```bash
sudo certbot --nginx -d votre-domaine.tn -d www.votre-domaine.tn
```

### Tâches cron

```bash
crontab -u django -e
```

```cron
# Rapport hebdo (lundi 08h)
0 8 * * 1 cd /home/django/concept-central && .venv/bin/python scripts/send_weekly_report.py

# Détection proactive (vendredi 16h)
0 16 * * 5 cd /home/django/concept-central && .venv/bin/python scripts/run_proactive_detection.py

# Séances manquées (chaque jour 9h)
0 9 * * * cd /home/django/concept-central && .venv/bin/python scripts/check_missed_sessions.py

# Archivage rétention (1er du mois 3h)
0 3 1 * * cd /home/django/concept-central && .venv/bin/python manage.py archive_expired_dossiers
```

---

## 3️⃣ Déploiement PaaS (Railway, Render, Fly.io)

### Railway

1. Connecter votre repo Git
2. Railway détecte le `Dockerfile`
3. Ajouter PostgreSQL via "New → Database"
4. Configurer les variables d'environnement :
   - `SECRET_KEY` (auto-générée)
   - `DATABASE_URL` (auto par Railway)
   - `ALLOWED_HOSTS=*.railway.app`
   - `DEBUG=False`
5. Déployer

### Render

1. New → Web Service → connecter le repo
2. Build : `pip install -r requirements.txt`
3. Start : `gunicorn concept_central.wsgi --bind 0.0.0.0:$PORT`
4. Ajouter PostgreSQL
5. Configurer les variables d'env

### Fly.io

```bash
fly launch
fly secrets set SECRET_KEY=... DATABASE_URL=...
fly deploy
```

---

## Sauvegardes

### PostgreSQL

```bash
# Sauvegarde quotidienne (cron)
pg_dump -U django concept_central | gzip > /backup/db-$(date +\%Y\%m\%d).sql.gz

# Restauration
gunzip -c db-20250115.sql.gz | psql -U django concept_central
```

### Media files (pièces jointes)

```bash
# rsync vers serveur distant chiffré
rsync -avz --delete /home/django/concept-central/media/ backup-server:/backups/concept-central/media/
```

---

## Monitoring

### Healthcheck

L'application expose `/accounts/login/` qui doit toujours répondre 200. Configurez votre monitoring (UptimeRobot, healthchecks.io) pour vérifier cet endpoint.

### Logs

```bash
# Application
sudo journalctl -u concept-central -f

# Nginx
sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log

# Audit trail Django (depuis l'app)
python manage.py shell
>>> from audit.models import AuditLog
>>> AuditLog.objects.filter(event_type="access_denied")[:10]
```

---

## Checklist post-déploiement

- [ ] `python manage.py check --deploy` → 0 warning
- [ ] HTTPS actif (test sur https://www.ssllabs.com/ssltest/)
- [ ] Email SMTP testé (`python manage.py shell` → `send_mail(...)`)
- [ ] Tâches cron actives (`crontab -l`)
- [ ] Sauvegardes testées (restauration sur un autre serveur)
- [ ] Comptes démo désactivés ou supprimés en production
- [ ] Superuser créé avec mot de passe fort
- [ ] Logs centralisés
