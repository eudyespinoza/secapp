from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0005_alter_tenant_plan_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='tenant',
            name='proof_retention_years',
            field=models.PositiveSmallIntegerField(
                choices=[(1, '1 year'), (3, '3 years'), (5, '5 years'), (7, '7 years'), (10, '10 years')],
                default=7,
                help_text='Applies to private evidence created after this setting is changed.',
                verbose_name='SecureApprove Proof evidence retention',
            ),
        ),
    ]
