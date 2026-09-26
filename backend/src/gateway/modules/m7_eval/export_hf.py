from __future__ import annotations

import json
from datetime import date
from pathlib import Path

DATASHEET_TEMPLATE = """# Code-Mixed (Hinglish) Benchmark — Datasheet

**Source:** synthetic seed expanded from {n_seed} Hinglish prompts across 5 task categories.
**Benchmark size:** {n_bench} rows
**Calibration size:** {n_cal}
**Pricing date:** {pricing_date}
**Collection method:** synthetic generation from curated Hinglish templates + heuristic fluff injection (clearly labelled `is_synthetic=true`).
**Consent:** no real user data; all rows are synthetic. Real-user pilot data will be consented and anonymized separately.
**Grading protocol:** reference answers are templated checkable answers; task_success/BLEU/ROUGE-L are lexical similarity proxies, NOT task accuracy (see METRIC_NOTE).
**Known limitations:** synthetic distribution does not replace real WhatsApp/support traffic; tokenizer numbers are whitespace/heuristic when HF tokenizers not installed.
**License:** CC-BY-4.0 recommended for release.

## Usage
```python
# local JSONL
import json
rows = [json.loads(l) for l in open("benchmark.jsonl")]
# HF datasets (when installed):
# from datasets import load_dataset
# ds = load_dataset("json", data_files="benchmark.jsonl")["train"]
```
"""


def export_benchmark(
    benchmark: Path,
    output_dir: Path,
    seed_file: Path | None = None,
    calibration_file: Path | None = None,
    pricing_date: str = "2026-08-28",
) -> Path:
    """Export benchmark + seed as a HF-datasets-ready folder.

    Produces:
      output_dir/data/benchmark.jsonl
      output_dir/data/seed_hinglish.jsonl
      output_dir/README.md  (datasheet)
      output_dir/dataset_info.json
    Returns the output directory path.
    """
    bench_n = 0
    if benchmark.exists():
        bench_n = sum(1 for line in benchmark.read_text(encoding="utf-8").splitlines() if line.strip())
    seed_n = 0
    if seed_file and seed_file.exists():
        seed_n = sum(1 for line in seed_file.read_text(encoding="utf-8").splitlines() if line.strip())
    cal_n = 0
    if calibration_file and calibration_file.exists():
        cal_n = sum(1 for line in calibration_file.read_text(encoding="utf-8").splitlines() if line.strip())

    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    if benchmark.exists():
        (data_dir / "benchmark.jsonl").write_text(benchmark.read_text(encoding="utf-8"), encoding="utf-8")
    if seed_file and seed_file.exists():
        (data_dir / "seed_hinglish.jsonl").write_text(seed_file.read_text(encoding="utf-8"), encoding="utf-8")

    today = date.today().isoformat()
    readme = DATASHEET_TEMPLATE.format(n_seed=seed_n, n_bench=bench_n, n_cal=cal_n, pricing_date=pricing_date)
    readme += f"\nExported: {today}\n"
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    info = {
        "description": "Synthetic Hinglish code-mixed benchmark for compression/routing evaluation",
        "citation": "Code-Mixed Gateway benchmark (synthetic seed)",
        "homepage": "",
        "license": "CC-BY-4.0",
        "features": {
            "id": {"dtype": "string"},
            "original": {"dtype": "string"},
            "compressed": {"dtype": "string"},
            "reference_answer": {"dtype": "string"},
            "protected": {"dtype": "list", "feature": {"dtype": "string"}},
            "is_synthetic": {"dtype": "bool"},
        },
        "splits": {"train": {"name": "train", "num_examples": bench_n}},
        "download_size": 0,
        "dataset_size": 0,
    }
    (output_dir / "dataset_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return output_dir
