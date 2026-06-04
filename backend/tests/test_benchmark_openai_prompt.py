import ast
from pathlib import Path


BENCHMARK_OPENAI_PATH = Path(__file__).resolve().parents[1] / "benchmark_openai.py"


def _get_string_constant(source: str, name: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    raise AssertionError(f"{name} string constant not found")


def _get_class_annotations(source: str, name: str) -> set[str]:
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return {
                statement.target.id
                for statement in node.body
                if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
            }
    raise AssertionError(f"{name} class not found")


def test_benchmark_openai_prompt_uses_adapted_receipt_parsing_rules():
    source = BENCHMARK_OPENAI_PATH.read_text()
    prompt = _get_string_constant(source, "BILL_OCR_PROMPT")

    assert "highly precise receipt-parsing engine" in prompt
    assert "price of a single unit" in prompt
    assert "Strip all currency symbols" in prompt
    assert "Do NOT extract line-item modifiers" in prompt
    assert "Do NOT include negative price items" in prompt
    assert "tax_amount / subtotal" in prompt
    assert "tip_amount / subtotal" in prompt
    assert "discount_amount" in prompt
    assert "absolute final grand total" in prompt


def test_benchmark_openai_prompt_matches_local_schema_and_stays_independent():
    source = BENCHMARK_OPENAI_PATH.read_text()
    annotations = _get_class_annotations(source, "OCRBill")

    assert annotations == {"items", "tax_rate", "service_charge", "discount_amount", "amount_paid"}
    assert "from app." not in source
    assert "import app." not in source
