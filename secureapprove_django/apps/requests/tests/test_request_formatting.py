from decimal import Decimal

from django.test import SimpleTestCase

from apps.requests.templatetags.request_formatting import format_amount


class FormatAmountTests(SimpleTestCase):
    def test_formats_large_amount_with_dot_grouping_and_comma_decimals(self):
        self.assertEqual(format_amount(Decimal("6500000.00")), "6.500.000,00")

    def test_rounds_to_exactly_two_decimals(self):
        self.assertEqual(format_amount(Decimal("1234.565")), "1.234,57")

    def test_formats_negative_amount(self):
        self.assertEqual(format_amount(Decimal("-1234.5")), "-1.234,50")

    def test_preserves_invalid_values(self):
        self.assertEqual(format_amount("not-an-amount"), "not-an-amount")
