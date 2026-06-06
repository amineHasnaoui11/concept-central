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
            name='DataAccessRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('requester_email', models.EmailField(max_length=254)),
                ('request_type', models.CharField(choices=[('access', "Droit d'accès"), ('rectification', 'Rectification'), ('erasure', 'Effacement'), ('portability', 'Portabilité')], max_length=20)),
                ('description', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('processed', 'Traitée'), ('rejected', 'Rejetée')], default='pending', max_length=20)),
                ('response_notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='data_access_requests', to='students.student')),
            ],
            options={
                'verbose_name': "Demande d'accès aux données",
                'verbose_name_plural': "Demandes d'accès aux données",
                'ordering': ['-created_at'],
            },
        ),
    ]
