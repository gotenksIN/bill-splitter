"""
LiteLLM service for multi-provider LLM calls.

This service provides a unified interface to multiple LLM providers (OpenAI, Anthropic, Google, etc.)
using LiteLLM. It supports custom proxy endpoints via LITELLM_API_BASE.
"""

import base64

from litellm import completion

from app.core.settings import settings
from app.schemas.bill import LLMOCRBill

BILL_OCR_PROMPT = """
You are a highly precise receipt-parsing engine. Extract structured data from the receipt image.

Rules:
1. **Raw Line Totals:** Extract the total line price and quantity for each ordered item. Do not do any unit price division math.
2. **Numeric Values:** Strip currency symbols and formatting.
3. **Exclusions:** Remove leading line numbers/bullets from item names. Skip items with 0 total price. Do not extract optional modifiers.
4. **Fees, Taxes, and Discounts:** Extract raw flat amounts as displayed on the bill:
   - **tax_amount:** The flat tax amount (e.g., 2.50). If no tax, use 0.0.
   - **service_charge_amount:** The flat tip or gratuity/service charge amount (e.g., 5.00). If none, use 0.0.
   - **discount_amount:** The total discount amount (e.g., 10.00). If none, use 0.0.
   - **amount_paid:** The grand total amount actually paid.
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
        "response_format": LLMOCRBill,
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
