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
            name='RiskThreshold',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Configuration par défaut', max_length=80)),
                ('max_absences', models.PositiveSmallIntegerField(default=3, help_text="Au-delà de ce nombre d'absences → contribution au risque.")),
                ('grade_drop_percent', models.PositiveSmallIntegerField(default=30, help_text='Baisse de notes (%) considérée comme significative.')),
                ('critical_grade_threshold', models.DecimalField(decimal_places=2, default=5.0, help_text='Note absolue en dessous de laquelle un risque est signalé', max_digits=4)),
                ('critical_score', models.PositiveSmallIntegerField(default=75, help_text='Score ≥ seuil critique → suggestion dossier psychologique.')),
                ('high_risk_score', models.PositiveSmallIntegerField(default=50)),
                ('is_active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Seuil de risque',
                'verbose_name_plural': 'Seuils de risque',
            },
        ),
        migrations.CreateModel(
            name='WeeklyEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week_start', models.DateField()),
                ('absences', models.PositiveSmallIntegerField(default=0)),
                ('control_grade', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('previous_grade', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('behavioral_incident', models.BooleanField(default=False)),
                ('observation', models.TextField(blank=True)),
                ('risk_score', models.PositiveSmallIntegerField(default=0)),
                ('risk_level', models.CharField(blank=True, max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recorded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recorded_entries', to=settings.AUTH_USER_MODEL)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='weekly_entries', to='students.student')),
            ],
            options={
                'verbose_name': 'Saisie hebdomadaire',
                'verbose_name_plural': 'Saisies hebdomadaires',
                'ordering': ['-week_start'],
                'unique_together': {('student', 'week_start')},
            },
        ),
        migrations.CreateModel(
            name='SubjectGrade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(choices=[('maths', 'Mathématiques'), ('french', 'Français'), ('arabic', 'Arabe'), ('english', 'Anglais'), ('sciences', 'Sciences'), ('history', 'Histoire-Géo'), ('other', 'Autre')], max_length=20)),
                ('grade', models.DecimalField(decimal_places=2, max_digits=5)),
                ('previous_grade', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('weekly_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subject_grades', to='education.weeklyentry')),
            ],
            options={
                'verbose_name': 'Note par matière',
                'verbose_name_plural': 'Notes par matière',
                'unique_together': {('weekly_entry', 'subject')},
            },
        ),
        migrations.CreateModel(
            name='DailyAttendance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('status', models.CharField(choices=[('present', 'Présent'), ('absent', 'Absent'), ('late', 'Retard'), ('excused', 'Excusé')], max_length=10)),
                ('notes', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recorded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendances', to='students.student')),
            ],
            options={
                'verbose_name': 'Présence journalière',
                'verbose_name_plural': 'Présences journalières',
                'ordering': ['-date'],
                'unique_together': {('student', 'date')},
            },
        ),
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(choices=[('medium', 'Risque modéré'), ('high', 'Risque élevé'), ('critical', 'Risque critique')], max_length=20)),
                ('risk_score', models.PositiveSmallIntegerField()),
                ('summary', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('validated', 'Validée'), ('resolved', 'Résolue'), ('dismissed', 'Écartée')], default='pending', max_length=20)),
                ('suggests_psych_dossier', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('validated_at', models.DateTimeField(blank=True, null=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='students.student')),
                ('validated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='validated_alerts', to=settings.AUTH_USER_MODEL)),
                ('weekly_entry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='education.weeklyentry')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='Intervention',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('intervention_type', models.CharField(choices=[('interview', 'Entretien individuel'), ('family', 'Contact famille'), ('referral', 'Orientation spécialisée'), ('other', 'Autre')], max_length=20)),
                ('planned_date', models.DateField()),
                ('notes', models.TextField(blank=True)),
                ('completed', models.BooleanField(default=False)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('effectiveness_rating', models.PositiveSmallIntegerField(choices=[(0, 'Non évaluée'), (1, 'Très peu efficace'), (2, 'Peu efficace'), (3, 'Modérée'), (4, 'Bonne'), (5, 'Excellente')], default=0, help_text="Évalué après l'intervention")),
                ('follow_up_notes', models.TextField(blank=True, help_text="Observations sur l'effet de l'intervention")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('alert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='interventions', to='education.alert')),
                ('planned_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['planned_date']},
        ),
        migrations.CreateModel(
            name='TeacherRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('priority', models.CharField(choices=[('low', 'Basse'), ('medium', 'Moyenne'), ('high', 'Élevée'), ('urgent', 'Urgente')], default='medium', max_length=20)),
                ('subject', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('in_progress', 'En cours'), ('resolved', 'Résolue')], default='pending', max_length=20)),
                ('response', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_requests', to=settings.AUTH_USER_MODEL)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teacher_requests', to='students.student')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Demande enseignant',
                'verbose_name_plural': 'Demandes enseignants',
                'ordering': ['-created_at'],
            },
        ),
    ]
