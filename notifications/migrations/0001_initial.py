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
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('recipient_email', models.EmailField(blank=True, max_length=254)),
                ('channel', models.CharField(choices=[('in_app', 'Application'), ('email', 'Email')], default='in_app', max_length=10)),
                ('event', models.CharField(choices=[
                    ('alert.created', 'Alerte créée'),
                    ('session.missed', 'Séance manquée'),
                    ('request.received', 'Demande enseignant reçue'),
                    ('intervention.planned', 'Intervention planifiée'),
                    ('dossier.opened', 'Dossier ouvert'),
                ], max_length=40)),
                ('title', models.CharField(max_length=180)),
                ('message', models.TextField(blank=True)),
                ('link', models.CharField(blank=True, max_length=300)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('sent_via_email_at', models.DateTimeField(blank=True, null=True)),
                ('recipient_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Notification',
                'verbose_name_plural': 'Notifications',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['recipient_user', 'read_at'], name='notif_user_read_idx'),
                ],
            },
        ),
    ]
