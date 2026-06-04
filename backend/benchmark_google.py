import time
import json
import re
from pathlib import Path
import os
from google.genai import Client, types

from dotenv import load_dotenv
load_dotenv()

API_KEY = os.environ.get('LITELLM_API_KEY')

pricing = {
    'models/gemini-2.5-flash': {'in': 0.30, 'out': 2.50},
    'models/gemini-3.1-pro-preview': {'in': 2.00, 'out': 12.00},
    'models/gemini-3.5-flash': {'in': 1.50, 'out': 9.00},
}

google_models = [
    'models/gemini-2.5-flash',
    'models/gemini-3.1-pro-preview',
    'models/gemini-3.5-flash',
]

# Model-specific thinking configurations using the unified Google Gen AI SDK
model_configs = {
    'models/gemini-2.5-flash': {
        'thinking_budget': 0,
    },
    'models/gemini-3.1-pro-preview': {
        'thinking_level': 'low',
    },
    'models/gemini-3.5-flash': {
        'thinking_level': 'low',
    },
}

print(f"Google models to benchmark: {google_models}")

BILL_OCR_PROMPT = """
You are an expert at analyzing receipts and bills.
Extract the details from the provided image into the requested structure.

Field Instructions:
- items: Extract the individual line items ordered.
  - name: The clean name of the item. Remove stray punctuation or leading bullets, but keep the original language/spelling.
  - price: The unit price of the item. Do not include discounts or negative values as items. Skip items with a 0 price. Do not extract line item modifiers or add-ons as separate items if their price is already included in the parent item's total cost.
  - quantity: The quantity ordered. If a quantity is not explicitly written, default to 1.
- tax_rate: The tax rate applied to the bill as a decimal (e.g., 0.05 for 5%). If the bill only shows a flat tax amount, calculate the decimal rate by dividing the tax amount by the subtotal. Default to 0.0 if no tax is found.
- service_charge: The service charge, tip, or gratuity as a decimal (e.g., 0.10 for 10%). Calculate this based on the subtotal if only a flat amount is shown. Default to 0.0 if not found.
- amount_paid: The final total amount on the receipt, after all taxes, service charges, and discounts are applied.

Analyze the bill image and extract the information accurately.
Return ONLY valid JSON. Do not include markdown formatting.
"""

GOOGLE_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        'tax_rate': types.Schema(type=types.Type.NUMBER),
        'service_charge': types.Schema(type=types.Type.NUMBER),
        'amount_paid': types.Schema(type=types.Type.NUMBER),
        'items': types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    'name': types.Schema(type=types.Type.STRING),
                    'price': types.Schema(type=types.Type.NUMBER),
                    'quantity': types.Schema(type=types.Type.NUMBER),
                },
                required=['name', 'price', 'quantity'],
            ),
        ),
    },
    required=['items', 'amount_paid', 'tax_rate', 'service_charge'],
)

test_cases = [
    {
        "file": "6093552737913081148_121.jpg",
        "gt_items": sorted([(420.0, 1), (319.0, 1), (120.0, 2), (159.0, 1)]),
        "gt_amount": 1138.0
    },
    {
        "file": "IMG20251226134639.jpg",
        "gt_items": sorted([(255.0, 1), (355.0, 1), (355.0, 1)]),
        "gt_amount": 1110.0
    },
    {
        "file": "PXL_20230528_084359642.jpg",
        "gt_items": sorted([
            (228.57, 2), (329.0, 1), (249.0, 1), (189.0, 2), (85.71, 3), 
            (389.0, 1), (439.0, 1), (59.0, 6), (319.0, 1), (85.0, 1)
        ]),
        "gt_amount": 3419.0
    }
]

print(f"{'MODEL':<30} | {'AVG TIME (s)':<12} | {'AVG COST ($)':<12} | {'ACCURATE?':<40}")
print("-" * 100)

