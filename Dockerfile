FROM python:3.12-slim

# Empêche Python d'écrire les fichiers .pyc et active le buffering immédiat
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=concept_central.settings

# Dépendances système (gettext pour les traductions, libpq pour PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer les dépendances Python d'abord (cache Docker)
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier le code de l'application
COPY . /app/

# Créer un utilisateur non-root pour la sécurité
RUN useradd -m -u 1000 django && \
    chown -R django:django /app
USER django

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/accounts/login/').read()" || exit 1

# Migrations + collecte des assets statiques + serveur
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn concept_central.wsgi:application --bind 0.0.0.0:8000 --workers 3 --access-logfile -"]
