import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('students', '0002_add_user_link'),
        ('wellbeing', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Meeting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_at', models.DateTimeField(verbose_name='Date et heure prévues')),
                ('duration_minutes', models.PositiveSmallIntegerField(default=45, verbose_name='Durée prévue (min)')),
                ('topic', models.CharField(help_text="Sera visible par l'élève", max_length=200, verbose_name='Sujet du RDV')),
                ('counselor_notes', models.TextField(blank=True, help_text="Notes internes — non visibles par l'élève", verbose_name='Notes du conseiller')),
                ('student_message', models.TextField(blank=True, help_text="Message lors de l'approbation / refus", verbose_name="Message de l'élève")),
                ('status', models.CharField(choices=[('proposed', "Proposé · en attente de l'élève"), ('approved', 'Approuvé'), ('rejected', 'Refusé'), ('cancelled', 'Annulé'), ('completed', 'Terminé'), ('missed', 'Manqué')], default='proposed', max_length=20)),
                ('room_token', models.CharField(blank=True, help_text='Identifiant secret du salon Jitsi', max_length=64, null=True, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('counselor_joined_at', models.DateTimeField(blank=True, null=True)),
                ('student_joined_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('counselor', models.ForeignKey(help_text='Conseiller qui a proposé le RDV', on_delete=django.db.models.deletion.CASCADE, related_name='proposed_meetings', to=settings.AUTH_USER_MODEL)),
                ('dossier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='meetings', to='wellbeing.psychdossier')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='meetings', to='students.student')),
            ],
            options={
                'verbose_name': 'Rendez-vous en ligne',
                'verbose_name_plural': 'Rendez-vous en ligne',
                'ordering': ['-scheduled_at'],
                'indexes': [models.Index(fields=['status', 'scheduled_at'], name='meetings_me_status_e9adde_idx')],
            },
        ),
    ]
