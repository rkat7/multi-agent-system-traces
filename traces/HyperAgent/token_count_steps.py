import json
import os
from pathlib import Path
from typing import Any, Dict, List

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parent
MANIFEST_DIR = ROOT / "manifest"
TOKENS_DIR = ROOT / "token-counts"

MODEL_ID = os.environ.get("TOKENIZER_MODEL", "mistralai/Mistral-7B-v0.1")
HF_TOKEN = os.environ.get("HF_TOKEN")


def to_string(data: Any) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, (list, dict)):
        return json.dumps(data, ensure_ascii=False)
    return str(data)


def count_tokens(tokenizer, text: str) -> int:
    return len(tokenizer.encode(text, add_special_tokens=True))


def load_tokenizer():
    kwargs = {}
    if HF_TOKEN:
        kwargs["token"] = HF_TOKEN
    return AutoTokenizer.from_pretrained(MODEL_ID, **kwargs)


def process_run(tokenizer, manifest_path: Path) -> List[Dict[str, Any]]:
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    results: List[Dict[str, Any]] = []
    for entry in entries:
        input_path = ROOT / entry["input_file"]
        output_path = ROOT / entry["output_file"]
        input_text = input_path.read_text(encoding="utf-8", errors="ignore")
        output_text = output_path.read_text(encoding="utf-8", errors="ignore")

        input_count = count_tokens(tokenizer, to_string(input_text))
        output_count = count_tokens(tokenizer, to_string(output_text))

        results.append(
            {
                "step_id": entry["step_id"],
                "source": entry["source"],
                "origin": entry["origin"],
                "input_file": entry["input_file"],
                "output_file": entry["output_file"],
                "input_tokens": input_count,
                "output_tokens": output_count,
                "total_tokens": input_count + output_count,
            }
        )
    return results


def main():
    TOKENS_DIR.mkdir(exist_ok=True)
    tokenizer = load_tokenizer()

    summary: Dict[str, Dict[str, Any]] = {}

    for manifest_file in sorted(MANIFEST_DIR.glob("*.json")):
        run_id = manifest_file.stem
        run_results = process_run(tokenizer, manifest_file)
        out_path = TOKENS_DIR / f"{run_id}.json"
        out_path.write_text(json.dumps(run_results, indent=2), encoding="utf-8")

        total_input = sum(r["input_tokens"] for r in run_results)
        total_output = sum(r["output_tokens"] for r in run_results)
        summary[run_id] = {
            "steps": len(run_results),
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "detail_file": str(out_path.relative_to(ROOT)),
        }

    summary_path = TOKENS_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
