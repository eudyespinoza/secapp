# Generated manually on 2025-12-05
# Migration to convert old plan values to new per-user pricing tiers

from django.db import migrations


def migrate_plan_values(apps, schema_editor):
    """
    Convert old plan values to new tier-based values:
    - starter -> tier_1 (2-6 users)
    - growth -> tier_2 (7-12 users)
    - scale -> tier_3 (12+ users)
    """
    Tenant = apps.get_model('tenants', 'Tenant')
    
    # Map old plan values to new ones
    plan_mapping = {
        'starter': 'tier_1',
        'growth': 'tier_2',
        'scale': 'tier_3',
    }
    
    for old_plan, new_plan in plan_mapping.items():
        Tenant.objects.filter(plan_id=old_plan).update(plan_id=new_plan)


def reverse_migrate_plan_values(apps, schema_editor):
    """
    Reverse migration: convert new tier values back to old plan names
    """
    Tenant = apps.get_model('tenants', 'Tenant')
    
    plan_mapping = {
        'tier_1': 'starter',
        'tier_2': 'growth',
        'tier_3': 'scale',
    }
    
    for new_plan, old_plan in plan_mapping.items():
        Tenant.objects.filter(plan_id=new_plan).update(plan_id=old_plan)


class Migration(migrations.Migration):

    dependencies = [
        ('tenants', '0003_alter_tenant_plan_id'),
    ]

    operations = [
        migrations.RunPython(migrate_plan_values, reverse_migrate_plan_values),
    ]
