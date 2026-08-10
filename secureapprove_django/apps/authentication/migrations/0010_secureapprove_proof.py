import django.db.models.deletion
import django.utils.timezone
import uuid

from django.db import migrations, models


def create_ledger_heads(apps, schema_editor):
    Tenant = apps.get_model('tenants', 'Tenant')
    ProofLedgerHead = apps.get_model('authentication', 'ProofLedgerHead')
    ProofLedgerHead.objects.bulk_create(
        [ProofLedgerHead(tenant_id=tenant_id) for tenant_id in Tenant.objects.values_list('id', flat=True)],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0009_termsapprovalsession_transaction_security'),
        ('requests', '0002_requestattachment'),
        ('tenants', '0006_tenant_proof_retention_years'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProofSigningKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kid', models.CharField(max_length=128, unique=True, verbose_name='Key ID')),
                ('key_arn', models.CharField(blank=True, max_length=512, verbose_name='AWS KMS key ARN')),
                ('algorithm', models.CharField(default='ES256', max_length=16, verbose_name='Algorithm')),
                ('public_jwk', models.JSONField(verbose_name='Public JWK')),
                ('status', models.CharField(choices=[('active', 'Active'), ('retired', 'Retired'), ('compromised', 'Compromised')], default='active', max_length=16, verbose_name='Status')),
                ('activated_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Activated At')),
                ('deactivated_at', models.DateTimeField(blank=True, null=True, verbose_name='Deactivated At')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
            ],
            options={'verbose_name': 'Proof Signing Key', 'verbose_name_plural': 'Proof Signing Keys', 'ordering': ['-activated_at']},
        ),
        migrations.CreateModel(
            name='ProofLedgerHead',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_entry_sha256', models.CharField(blank=True, default='', max_length=64)),
                ('entry_count', models.PositiveBigIntegerField(default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='proof_ledger_head', to='tenants.tenant')),
            ],
            options={'verbose_name': 'Proof Ledger Head', 'verbose_name_plural': 'Proof Ledger Heads'},
        ),
        migrations.CreateModel(
            name='SecurityProof',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('schema', models.CharField(default='sap-proof-v1', max_length=32)),
                ('event_type', models.CharField(choices=[('approval_request', 'Approval Request'), ('iframe_acceptance', 'Iframe Acceptance')], max_length=32)),
                ('decision', models.CharField(choices=[('approve', 'Approve'), ('reject', 'Reject')], max_length=16)),
                ('transaction_sha256', models.CharField(db_index=True, max_length=64)),
                ('webauthn_assertion_sha256', models.CharField(max_length=64)),
                ('previous_ledger_sha256', models.CharField(blank=True, default='', max_length=64)),
                ('ledger_entry_sha256', models.CharField(max_length=64, unique=True)),
                ('protected_header', models.JSONField(default=dict)),
                ('public_payload', models.JSONField(default=dict)),
                ('jws', models.TextField()),
                ('evidence_ciphertext', models.BinaryField(blank=True, null=True)),
                ('evidence_nonce', models.BinaryField(blank=True, null=True)),
                ('encrypted_data_key', models.BinaryField(blank=True, null=True)),
                ('evidence_expires_at', models.DateTimeField(db_index=True)),
                ('evidence_purged_at', models.DateTimeField(blank=True, null=True)),
                ('archive_status', models.CharField(choices=[('pending', 'Pending'), ('archived', 'Archived'), ('delayed', 'Delayed'), ('failed', 'Failed'), ('disabled', 'Disabled')], default='pending', max_length=16)),
                ('archive_object_key', models.CharField(blank=True, max_length=512)),
                ('archive_version_id', models.CharField(blank=True, max_length=255)),
                ('archived_at', models.DateTimeField(blank=True, null=True)),
                ('archive_error', models.TextField(blank=True)),
                ('issued_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='actor_security_proofs', to='authentication.user')),
                ('approval_audit', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='security_proof', to='authentication.approvalaudit')),
                ('signing_key', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='proofs', to='authentication.proofsigningkey')),
                ('subject_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='subject_security_proofs', to='authentication.user')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='security_proofs', to='tenants.tenant')),
                ('terms_audit', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='security_proof', to='authentication.termsacceptanceaudit')),
            ],
            options={'verbose_name': 'Security Proof', 'verbose_name_plural': 'Security Proofs', 'ordering': ['-issued_at']},
        ),
        migrations.AddIndex(model_name='securityproof', index=models.Index(fields=['tenant', 'issued_at'], name='authentica_tenant__b0990a_idx')),
        migrations.AddIndex(model_name='securityproof', index=models.Index(fields=['tenant', 'archive_status'], name='authentica_tenant__7764f3_idx')),
        migrations.AddIndex(model_name='securityproof', index=models.Index(fields=['event_type', 'decision'], name='authentica_event_t_7f54b2_idx')),
        migrations.RunPython(create_ledger_heads, migrations.RunPython.noop),
    ]
