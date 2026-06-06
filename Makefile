# Concept Central - Cross-platform commands
# Usage: `make <commande>` (nécessite GNU Make ; sur Windows, installer via Chocolatey ou WSL)

.PHONY: help install setup run migrate seed test test-cov lint format clean docker-up docker-down docker-logs docker-shell weekly-report check-sessions proactive-detect translations

help:  ## Affiche cette aide
	@echo "Concept Central - Commandes disponibles :"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Installe les dépendances
	pip install -r requirements.txt

setup:  ## Configuration initiale (env + migrations + données démo)
	@if [ ! -f .env ]; then cp .env.example .env; echo ".env créé depuis .env.example"; fi
	python manage.py migrate
	python manage.py seed_demo

run:  ## Lance le serveur de développement
	python manage.py runserver

migrate:  ## Applique les migrations
	python manage.py makemigrations
	python manage.py migrate

seed:  ## Recharge les données de démonstration
	python manage.py seed_demo

test:  ## Lance la suite de tests
	python manage.py test --verbosity 2

test-cov:  ## Lance les tests avec couverture
	coverage run --source='.' manage.py test
	coverage report
	coverage html

lint:  ## Vérifie le code (flake8)
	flake8 . --exclude=.venv,migrations,__pycache__ --max-line-length=120

format:  ## Formate le code (black + isort)
	black . --exclude='/(\.venv|migrations)/'
	isort . --skip .venv --skip migrations

clean:  ## Nettoie les fichiers temporaires
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov .coverage .pytest_cache

# === Docker ===
docker-up:  ## Démarre les conteneurs
	docker compose up -d --build

docker-down:  ## Arrête les conteneurs
	docker compose down

docker-logs:  ## Affiche les logs
	docker compose logs -f web

docker-shell:  ## Ouvre un shell dans le conteneur
	docker compose exec web bash

docker-seed:  ## Charge les données démo dans Docker
	docker compose exec web python manage.py seed_demo

# === Tâches planifiées ===
weekly-report:  ## Envoie le rapport hebdomadaire
	python scripts/send_weekly_report.py

check-sessions:  ## Vérifie les séances manquées
	python manage.py check_missed_sessions

proactive-detect:  ## Détection proactive des élèves à risque
	python scripts/run_proactive_detection.py

# === i18n ===
translations:  ## Compile les fichiers de traduction
	python manage.py compilemessages

makemessages:  ## Extrait les chaînes à traduire
	python manage.py makemessages -l ar
	python manage.py makemessages -l fr
