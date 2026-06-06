from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('operator', 'Opérateur (Enseignant)'),
                    ('supervisor', 'Superviseur (Conseiller / Psychologue)'),
                    ('admin', 'Admin (Direction)'),
                    ('student', 'Élève'),
                ],
                default='operator',
                max_length=20,
            ),
        ),
    ]
