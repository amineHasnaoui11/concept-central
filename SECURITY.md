# 🔐 Politique de sécurité

## Modèle de menaces

Concept Central manipule des données sensibles sur des **mineurs** :
- Données scolaires (notes, absences, comportement)
- Évaluations psychologiques (stress, anxiété, isolement)
- Informations familiales

Les protections sont conçues pour résister à :

| Menace | Mitigation |
|--------|-----------|
| Accès non autorisé inter-rôles | Décorateurs `@role_required` + tests |
| Brute-force sur login | `django-axes` (5 essais → blocage 1h) |
| Vol de session | `SESSION_COOKIE_HTTPONLY`, `SAMESITE=Lax`, timeout 30 min |
| Énumération d'emails parents | Réponse identique succès/échec sur `/famille/` |
| Spam du portail famille | Rate limiting `5/h/IP` (django-ratelimit) |
| CSRF | Token Django sur tous les POST |
| Upload malveillant | Whitelist extensions + taille max 5 MB |
| Fuite vers LLM externe | Anonymisation systématique (pseudonyme `ELEVE-XXX`) |
| Violation de rôle silencieuse | Logging dans `AuditLog` |
| Mots de passe faibles | Validators Django activés (min 8 chars + checks) |

---

## Couches de sécurité

### 1. Authentification

- Modèle `User` personnalisé avec champ `role` (operator/supervisor/admin)
- `django-axes` bloque après 5 essais ratés
- Password reset par email avec token expirant
- Session timeout : 30 min d'inactivité → déconnexion auto (configurable)
- Cookies : `HttpOnly`, `Secure` (en prod), `SameSite=Lax`

### 2. Autorisation

Trois rôles strictement séparés :

```python
@role_required(Role.SUPERVISOR)  # Conseiller uniquement
def create_dossier(request, student_id):
    ...
```

Les permissions sont testées dans `accounts/tests.py`, `wellbeing/tests.py`, etc.

### 3. Audit trail

**Tout** événement sensible est loggé dans `AuditLog` :
- Tentatives d'accès refusées (rôle inadapté)
- Création d'alertes
- Ouvertures de dossiers psychologiques
- Imports CSV échoués
- Recommandations LLM générées
- Connexions au portail famille

### 4. Anonymisation LLM

Avant tout envoi à un LLM (Ollama/Anthropic/Groq), le profil de l'élève passe par `Student.anonymized_profile()` :

```python
{
    "pseudonym": "ELEVE-TN-2024-001",
    "age_range": "13 ans",
    "level": "Collège",
    "class_group": "3A",
}
```

Le nom réel n'est **jamais** transmis. Une `assert` dans `recommendations/services.py` vérifie qu'aucun nom n'est présent dans le payload.

### 5. Portail famille

- Pas de mot de passe → magic link à usage unique (15 min)
- Le parent voit son enfant uniquement si `parent_email` correspond
- **Aucune donnée clinique** brute n'est exposée (pas de scores, pas de notes psy)
- Rate limiting `5/h/IP` pour bloquer le scraping

### 6. Uploads

- Extensions autorisées : `.pdf`, `.png`, `.jpg`, `.jpeg`, `.docx`
- Taille max : 5 MB
- Stockage dans `/media/dossiers/<dossier_id>/` (accessible uniquement aux superviseurs)
- Validator `validate_upload_extension` sur le `FileField`

### 7. Conformité RGPD

- **Consentement** : `ParentConsent` modélise les 4 types (données scolaires, suivi psy, portail, IA)
- **Droit d'accès** : export JSON complet via `students/<id>/export/`
- **Rétention** : `PsychDossier.retention_until` calculé automatiquement (5 ans par défaut)
- **Archivage** : `python manage.py archive_expired_dossiers`
- **Traçabilité** : toute action loggée

---

## Configuration production

Variables à activer dans `.env` :

```bash
DEBUG=False
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
ALLOWED_HOSTS=votre-domaine.tn
CSRF_TRUSTED_ORIGINS=https://votre-domaine.tn
```

Et :
- Changer `SECRET_KEY` (générez via `python -c "import secrets; print(secrets.token_urlsafe(50))"`)
- Activer HTTPS au niveau du reverse proxy (Nginx)
- Configurer PostgreSQL au lieu de SQLite
- Mettre en place les sauvegardes chiffrées

---

## Signaler une vulnérabilité

Si vous découvrez une faille de sécurité :

1. **NE PAS** ouvrir d'issue publique
2. Contactez le mainteneur en privé
3. Décrivez l'attaque + l'impact + un PoC si possible
4. Une réponse sera apportée sous 7 jours

---

## Checklist pré-déploiement

- [ ] `SECRET_KEY` unique généré
- [ ] `DEBUG=False`
- [ ] HTTPS configuré (Let's Encrypt)
- [ ] Cookies sécurisés activés
- [ ] HSTS activé
- [ ] `ALLOWED_HOSTS` restreint
- [ ] PostgreSQL configuré (pas SQLite)
- [ ] Sauvegardes automatiques en place
- [ ] Email SMTP testé
- [ ] Tâches cron pour :
  - [ ] `archive_expired_dossiers` (mensuel)
  - [ ] `check_missed_sessions` (quotidien)
  - [ ] `send_weekly_report` (hebdomadaire)
- [ ] `python manage.py check --deploy` → 0 warning
- [ ] Tests verts : `make test`
- [ ] Logs centralisés (journald, ELK, etc.)
