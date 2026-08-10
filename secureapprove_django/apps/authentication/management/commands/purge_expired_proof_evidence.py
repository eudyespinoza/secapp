from django.core.management.base import BaseCommand

from apps.authentication.tasks import purge_expired_proof_evidence


class Command(BaseCommand):
    help = 'Delete expired encrypted SecureApprove Proof evidence and retain public JWS records.'

    def handle(self, *args, **options):
        count = purge_expired_proof_evidence.run()
        self.stdout.write(self.style.SUCCESS(f'Purged evidence for {count} proof(s).'))
