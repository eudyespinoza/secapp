# ==================================================
# SecureApprove Django - Setup Admin User Command
# ==================================================

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'Setup admin user configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default='eudyespinoza@gmail.com',
            help='Admin user email'
        )

    def handle(self, *args, **options):
        User = get_user_model()
        email = options['email']
        
        try:
            # Get or create user
            user = User.objects.filter(email=email).first()
            if not user:
                self.stdout.write(
                    self.style.ERROR(f'User {email} not found')
                )
                return
            
            # Configure as superuser
            user.is_superuser = True
            user.is_staff = True
            user.role = 'admin'
            user.save()
            
            # Get or create tenant
            tenant, created = Tenant.objects.get_or_create(
                key='admin-tenant',
                defaults={
                    'name': 'SecureApprove Admin',
                    'plan_id': 'scale',
                    'approver_limit': 999,
                    'status': 'active',
                    'is_active': True
                }
            )
            
            # Assign tenant to user
            user.tenant = tenant
            user.save()
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created tenant: {tenant.name}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'Using existing tenant: {tenant.name}')
                )
                
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully configured {email} as admin user with tenant access'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error setting up admin user: {str(e)}')
            )