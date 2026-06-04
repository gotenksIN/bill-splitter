import pytest

from app.schemas.bill import Outing, OutingSplit
from app.services.bill import (
    OutingPaymentBalance,
    calculate_balance,
    calculate_outing_split_with_minimal_transactions,
    get_bill_details_from_image,
)
from tests import examples


class TestCalculateBalance:
    @pytest.mark.parametrize(
        "outing, balance",
        [
            (
                examples.simple_bill.OUTING,
                examples.simple_bill.OUTING_PAYMENT_BALANCE,
            ),
            (
                examples.multiple_bills.OUTING,
                examples.multiple_bills.OUTING_PAYMENT_BALANCE,
            ),
            (
                examples.simple_bill_discounted.OUTING,
                examples.simple_bill_discounted.OUTING_PAYMENT_BALANCE,
            ),
            (
                examples.multiple_bills_discounted.OUTING,
                examples.multiple_bills_discounted.OUTING_PAYMENT_BALANCE,
            ),
        ],
    )
    def test_examples(self, outing: Outing, balance: OutingPaymentBalance):
        assert calculate_balance(outing) == balance


class TestCalculateOutingSplitWithMinimalTransactions:
    @pytest.mark.parametrize(
        "balance, split",
        [
            (
                examples.simple_bill.OUTING_PAYMENT_BALANCE,
                examples.simple_bill.OUTING_SPLIT_WITH_MINIMAL_TRANSACTIONS,
            ),
            (
                examples.multiple_bills.OUTING_PAYMENT_BALANCE,
                examples.multiple_bills.OUTING_SPLIT_WITH_MINIMAL_TRANSACTIONS,
            ),
            (
                examples.simple_bill_discounted.OUTING_PAYMENT_BALANCE,
                examples.simple_bill_discounted.OUTING_SPLIT_WITH_MINIMAL_TRANSACTIONS,
            ),
            (
                examples.multiple_bills_discounted.OUTING_PAYMENT_BALANCE,
                examples.multiple_bills_discounted.OUTING_SPLIT_WITH_MINIMAL_TRANSACTIONS,
            ),
        ],
    )
    def test_examples(self, balance: OutingPaymentBalance, split: OutingSplit):
        assert calculate_outing_split_with_minimal_transactions(balance) == split


import json


class TestGetBillDetailsFromImage:
    success_bill = examples.simple_bill.OCR_BILL

    @pytest.fixture
    def _mock_litellm_service_method(self, monkeypatch: pytest.MonkeyPatch):
        llm_response = {
            "items": [
                {"name": "Pizza", "total_line_price": 600.0, "quantity": 1},
                {"name": "Coke", "total_line_price": 150.0, "quantity": 1},
                {"name": "Ice Cream", "total_line_price": 300.0, "quantity": 1},
            ],
            "tax_amount": 52.5,
            "service_charge_amount": 105.0,
            "discount_amount": 0.0,
            "amount_paid": 1207.50,
        }

        class MockLLMService:
            def get_bill_details_from_image(self, image_bytes: bytes, mime_type: str) -> str:
                return json.dumps(llm_response)

        monkeypatch.setattr("app.services.bill.litellm_service", MockLLMService())

    def test_litellm(self, _mock_litellm_service_method):
        ocr_bill = get_bill_details_from_image(image_bytes=b"fake-image-bytes", mime_type="image/png")
        assert ocr_bill == self.success_bill
