import accounts.invitations
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_student_role'),
        ('students', '0002_add_user_link'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentInvitation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(default=accounts.invitations._generate_invitation_code, editable=False, max_length=24, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(default=accounts.invitations._default_invitation_expiry)),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_invitations', to=settings.AUTH_USER_MODEL)),
                ('used_by_user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='claimed_invitation', to=settings.AUTH_USER_MODEL)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invitations', to='students.student')),
            ],
            options={
                'verbose_name': 'Invitation élève',
                'verbose_name_plural': 'Invitations élèves',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['code'], name='accounts_st_code_4eaa10_idx')],
            },
        ),
    ]
