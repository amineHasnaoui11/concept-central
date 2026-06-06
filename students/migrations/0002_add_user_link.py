import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0001_initial'),
        ('accounts', '0002_add_student_role'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='user',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='student_profile',
                to=settings.AUTH_USER_MODEL,
                help_text="Compte de connexion de l'élève (créé par le conseiller).",
            ),
        ),
    ]
