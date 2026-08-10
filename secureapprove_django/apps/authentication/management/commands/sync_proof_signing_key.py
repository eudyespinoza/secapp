from django.core.management.base import BaseCommand, CommandError

from apps.authentication.proof_service import ProofUnavailable, sync_active_signing_key


class Command(BaseCommand):
    help = 'Fetch and persist the active SecureApprove Proof public key from AWS KMS.'

    def handle(self, *args, **options):
        try:
            key = sync_active_signing_key()
        except ProofUnavailable as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f'Active Proof signing key: {key.kid}'))
