from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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
        )
        self.client.force_login(self.user)

    def test_amount_uses_localized_grouping_and_accessible_card_tokens(self):
        url = reverse("requests:detail", args=[self.approval_request.id])
        response = self.client.get(url.replace("/en/", "/es/", 1))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "6\u00a0500\u00a0000,00", count=3)
        self.assertNotContains(response, "$6500000,00")
        self.assertContains(response, 'class="amount-label"')
        self.assertContains(response, 'class="amount-value"')
        self.assertContains(response, 'font-variant-numeric: tabular-nums')
        self.assertContains(response, '[data-theme="dark"] .request-detail-page')
