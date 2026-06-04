"""
LiteLLM service for multi-provider LLM calls.

This service provides a unified interface to multiple LLM providers (OpenAI, Anthropic, Google, etc.)
using LiteLLM. It supports custom proxy endpoints via LITELLM_API_BASE.
"""

import base64

from litellm import completion

from app.core.settings import settings
from app.schemas.bill import OCRBill

BILL_OCR_PROMPT = """
You are a highly precise receipt-parsing engine. Your task is to analyze the provided image of a receipt/bill and extract structured data matching the schema.

### Core Rules:
1. **Unit Price vs. Line Total:**
   - **price** must be the **price of a single unit** (unit price).
   - If the receipt displays a line-item total for multiple quantities (e.g., "3 Hot Dogs - $15.00"), you MUST calculate and return the price of a single unit (e.g., unit price = $5.00, quantity = 3).
   - If the receipt only lists a single price next to an item without a quantity, default **quantity** to 1 and **price** to that price.
2. **Numeric Values:**
   - Strip all currency symbols (e.g., $, €, ₹, £) and formatting characters.
   - Parse all floats and integers as pure numeric values.
3. **Accuracy and Exclusions:**
   - Remove leading bullets, line numbers, or stray punctuation from item names. Keep the original item language and spelling.
   - Do NOT extract line-item modifiers, add-ons, or optional toppings (e.g., "Add Cheese - $0.00" or "No Onion") as separate items if their cost is already included in the parent item's price.
   - Do NOT include negative price items, discounts, or vouchers as items in the `items` list. Skip any items with a 0.0 price.
4. **Fees, Taxes, and Discounts:**
   - **tax_rate:** Extract the tax rate applied to the bill as a decimal (e.g., 5.5% tax -> 0.055). If the receipt only lists a flat tax amount (e.g., "Tax: $2.50"), calculate the rate: `tax_amount / subtotal`.
   - **service_charge:** Extract the service charge, gratuity, or tip rate as a decimal (e.g., 10% service charge -> 0.10). If only a flat tip/gratuity amount is listed, calculate the rate: `tip_amount / subtotal`.
   - **discount_amount:** If there is an overall flat discount applied at the bottom of the bill (e.g., "-$10.00 Coupon" or "10% Discount"), extract the positive numeric value of the total discount amount here (e.g., 10.00). If no discount exists, use 0.0.
   - **amount_paid:** This is the absolute final grand total at the bottom of the receipt that was actually paid, after all taxes, service charges, tips, and discounts have been applied.

Please analyze the receipt image and extract the fields with maximum precision.
"""


def get_bill_details_from_image(image_bytes: bytes, mime_type: str) -> str:
    """
    Use LiteLLM to extract bill details from an image.

    Supports multiple LLM providers via a unified interface. Can be configured
    to use a custom proxy endpoint via LITELLM_API_BASE.

    :param image_bytes: The image bytes of the bill
    :param mime_type: The MIME type of the image (e.g., "image/jpeg")
    :return: Extracted bill details as a JSON string
    """
    # Encode image to base64 data URL
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:{mime_type};base64,{base64_image}"

    # Build message with vision content
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": BILL_OCR_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                },
            ],
        }
    ]

    # Build completion kwargs
    kwargs: dict = {
        "model": settings.LITELLM_MODEL,
        "messages": messages,
        "response_format": OCRBill,
        "api_base": settings.LITELLM_API_BASE,
        "api_key": settings.LITELLM_API_KEY,
    }

    response = completion(**kwargs)

    if not response.choices or len(response.choices) == 0:
        raise ValueError("No response from LiteLLM")

    content = response.choices[0].message.content
    if content is None:
        raise ValueError("No content in LiteLLM response")

    return content
