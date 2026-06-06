# Concept Central

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-5.0+-darkgreen.svg)](https://www.djangoproject.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Plateforme Django de **détection précoce du décrochage scolaire** et de **suivi de la santé mentale** des élèves tunisiens (10–18 ans), reliant l'école, le conseiller psychologique et la famille.

---

## ✨ Fonctionnalités

- 🎯 **Moteur de risque automatique** : absences + baisse de notes + incidents comportementaux + note critique
- 🤖 **Recommandations IA** (Ollama local, Anthropic, Groq) avec données strictement anonymisées
- 📊 **Tableaux de bord** par rôle (enseignant / conseiller / direction / **élève**) avec graphiques Chart.js
- 👨‍👩‍👧 **Portail famille** sécurisé par lien magique à usage unique (15 min, rate-limited)
- 📋 **Dossiers psychologiques** avec timeline, séances, pièces jointes et politique de rétention
- 🎥 **Rendez-vous vidéo conseiller ↔ élève** (Jitsi Meet embarqué, token secret, fenêtre temporelle d'accès)
- 📧 **Notifications email** automatiques (alertes critiques, rappels, rapports hebdomadaires)
- 🔍 **Détection proactive** d'élèves à risque (analyse de tendances)
- 📜 **Conformité RGPD / Loi tunisienne 2004-63** : consentements parentaux, export de données, archivage
- 🌐 **Multilingue** : Français + Arabe (avec support RTL)
- 🔐 **Sécurité durcie** : brute-force protection, session timeout, rate limiting, headers HTTPS-ready

---

## 🚀 Démarrage rapide

### Option A — Docker (recommandé, cross-platform)

**Pré-requis** : [Docker](https://www.docker.com/) installé.

```bash
git clone <votre-repo> concept-central
cd concept-central
cp .env.example .env       # adaptez si besoin
docker compose up -d --build
docker compose exec web python manage.py seed_demo
```

Ouvrez **http://localhost:8000** 🎉

### Option B — Python local

**Pré-requis** : Python 3.12+, pip.

```bash
git clone <votre-repo> concept-central
cd concept-central

# 1. Environnement virtuel
python -m venv .venv

# Activation (Linux/macOS)
source .venv/bin/activate

# Activation (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activation (Windows CMD)
.venv\Scripts\activate.bat

# 2. Dépendances
pip install -r requirements.txt

# 3. Configuration
cp .env.example .env       # cp sous Linux/macOS, copy sous Windows

# 4. Base de données + données démo
python manage.py migrate
python manage.py seed_demo

# 5. Lancer
python manage.py runserver
```

Ouvrez **http://127.0.0.1:8000** 🎉

### Option C — Avec Make (Linux/macOS/WSL)

```bash
make setup       # tout en une commande
make run         # lance le serveur
make test        # lance les tests
make help        # voir toutes les commandes
```

---

## 👥 Comptes de démonstration

| Rôle | Identifiant | Mot de passe | Accès |
|------|-------------|--------------|-------|
| 🍎 Enseignant | `enseignant` | `demo1234` | Saisies hebdo, import CSV |
| 🧠 Conseiller | `conseiller` | `demo1234` | Alertes, dossiers, interventions, RDV |
| 🏛️ Direction | `direction` | `demo1234` | Seuils, tableaux de bord, conformité |
| 🎓 Élève | `eleve_tn_2024_001` | `eleve1234` | Réponse aux RDV, accès vidéo |

> Les comptes élèves sont créés par le conseiller depuis la fiche élève (bouton "🔑 Créer un compte élève"). Le mot de passe initial est affiché une seule fois.

---

## 📂 Structure du projet

```
concept-central/
├── accounts/             # Utilisateurs, rôles, auth, middleware session timeout
├── audit/                # Journal d'audit (toutes les actions sensibles)
├── compliance/           # Conformité RGPD (consentements, rétention, accès)
├── concept_central/      # Configuration Django (settings, urls, wsgi)
├── education/            # Moteur de risque, alertes, interventions, demandes
│   ├── models.py         # WeeklyEntry, SubjectGrade, DailyAttendance, Alert
│   ├── risk_engine.py    # Algorithme de calcul du score de risque
│   ├── signals.py        # Création automatique d'alertes
│   ├── analytics.py      # Détection proactive
│   ├── reports.py        # Rapports hebdomadaires
│   └── notifications.py  # Emails d'alerte
├── family/               # Portail famille (magic link, rate-limited)
├── notifications/        # Notifications in-app + email
├── recommendations/      # Recommandations LLM (Ollama/Anthropic)
├── students/             # Élèves + consentements parentaux + export RGPD
├── wellbeing/            # Dossiers psy, séances, pièces jointes, rétention
├── samples/              # Exemples CSV pour tester
├── scripts/              # Scripts cross-platform (Python pur)
├── static/css/           # Styles "Tunisian Citrus"
├── templates/            # Templates Django
├── locale/               # Traductions (FR + AR)
├── Dockerfile            # Image Docker production
├── docker-compose.yml    # Orchestration locale
├── Makefile              # Commandes communes
├── .env.example          # Variables d'environnement
└── requirements.txt
```

---

## 🎬 Scénarios de démonstration

### Scénario 1 — Alerte précoce de décrochage

1. Connectez-vous comme `enseignant`
2. **Saisie hebdo** → renseignez 4 absences, note 8/20 (vs 14 précédente), incident comportemental
3. Le moteur calcule un score ≥ 75 → alerte **critique** + suggestion dossier psych.
4. Connectez-vous comme `conseiller` → validez l'alerte, planifiez une intervention
5. Connectez-vous comme `direction` → résolvez l'alerte une fois traitée

### Scénario 2 — Import CSV (avec test d'échec)

1. Comme `enseignant`, **Import CSV** :
   - `samples/weekly_valid.csv` → ✅ succès
   - `samples/weekly_invalid.csv` → ❌ erreur claire + log dans `audit_log`

### Scénario 3 — Violation de rôle (audit trail)

1. Comme `enseignant`, naviguez sur la fiche d'un élève ayant un dossier
2. Tentez d'accéder au dossier psychologique → **403** + entrée dans `AuditLog` (`access_denied`)

### Scénario 4 — Portail famille

1. Allez sur http://localhost:8000/famille/
2. Saisissez `parent1@famille.tn` (créé par `seed_demo`)
3. Un lien magique s'affiche (en mode DEBUG) → cliquez
4. Vous voyez le suivi de votre enfant **sans** données cliniques sensibles
5. Testez le rate limiting : faites 6 demandes en moins d'une heure → 429

### Scénario 5 — Recommandation IA anonymisée

1. Sur n'importe quelle alerte → la recommandation est générée automatiquement
2. Le payload envoyé au LLM ne contient **jamais** le nom réel, seulement `ELEVE-TN-2024-001`
3. Si Ollama tourne en local sur `http://localhost:11434` → modèle Llama appelé
4. Sinon → mode fallback déterministe local

### Scénario 6 — RDV en ligne conseiller ↔ élève 🎥

1. **Conseiller** → fiche élève → "🔑 Créer un compte élève" → identifiants affichés une seule fois
2. **Conseiller** → dossier psychologique → "📅 Proposer un RDV en ligne" (date, durée, sujet)
3. L'élève reçoit notification + email → se connecte avec ses identifiants
4. **Élève** → dashboard → "Répondre" → Approuve ou refuse
5. Si approuvé → token secret généré, salon Jitsi créé
6. À l'heure prévue (±10 min) → bouton "🎥 Rejoindre" apparaît pour les 2 parties
7. Salon Jitsi privé (nom = token non devinable), pas de signup requis
8. Connexions tracées dans `AuditLog`

### Scénario 7 — Conformité RGPD

1. Comme `direction` → **Conformité** dans la barre
2. Visualisez consentements, dossiers en rétention, accès refusés
3. Sur une fiche élève → **Export RGPD (JSON)** : toutes les données structurées

---

## 🛠️ Commandes utiles

```bash
# Tests
python manage.py test                          # Tous les tests
python manage.py test accounts                 # Un module
python manage.py test --verbosity 2

# Tâches périodiques
python scripts/send_weekly_report.py           # Rapport hebdo manuel
python scripts/run_proactive_detection.py      # Détection proactive
python scripts/check_missed_sessions.py        # Vérifier séances manquées
python manage.py archive_expired_dossiers      # Archiver les dossiers expirés

# Admin
python manage.py createsuperuser
python manage.py reset_passwords               # Réinitialise les comptes démo
python manage.py seed_demo                     # Recharge les données démo

# Traductions
python manage.py makemessages -l ar
python manage.py compilemessages
```

---

## ⚙️ Configuration (`.env`)

Toutes les options sont dans `.env.example`. Variables clés :

| Variable | Description | Défaut |
|----------|-------------|--------|
| `SECRET_KEY` | Clé secrète Django (**à changer en prod**) | *à définir* |
| `DEBUG` | Mode debug | `True` |
| `DATABASE_URL` | URL de la base | `sqlite:///db.sqlite3` |
| `EMAIL_BACKEND` | Backend email | `console.EmailBackend` |
| `OLLAMA_URL` | URL Ollama local | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modèle Llama à utiliser | `llama3.2` |
| `SESSION_IDLE_TIMEOUT_MINUTES` | Déconnexion auto staff | `30` |
| `FAMILY_RATE_LIMIT` | Rate limit portail famille | `5/h` |
| `PSYCH_DOSSIER_RETENTION_YEARS` | Rétention dossiers psy | `5` |
| `AXES_FAILURE_LIMIT` | Brute-force après N essais | `5` |

---

## 🔐 Sécurité

Voir [`SECURITY.md`](SECURITY.md) pour les détails complets. En résumé :

- ✅ Authentification par rôles (3 rôles distincts)
- ✅ Brute-force protection (`django-axes`)
- ✅ Session timeout automatique
- ✅ Rate limiting sur endpoints sensibles
- ✅ Anonymisation systématique avant envoi LLM
- ✅ Audit trail complet (`AuditLog`)
- ✅ Validation stricte des uploads (extensions, taille)
- ✅ Headers HTTPS prêts pour la production
- ✅ Mots de passe avec validators Django par défaut
- ✅ Conformité RGPD (consentements, rétention, export)

---

## 🚢 Déploiement en production

Voir [`DEPLOYMENT.md`](DEPLOYMENT.md). Points clés :

1. Changer `SECRET_KEY`
2. Mettre `DEBUG=False`
3. Configurer `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS`
4. Activer `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`
5. Configurer PostgreSQL via `DATABASE_URL`
6. Configurer SMTP réel (Gmail App Password ou SendGrid)
7. Lancer derrière Nginx + Gunicorn (ou utiliser Docker)

---

## 🧪 Couverture des tests

```bash
make test-cov   # ou: coverage run --source='.' manage.py test && coverage report
```

| Module | Tests |
|--------|-------|
| `accounts` | Permissions rôles, login/logout, session timeout, brute-force, password reset |
| `students` | Modèles, formulaires (validation âge/code), consentements, export RGPD |
| `education` | Moteur de risque, import CSV, création auto d'alertes, permissions |
| `wellbeing` | Accès opérateur refusé, rétention auto, séances manquées, validation uploads |
| `family` | Magic link lifecycle, expiration, rate limiting |

---

## 🤝 Contribution

```bash
git checkout -b feature/ma-feature
# coder...
make format     # black + isort
make lint       # flake8
make test       # tests doivent passer
git commit -m "feat: ma feature"
git push origin feature/ma-feature
```

---

## 📜 Licence

MIT — voir [LICENSE](LICENSE).

---

## 🙏 Remerciements

Conçu pour répondre aux besoins du système éducatif tunisien (élèves 10–18 ans) avec un fort accent sur la confidentialité, le bien-être des mineurs, et la collaboration école ↔ famille.
