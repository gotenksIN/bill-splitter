from google.genai import Client, types

from app.core.settings import settings

BILL_OCR_PROMPT = """
You are an expert at analyzing receipts and bills.
Extract the details from the provided image into the requested structure.

Field Instructions:
- items: Extract the individual line items ordered.
  - name: The clean name of the item. Remove stray punctuation or leading bullets, but keep the original language/spelling.
  - price: The unit price of the item. Do not include discounts or negative values as items. Skip items with a 0 price.
  - quantity: The quantity ordered. If a quantity is not explicitly written, default to 1.
- tax_rate: The tax rate applied to the bill as a decimal (e.g., 0.05 for 5%). If the bill only shows a flat tax amount, calculate the decimal rate by dividing the tax amount by the subtotal. Default to 0.0 if no tax is found.
- service_charge: The service charge, tip, or gratuity as a decimal (e.g., 0.10 for 10%). Calculate this based on the subtotal if only a flat amount is shown. Default to 0.0 if not found.
- discount_amount: If the bill includes a flat discount applied to the overall total, extract the positive discount amount here. Default to 0.0 if not found.
- amount_paid: The final total amount on the receipt, after all taxes, service charges, and discounts are applied.

Analyze the bill image and extract the information accurately.
"""

GENERATE_CONTENT_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "tax_rate": types.Schema(
                type=types.Type.NUMBER,
            ),
            "service_charge": types.Schema(
                type=types.Type.NUMBER,
            ),
            "amount_paid": types.Schema(
                type=types.Type.NUMBER,
            ),
            "items": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "name": types.Schema(
                            type=types.Type.STRING,
                        ),
                        "price": types.Schema(
                            type=types.Type.NUMBER,
                        ),
                        "quantity": types.Schema(
                            type=types.Type.NUMBER,
                        ),
                    },
                    required=[
                        "name",
                        "price",
                        "quantity",
                    ],
                ),
            ),
        },
        required=[
            "items",
            "amount_paid",
            "tax_rate",
            "service_charge",
        ],
    ),
)


_client = None

def get_client() -> Client:
    global _client
    if _client is None:
        if settings.GEMINI_API_BASE:
            _client = Client(
                api_key=settings.GEMINI_API_KEY,
                http_options=types.HttpOptions(base_url=settings.GEMINI_API_BASE),
            )
        else:
            _client = Client(api_key=settings.GEMINI_API_KEY)
    return _client

def get_bill_details_from_image(image_bytes: bytes, mime_type: str) -> str:
    """
    Use Gemini API to extract bill details from an image.

    :param image_bytes: The image bytes of the bill
    :return: Extracted bill details as an OCRBill object
    """
    client = get_client()

    model = settings.GEMINI_MODEL
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=BILL_OCR_PROMPT),
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        ),
    ]

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=GENERATE_CONTENT_CONFIG,
    )

    if response.candidates is None or len(response.candidates) == 0:
        raise ValueError("No response from Gemini API")

    candidate = response.candidates[0]
    if candidate.content is None or candidate.content.parts is None or len(candidate.content.parts) == 0:
        raise ValueError("No content parts in Gemini API response")

    bill_data = candidate.content.parts[0].text
    if bill_data is None:
        raise ValueError("No text content in Gemini API response")

    return bill_data
