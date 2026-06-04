import time
import json
import re
from pathlib import Path
import litellm
import os
import base64
from pydantic import BaseModel

litellm.drop_params = True

from dotenv import load_dotenv
load_dotenv()

API_KEY = os.environ.get('LITELLM_API_KEY')

pricing = {
    'gpt-4o': {'in': 2.50, 'out': 10.00},
    'gpt-4o-mini': {'in': 0.15, 'out': 0.60},
    'gpt-5.4': {'in': 2.50, 'out': 15.00},
}

openai_models = [
    'gpt-4o',
    'gpt-4o-mini',
    'gpt-5.4',
]

# Model-specific configurations for OpenAI models
model_configs = {
    'gpt-5.4': {
        'reasoning_effort': 'low',
    }
}

print(f"OpenAI models to benchmark: {openai_models}")

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

class Item(BaseModel):
    name: str
    price: float
    quantity: int

class OCRBill(BaseModel):
    items: list[Item]
    tax_rate: float
    service_charge: float
    amount_paid: float


OPENAI_RESPONSE_FORMAT = OCRBill

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
    os.environ['OPENAI_API_KEY'] = API_KEY

    for model in openai_models:
        try:
            total_time = 0
            total_cost = 0
            is_accurate = "True"
            correct_count = 0
            
            for tc in test_cases:
                file_path = Path(tc['file'])
                if not file_path.exists():
                    file_path = Path(__file__).parent / tc['file']
                if not file_path.exists():
                    file_path = Path(__file__).parent.parent / tc['file']
                image_bytes = file_path.read_bytes()
                b64_image = base64.b64encode(image_bytes).decode('utf-8')
                
                openai_messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": BILL_OCR_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64_image}"
                                }
                            }
                        ]
                    }
                ]
                
                start = time.time()
                for attempt in range(3):
                    try:
                        litellm_api_base = os.environ.get('LITELLM_API_BASE')
                        api_base = f"{litellm_api_base.rstrip('/')}/openai" if litellm_api_base else None

                        response_kwargs = {
                            'model': model,
                            'messages': openai_messages,
                            'api_base': f"{api_base}/v1" if api_base else None,
                        }

                        if not model.startswith('o'):
                            response_kwargs['response_format'] = OPENAI_RESPONSE_FORMAT

                        config_opts = model_configs.get(model, {})
                        if 'reasoning_effort' in config_opts:
                            response_kwargs['reasoning_effort'] = config_opts['reasoning_effort']

                        response = litellm.completion(**response_kwargs)
                        break
                    except Exception as e:
                        if attempt == 2:
                            raise e
                        time.sleep(5)
                elapsed = time.time() - start
                total_time += elapsed
                
                in_tokens = response.usage.prompt_tokens if response.usage else 0
                out_tokens = response.usage.completion_tokens if response.usage else 0
                cost = (in_tokens * pricing[model]['in'] / 1e6) + (out_tokens * pricing[model]['out'] / 1e6)
                total_cost += cost
                
                raw_content = response.choices[0].message.content
                if raw_content.startswith('```json'):
                    raw_content = raw_content[7:-3]
                elif raw_content.startswith('```'):
                    raw_content = raw_content[3:-3]
                
                raw_content = re.sub(r',\s*([\]}])', r'\1', raw_content)
                    
                data = json.loads(raw_content)
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
