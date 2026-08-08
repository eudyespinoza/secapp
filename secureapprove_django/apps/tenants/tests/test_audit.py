from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.authentication.models import ApprovalAudit, TermsAcceptanceAudit
from apps.requests.models import ApprovalRequest
from apps.tenants.models import Tenant


User = get_user_model()


class TenantAuditViewTests(TestCase):
    password = "test-password"

    def setUp(self):
        self.tenant = Tenant.objects.create(key="acme", name="Acme", status="active")
        self.other_tenant = Tenant.objects.create(key="other", name="Other", status="active")
        self.admin = User.objects.create_user(
            username="acme-admin",
            email="admin@acme.test",
            password=self.password,
            role="tenant_admin",
            tenant=self.tenant,
        )
        self.actor = User.objects.create_user(
            username="actor",
            email="actor@acme.test",
            password=self.password,
            role="approver",
            tenant=self.tenant,
        )
        self.other_actor = User.objects.create_user(
            username="other-actor",
            email="actor@other.test",
            password=self.password,
            role="approver",
            tenant=self.other_tenant,
        )
        self.request = ApprovalRequest.objects.create(
            title="Approve supplier contract",
            description="Contract approval",
            requester=self.admin,
            tenant=self.tenant,
        )
        self.other_request = ApprovalRequest.objects.create(
            title="Other tenant request",
            description="Must never be visible to Acme",
            requester=self.other_actor,
            tenant=self.other_tenant,
        )
        self.success_audit = ApprovalAudit.objects.create(
            approval_request=self.request,
            user=self.actor,
            credential_id="credential-success",
            challenge_id="challenge-success",
            action="approve",
            status="success",
            ip_address="192.0.2.10",
            user_agent="Test Browser",
            context_data={"decision": "approve"},
        )
        self.failed_audit = ApprovalAudit.objects.create(
            approval_request=self.request,
            user=self.actor,
            credential_id="credential-failed",
            challenge_id="challenge-failed",
            action="reject",
            status="failed",
            ip_address="192.0.2.11",
            error_message="Signature rejected",
        )
        ApprovalAudit.objects.create(
            approval_request=self.other_request,
            user=self.other_actor,
            credential_id="credential-other",
            challenge_id="challenge-other",
            action="approve",
            status="success",
            ip_address="198.51.100.3",
        )
        self.client.force_login(self.admin)
        self.url = reverse("tenants:audit")

    def test_approval_filters_metrics_and_tenant_isolation(self):
        response = self.client.get(
            self.url,
            {
                "type": "approvals",
                "status": "failed",
                "action": "reject",
                "q": str(self.request.id),
                "ip": "192.0.2.11",
                "sort": "oldest",
                "page_size": "25",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertEqual(response.context["metrics"]["total"], 1)
        self.assertEqual(response.context["metrics"]["successful"], 0)
        self.assertEqual(response.context["metrics"]["attention"], 1)
        self.assertEqual(response.context["metrics"]["unique_users"], 1)
        self.assertEqual(response.context["page_size"], 25)
        self.assertContains(response, "Signature rejected")
        self.assertContains(response, reverse("requests:detail", args=[self.request.id]))
        self.assertNotContains(response, "Other tenant request")

    def test_date_filter_and_terms_search_cover_evidence_fields(self):
        old_terms = TermsAcceptanceAudit.objects.create(
            tenant=self.tenant,
            user=self.actor,
            initiated_by=self.admin,
            document_type="privacy",
            document_version="2025-01",
            document_hash="old-document-hash",
            status="success",
            credential_id="terms-credential",
            challenge_id="terms-challenge",
            ip_address="203.0.113.8",
        )
        TermsAcceptanceAudit.objects.filter(pk=old_terms.pk).update(
            performed_at=timezone.now() - timedelta(days=10)
        )
        TermsAcceptanceAudit.objects.create(
            tenant=self.tenant,
            user=self.actor,
            initiated_by=self.admin,
            document_type="terms",
            document_version="2026-08",
            document_hash="current-document-hash",
            status="success",
            credential_id="current-credential",
            challenge_id="current-challenge",
            ip_address="203.0.113.9",
        )

        response = self.client.get(
            self.url,
            {
                "type": "terms",
                "date_from": timezone.localdate().isoformat(),
                "q": "current-document-hash",
            },
        )

        self.assertEqual(response.context["page_obj"].paginator.count, 1)
        self.assertContains(response, "2026-08")
        self.assertNotContains(response, "2025-01")

    def test_csv_export_honors_filters_and_prevents_formula_injection(self):
        self.request.title = '=HYPERLINK("https://example.test")'
        self.request.save(update_fields=["title"])

        response = self.client.get(
            self.url,
            {"type": "approvals", "status": "success", "format": "csv"},
        )
        content = b"".join(response.streaming_content).decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertIn("secureapprove-acme-approvals-audit", response["Content-Disposition"])
        self.assertIn("'=HYPERLINK", content)
        self.assertIn("credential-success", content)
        self.assertNotIn("credential-failed", content)
        self.assertNotIn("credential-other", content)

    def test_invalid_filter_values_are_reported_without_breaking_the_page(self):
        response = self.client.get(
            self.url,
            {
                "type": "approvals",
                "ip": "not-an-ip",
                "date_from": "2026-99-99",
                "page_size": "9999",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_size"], 50)
        self.assertEqual(len(response.context["filter_errors"]), 2)
        self.assertContains(response, 'role="alert"')

    def test_non_admin_cannot_open_tenant_audit(self):
        regular_user = User.objects.create_user(
            username="regular",
            email="regular@acme.test",
            password=self.password,
            role="requester",
            tenant=self.tenant,
        )
        self.client.force_login(regular_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("landing:index"))

    def test_template_exposes_accessible_controls_and_dark_mode_tokens(self):
        response = self.client.get(self.url, {"type": "approvals"})

        self.assertContains(response, 'class="audit-table-scroll"')
        self.assertContains(response, 'role="link"')
        self.assertContains(response, '[data-theme="dark"] .audit-page')
        self.assertContains(response, "audit-evidence")

    def test_spanish_audit_labels_are_translated(self):
        spanish_url = self.url.replace("/en/", "/es/", 1)
        response = self.client.get(spanish_url, {"type": "approvals"})

        self.assertContains(response, "Registro de auditoría")
        self.assertContains(response, "Todos los estados")
        self.assertContains(response, "Auditorías de aprobación")
        self.assertContains(response, "Fecha y hora")
        self.assertContains(response, "Restablecer")
