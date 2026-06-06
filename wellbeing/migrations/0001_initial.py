import django.db.models.deletion
import wellbeing.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('education', '0001_initial'),
        ('students', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PsychDossier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('open', 'Ouvert'), ('closed', 'Clôturé'), ('archived', 'Archivé')], default='open', max_length=10)),
                ('summary', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('retention_until', models.DateField(blank=True, help_text="Date après laquelle le dossier doit être archivé/anonymisé", null=True)),
                ('opened_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='opened_dossiers', to=settings.AUTH_USER_MODEL)),
                ('opened_from_alert', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='psych_dossiers', to='education.alert')),
                ('student', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='psych_dossier', to='students.student')),
            ],
            options={
                'verbose_name': 'Dossier psychologique',
                'verbose_name_plural': 'Dossiers psychologiques',
            },
        ),
        migrations.CreateModel(
            name='FollowUpSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_at', models.DateTimeField()),
                ('status', models.CharField(choices=[('planned', 'Planifiée'), ('completed', 'Réalisée'), ('missed', 'Manquée')], default='planned', max_length=10)),
                ('stress_level', models.PositiveSmallIntegerField(default=0, help_text='0-10 (synthétique)')),
                ('anxiety_level', models.PositiveSmallIntegerField(default=0)),
                ('isolation_level', models.PositiveSmallIntegerField(default=0)),
                ('notes', models.TextField(blank=True)),
                ('reminder_sent', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('dossier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessions', to='wellbeing.psychdossier')),
            ],
            options={'ordering': ['scheduled_at']},
        ),
        migrations.CreateModel(
            name='DossierAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=wellbeing.models.dossier_attachment_path, validators=[wellbeing.models.validate_upload_extension])),
                ('description', models.CharField(blank=True, max_length=200)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('dossier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='wellbeing.psychdossier')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Pièce jointe',
                'verbose_name_plural': 'Pièces jointes',
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='CaseTimelineEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=120)),
                ('detail', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('dossier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='timeline_events', to='wellbeing.psychdossier')),
            ],
            options={
                'verbose_name': 'Événement timeline',
                'verbose_name_plural': 'Événements timeline',
                'ordering': ['-created_at'],
            },
        ),
    ]
