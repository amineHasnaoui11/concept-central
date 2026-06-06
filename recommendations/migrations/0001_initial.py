import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('education', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='InterventionRecommendation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anonymized_payload', models.JSONField(help_text='Données envoyées au LLM (sans nom réel).')),
                ('recommendation_text', models.TextField()),
                ('urgency', models.CharField(blank=True, max_length=20)),
                ('suggested_actions', models.JSONField(blank=True, default=list)),
                ('model_used', models.CharField(default='fallback', max_length=80)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('alert', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='llm_recommendation', to='education.alert')),
            ],
            options={
                'verbose_name': 'Recommandation LLM',
                'verbose_name_plural': 'Recommandations LLM',
            },
        ),
    ]
