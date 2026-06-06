import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('students', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('csv_import_failed', 'Échec import CSV'), ('access_denied', 'Accès refusé'), ('alert_created', 'Alerte créée'), ('intervention_planned', 'Intervention planifiée'), ('dossier_opened', 'Dossier psychologique ouvert'), ('session_missed', 'Séance manquée'), ('llm_recommendation', 'Recommandation LLM générée')], max_length=40)),
                ('message', models.TextField()),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('student', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='students.student')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': "Journal d'audit",
                'verbose_name_plural': "Journaux d'audit",
                'ordering': ['-created_at'],
            },
        ),
    ]
