from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from apps.requests.models import ApprovalRequest
from apps.tenants.models import Tenant


User = get_user_model()


class RequestDetailAmountTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            key="amount-format",
            name="Amount Format",
            status="active",
        )
        self.user = User.objects.create_user(
            username="amount-owner",
            email="amount-owner@example.test",
            password="test-password",
            role="requester",
            tenant=self.tenant,
        )
        self.approval_request = ApprovalRequest.objects.create(
            title="Large expense",
            description="Readable amount regression test",
            category="expense",
            priority="high",
            status="rejected",
            amount=Decimal("6500000.00"),
            requester=self.user,
            tenant=self.tenant,
            rejection_reason="Outside policy",
            metadata={
                "receipt_ref": "RCPT-2026-001",
                "expense_category": "Travel",
            },
        )
        self.client.force_login(self.user)

    def test_amount_uses_required_grouping_and_accessible_card_tokens(self):
        with translation.override("es"):
            url = reverse("requests:detail", args=[self.approval_request.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "6.500.000,00", count=3)
        self.assertNotContains(response, "$6500000,00")
        self.assertContains(response, 'class="amount-label"')
        self.assertContains(response, 'class="amount-value"')
        self.assertContains(response, 'font-variant-numeric: tabular-nums')
        self.assertContains(response, '[data-theme="dark"] .request-detail-page')

    def test_detail_status_and_metadata_are_translated_in_spanish(self):
        with translation.override("es"):
            url = reverse("requests:detail", args=[self.approval_request.id])
        response = self.client.get(url)

        self.assertContains(response, "Esta solicitud fue rechazada el")
        self.assertContains(response, "Referencia de Recibo")
        self.assertContains(response, "Categoría de Gastos")
        self.assertNotContains(response, "This request was rejected on")

    def test_detail_status_and_metadata_are_translated_in_portuguese(self):
        with translation.override("pt-br"):
            url = reverse("requests:detail", args=[self.approval_request.id])
        response = self.client.get(url)

        self.assertContains(response, "Esta solicitação foi rejeitada em")
        self.assertContains(response, "Referência do Recibo")
        self.assertContains(response, "Categoria de Despesas")
        self.assertNotContains(response, "This request was rejected on")

    def test_list_translates_count_and_metadata_and_formats_amount(self):
        with translation.override("es"):
            url = reverse("requests:list")
        response = self.client.get(url)

        self.assertContains(response, "6.500.000,00")
        self.assertContains(response, "solicitud en total")
        self.assertContains(response, "Referencia de Recibo")
        self.assertContains(response, "Categoría de Gastos")
        self.assertNotContains(response, "Receipt_Ref")
        self.assertNotContains(response, "Expense_Category")
