"""Build the self-contained Colab notebook for GPU LLM-teacher bootstrap.

Reads the current source files and embeds them as %%writefile cells so the
notebook runs without pushing uncommitted work to GitHub.

Usage:
    python scripts/build_colab_notebook.py [--out backend/colab/crf_teacher_colab.ipynb]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

#: (repo-relative path, colab destination relative to repo root)
EMBED_FILES = [
    "backend/src/gateway/modules/m2_compressor/phonetic.py",
    "backend/src/gateway/modules/m2_compressor/heuristic_passes.py",
    "backend/src/gateway/modules/m2_compressor/tfidf.py",
    "backend/src/gateway/modules/m2_compressor/crf_tagger.py",
    "backend/src/gateway/modules/m2_compressor/linguistic.py",
    "backend/scripts/generate_hinglish_prompts.py",
    "backend/scripts/bootstrap_crf_data.py",
    "backend/scripts/build_tfidf.py",
    "backend/scripts/train_crf.py",
    "backend/scripts/compare_teachers.py",
]

REPO_URL = "https://github.com/tusharsaharan/code-mixed-gateway.git"


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def build() -> dict:
    repo_root = BACKEND_ROOT.parent
    cells: list[dict] = [
        md(
            "# CRF Hinglish Compressor — GPU LLM-Teacher Bootstrap\n"
            "\n"
            "**Before running:** Runtime → Change runtime type → **T4 GPU**.\n"
            "\n"
            "Pipeline: clone repo → embed uncommitted CRF sources → generate 5K prompts →\n"
            "deterministic baseline (fast) → LLM-teacher labels on GPU → train both CRFs →\n"
            "compare on held-out slice → download winner artifacts.\n"
            "Set `HF_MODEL` below (default needs no access token)."
        ),
        code(
            "!nvidia-smi --query-gpu=name,memory.total --format=csv\n"
            "import torch\n"
            "assert torch.cuda.is_available(), 'Enable a GPU runtime first (Runtime → Change runtime type → T4 GPU)'\n"
            "print('cuda:', torch.cuda.get_device_name(0))"
        ),
        code(
            f"!rm -rf /content/code-mixed-gateway\n"
            f"!git clone --depth 1 {REPO_URL} /content/code-mixed-gateway\n"
            "!pip -q install sklearn-crfsuite scikit-learn transformers accelerate sentence-transformers\n"
            "print('deps ok')"
        ),
    ]
    for rel in EMBED_FILES:
        content = (repo_root / rel).read_text(encoding="utf-8")
        dest = "/content/code-mixed-gateway/" + rel
        cells.append(code(f"%%writefile {dest}\n{content}"))
    cells += [
        code(
            "%cd /content/code-mixed-gateway/backend\n"
            "!python scripts/generate_hinglish_prompts.py --n 5000 --seed 7 --variants 2 \\\n"
            "  --out data/training/prompts.jsonl\n"
            "!python scripts/build_tfidf.py --prompts data/training/prompts.jsonl --out data/tfidf/hinglish_idf.json"
        ),
        code(
            "# Deterministic baseline (CPU, ~1 min)\n"
            "!python scripts/bootstrap_crf_data.py --prompts data/training/prompts.jsonl "
            "--out data/training/bootstrap_det.jsonl --no-llm\n"
            "!python scripts/train_crf.py --data data/training/bootstrap_det.jsonl "
            "--model data/models/crf_det.pkl --idf data/tfidf/hinglish_idf.json"
        ),
        code(
            "# LLM teacher on GPU. --resume makes reruns continue where a crash stopped\n"
            "# (results flush to disk after every batch, so nothing is ever lost).\n"
            "HF_MODEL = 'mistralai/Mistral-7B-Instruct-v0.1'  # or 'Qwen/Qwen2.5-7B-Instruct' (needs token + license)\n"
            "HF_BATCH = 8\n"
            "!python scripts/bootstrap_crf_data.py --prompts data/training/prompts.jsonl "
            "--out data/training/bootstrap_llm.jsonl --hf-model \"$HF_MODEL\" --hf-batch \"$HF_BATCH\" --resume\n"
            "!python scripts/train_crf.py --data data/training/bootstrap_llm.jsonl "
            "--model data/models/crf_llm.pkl --idf data/tfidf/hinglish_idf.json"
        ),
        code(
            "# Head-to-head on a held-out slice (seed 999, never used in training)\n"
            "!python scripts/compare_teachers.py --models det=data/models/crf_det.pkl llm=data/models/crf_llm.pkl "
            "--limit 500 --seed 999 | tee data/training/teacher_comparison.json"
        ),
        code(
            "import os\n"
            "from google.colab import files\n"
            "wanted = {\n"
            "    'data/models/crf_llm.pkl': 'train cell (train_crf.py on bootstrap_llm.jsonl)',\n"
            "    'data/training/bootstrap_llm.jsonl': 'HF bootstrap cell (re-run it: --resume continues)',\n"
            "    'data/training/teacher_comparison.json': 'compare cell',\n"
            "}\n"
            "for path, rerun in wanted.items():\n"
            "    if os.path.exists(path):\n"
            "        files.download(path)\n"
            "    else:\n"
            "        print(f'MISSING {path} -> re-run the {rerun}')\n"
            "print('Copy crf_llm.pkl over backend/data/models/crf_compressor.pkl locally if the llm row wins.')\n"
            "print('Then re-run: pytest tests/test_linguistic_* tests/test_m2.py tests/test_lexicon.py')"
        ),
    ]
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "accelerator": "GPU",
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        },
        "cells": cells,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="backend/colab/crf_teacher_colab.ipynb")
    args = ap.parse_args()
    repo_root = BACKEND_ROOT.parent
    out = Path(args.out)
    if not out.is_absolute():
        out = repo_root / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(), indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} ({len(EMBED_FILES)} embedded files)")


if __name__ == "__main__":
    main()
