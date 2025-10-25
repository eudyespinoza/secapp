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
            'name': 'starter',
            'display_name': 'Starter',
            'monthly_price': Decimal('25.00'),
            'max_approvers': 2,
            'max_requests_per_month': 0,
            'max_users': 10,
            'order': 1
        },
        {
            'name': 'growth',
            'display_name': 'Growth',
            'monthly_price': Decimal('45.00'),
            'max_approvers': 6,
            'max_requests_per_month': 0,
            'max_users': 25,
            'advanced_analytics': True,
            'api_access': True,
            'order': 2
        },
        {
            'name': 'scale',
            'display_name': 'Scale',
            'monthly_price': Decimal('65.00'),
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
    
    for plan_data in plans_data:
        plan, created = Plan.objects.get_or_create(
            name=plan_data['name'],
            defaults=plan_data
        )
        print(f'Plan {plan.name}: {"Created" if created else "Updated"}')
    
    print('Plans setup completed')

if __name__ == '__main__':
    setup_plans()