def run_benchmarks():
    litellm_api_base = os.environ.get('LITELLM_API_BASE')
    base_url = f"{litellm_api_base.rstrip('/')}/google" if litellm_api_base else None

    google_client = Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(base_url=base_url),
    )

    for model in google_models:
        try:
            total_time = 0
            total_cost = 0
            is_accurate = "True"
            correct_count = 0

            # Build model-specific thinking configuration
            thinking_opts = model_configs.get(model, {})
            thinking_cfg = None
            if 'thinking_level' in thinking_opts or 'thinking_budget' in thinking_opts:
                thinking_cfg = types.ThinkingConfig(
                    thinking_level=thinking_opts.get('thinking_level'),
                    thinking_budget=thinking_opts.get('thinking_budget'),
                    include_thoughts=True
                )

            google_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GOOGLE_RESPONSE_SCHEMA,
                thinking_config=thinking_cfg,
            )
            
            for tc in test_cases:
                file_path = Path(tc['file'])
                if not file_path.exists():
                    file_path = Path(__file__).parent / tc['file']
                if not file_path.exists():
                    file_path = Path(__file__).parent.parent / tc['file']
                image_bytes = file_path.read_bytes()
                google_contents = [
                    types.Content(
                        role='user',
                        parts=[
                            types.Part.from_text(text=BILL_OCR_PROMPT),
                            types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'),
                        ],
                    ),
                ]
                
                start = time.time()
                for attempt in range(3):
                    try:
                        response = google_client.models.generate_content(
                            model=model,
                            contents=google_contents,
                            config=google_config
                        )
                        break
                    except Exception as e:
                        if attempt == 2:
                            raise e
                        time.sleep(5)
                elapsed = time.time() - start
                total_time += elapsed
                
                usage = getattr(response, 'usage_metadata', None)
                if usage is not None:
                    in_tokens = getattr(usage, 'prompt_token_count', 0)
                    out_tokens = getattr(usage, 'candidates_token_count', 0)
                else:
                    in_tokens = 0
                    out_tokens = 0

                cost = (in_tokens * pricing[model]['in'] / 1e6) + (out_tokens * pricing[model]['out'] / 1e6)
                total_cost += cost
                
                # Filter out model thought parts and locate the final text response
                raw_text = ""
                for part in response.candidates[0].content.parts:
                    if part.text and not getattr(part, 'thought', False):
                        raw_text = part.text
                        break

                if not raw_text:
                    raise ValueError("No final response text part found in response candidates.")

                if raw_text.startswith('```json'):
                    raw_text = raw_text[7:-3]
                elif raw_text.startswith('```'):
                    raw_text = raw_text[3:-3]
                
                raw_text = re.sub(r',\s*([\]}])', r'\1', raw_text)

                data = json.loads(raw_text)
                items = data.get('items', [])
                actual_items = sorted([(float(i.get('price', 0)), int(i.get('quantity', 0))) for i in items])
                actual_amount = float(data.get('amount_paid', 0))
                
                if actual_items != tc['gt_items'] or actual_amount != tc['gt_amount']:
                    if is_accurate == "True":
                        is_accurate = f"Fail {tc['file'][:3]}"
                    else:
                        is_accurate += f", {tc['file'][:3]}"
                    if actual_items != tc['gt_items']:
                        is_accurate += "(items)"
                    if actual_amount != tc['gt_amount']:
                        is_accurate += "(amt)"
                else:
                    correct_count += 1
                time.sleep(2)
            
            avg_time = total_time / len(test_cases)
            avg_cost = total_cost / len(test_cases)
            accuracy_pct = (correct_count / len(test_cases)) * 100
            if is_accurate == "True":
                acc_str = "100%"
            else:
                acc_str = f"{accuracy_pct:.0f}% ({is_accurate})"
            print(f"{model:<30} | {avg_time:<12.2f} | ${avg_cost:<11.6f} | {acc_str:<40}")
            time.sleep(3)
        except Exception as e:
            err = str(e).replace('\n', ' ')[:40]
            print(f"{model:<30} | {'ERROR':<12} | {'-':<12} | {err}")

run_benchmarks()
