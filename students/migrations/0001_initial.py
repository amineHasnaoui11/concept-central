import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('internal_code', models.CharField(help_text='Identifiant interne (jamais envoyé au LLM en clair avec le nom).', max_length=32, unique=True)),
                ('first_name', models.CharField(max_length=80)),
                ('last_name', models.CharField(max_length=80)),
                ('birth_year', models.PositiveSmallIntegerField()),
                ('level', models.CharField(choices=[('college', 'Collège'), ('lycee', 'Lycée')], max_length=10)),
                ('class_name', models.CharField(max_length=40, verbose_name='Classe')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('parent_full_name', models.CharField(blank=True, max_length=160, verbose_name='Nom du parent / tuteur')),
                ('parent_phone', models.CharField(blank=True, max_length=32, verbose_name='Téléphone parent')),
                ('parent_email', models.EmailField(blank=True, help_text="Utilisé pour le lien d'accès au portail famille.", max_length=254, verbose_name='Email parent')),
                ('parent_preferred_language', models.CharField(choices=[('fr', 'Français'), ('ar', 'العربية')], default='fr', max_length=2, verbose_name='Langue préférée')),
            ],
            options={
                'verbose_name': 'Élève',
                'verbose_name_plural': 'Élèves',
                'ordering': ['last_name', 'first_name'],
            },
        ),
        migrations.CreateModel(
            name='ParentConsent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('consent_type', models.CharField(choices=[('data', 'Traitement des données scolaires'), ('psych', 'Suivi psychologique'), ('portal', 'Accès portail famille'), ('llm', 'Analyse IA (anonymisée)')], max_length=10)),
                ('granted', models.BooleanField(default=False)),
                ('granted_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('granted_by', models.CharField(blank=True, help_text='Nom du parent / tuteur qui a accordé le consentement', max_length=160)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recorded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consents', to='students.student')),
            ],
            options={
                'verbose_name': 'Consentement parental',
                'verbose_name_plural': 'Consentements parentaux',
                'unique_together': {('student', 'consent_type')},
            },
        ),
    ]
