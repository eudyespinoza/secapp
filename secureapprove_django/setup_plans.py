#!/usr/bin/env python
"""Setup default billing plans"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.billing.models import Plan
from decimal import Decimal

def setup_plans():
    """Create default billing plans"""
    
    plans_data = [
        {
            'name': 'tier_1',
            'display_name': 'Small Team (2-6 users)',
            'monthly_price': Decimal('60.00'),
            'max_approvers': 6,
            'max_requests_per_month': 0,
            'max_users': 6,
            'advanced_analytics': True,
            'api_access': True,
            'custom_workflows': False,
            'priority_support': False,
            'order': 1
        },
        {
            'name': 'tier_2',
            'display_name': 'Medium Team (7-12 users)',
            'monthly_price': Decimal('55.00'),
            'max_approvers': 12,
            'max_requests_per_month': 0,
            'max_users': 12,
            'advanced_analytics': True,
            'api_access': True,
            'custom_workflows': True,
            'priority_support': False,
            'order': 2
        },
        {
            'name': 'tier_3',
            'display_name': 'Large Team (12+ users)',
            'monthly_price': Decimal('50.00'),
            'max_approvers': 999999,
            'max_requests_per_month': 0,
            'max_users': 0,
            'advanced_analytics': True,
            'api_access': True,
            'custom_workflows': True,
            'priority_support': True,
            'order': 3
        }
    ]
    
    # Deactivate old plans
    old_plans = ['starter', 'growth', 'scale']
    Plan.objects.filter(name__in=old_plans).update(is_active=False)
    print('Old plans deactivated')
    
    for plan_data in plans_data:
        plan, created = Plan.objects.update_or_create(
            name=plan_data['name'],
            defaults=plan_data
        )
        print(f'Plan {plan.name}: {"Created" if created else "Updated"}')
    
    print('Plans setup completed')

if __name__ == '__main__':
    setup_plans()