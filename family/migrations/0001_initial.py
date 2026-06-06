import family.models
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ParentMagicLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('parent_email', models.EmailField(db_index=True, max_length=254)),
                ('token', models.CharField(default=family.models._generate_token, editable=False, max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(default=family.models._default_expiry)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
            ],
            options={
                'verbose_name': "Lien d'accès parent",
                'verbose_name_plural': "Liens d'accès parent",
                'ordering': ['-created_at'],
            },
        ),
    ]
