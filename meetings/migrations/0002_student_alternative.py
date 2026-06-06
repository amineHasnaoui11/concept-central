from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('meetings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='meeting',
            name='student_alternative_proposal',
            field=models.DateTimeField(
                blank=True, null=True,
                verbose_name="Date alternative proposée par l'élève",
                help_text="Si refus avec contre-proposition, l'élève suggère une autre date",
            ),
        ),
    ]
