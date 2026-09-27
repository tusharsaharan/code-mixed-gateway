"""Build self-contained GPU notebooks for LLM-teacher bootstrap.

Reads the current source files and embeds them as %%writefile cells so the
notebooks run without pushing uncommitted work to GitHub.

Usage:
    python scripts/build_colab_notebook.py [--platform colab|kaggle|all]
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

#: Per-platform roots, workdirs, and artifact homes.
PLATFORMS = {
    "colab": {"root": "/content", "repo": "/content/code-mixed-gateway"},
    "kaggle": {"root": "/kaggle/working", "repo": "/kaggle/working/code-mixed-gateway"},
}


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


def build(platform: str) -> dict:
    repo_root = BACKEND_ROOT.parent
    home = PLATFORMS[platform]["repo"]
    if platform == "kaggle":
        header = (
            "# CRF Hinglish Compressor — GPU LLM-Teacher Bootstrap (Kaggle)\n"
            "\n"
            "**Before running:** Settings (right sidebar) → Accelerator: **GPU T4 x2** → "
            "Internet: **ON** (needed for the model download).\n"
            "\n"
            "Pipeline: clone repo → embed CRF sources → generate 5K prompts →\n"
            "deterministic baseline (fast) → LLM-teacher labels on GPU → train both CRFs →\n"
            "compare on held-out slice. Artifacts persist in the working dir and are\n"
            "downloadable from the Output panel. Set `HF_MODEL` below "
            "(default needs no access token)."
        )
    else:
        header = (
            "# CRF Hinglish Compressor — GPU LLM-Teacher Bootstrap\n"
            "\n"
            "**Before running:** Runtime → Change runtime type → **T4 GPU**.\n"
            "\n"
            "Pipeline: clone repo → embed uncommitted CRF sources → generate 5K prompts →\n"
            "deterministic baseline (fast) → LLM-teacher labels on GPU → train both CRFs →\n"
            "compare on held-out slice → download winner artifacts.\n"
            "Set `HF_MODEL` below (default needs no access token)."
        )
    cells: list[dict] = [
        md(header),
        code(
            "!nvidia-smi --query-gpu=name,memory.total --format=csv\n"
            "import torch\n"
            "assert torch.cuda.is_available(), 'Enable a GPU accelerator first (see header)'\n"
            "print('cuda:', torch.cuda.get_device_name(0))"
        ),
        code(
            f"!rm -rf {home}\n"
            f"!git clone --depth 1 {REPO_URL} {home}\n"
            "!pip -q install sklearn-crfsuite scikit-learn transformers accelerate bitsandbytes sentence-transformers\n"
            "print('deps ok')"
        ),
    ]
    for rel in EMBED_FILES:
        content = (repo_root / rel).read_text(encoding="utf-8")
        dest = home + "/" + rel
        cells.append(code(f"%%writefile {dest}\n{content}"))
    cells += [
        code(
            f"%cd {home}/backend\n"
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
            "# LLM teacher on GPU, 4-bit quantized (fits fully on a T4, no CPU offload).\n"
            "# Expect well under an hour for 5K. --resume continues after a crash;\n"
            "# results flush to disk after every batch, so nothing is ever lost.\n"
            "HF_MODEL = 'mistralai/Mistral-7B-Instruct-v0.1'  # or 'Qwen/Qwen2.5-7B-Instruct' (needs token + license)\n"
            "HF_BATCH = 4\n"
            "!python scripts/bootstrap_crf_data.py --prompts data/training/prompts.jsonl "
            "--out data/training/bootstrap_llm.jsonl --hf-model \"$HF_MODEL\" --hf-batch \"$HF_BATCH\" --resume\n"
            "!python scripts/train_crf.py --data data/training/bootstrap_llm.jsonl "
            "--model data/models/crf_llm.pkl --idf data/tfidf/hinglish_idf.json"
        ),
    ]
    if platform == "kaggle":
        cells += [
            code(
                "# Head-to-head on a held-out slice (seed 999, never used in training)\n"
                "!python scripts/compare_teachers.py --models det=data/models/crf_det.pkl llm=data/models/crf_llm.pkl "
                "--limit 500 --seed 999 | tee data/training/teacher_comparison.json"
            ),
            code(
                "# Artifacts persist in the working dir -- download them from the\n"
                "# Output panel (right side, under this notebook):\n"
                "!ls -la data/models/crf_llm.pkl data/training/bootstrap_llm.jsonl "
                "data/training/teacher_comparison.json\n"
                "print('Download the three files above from the Output panel.')"
            ),
        ]
    else:
        cells += [
            code(
                "# Back up labels to Google Drive NOW -- /content is wiped if the runtime dies.\n"
                "# Run this cell the moment bootstrap finishes, before anything else.\n"
                "from google.colab import drive\n"
                "drive.mount('/content/drive')\n"
                "!mkdir -p /content/drive/MyDrive/crf_bootstrap && "
                "cp data/training/bootstrap_llm.jsonl data/training/prompts.jsonl "
                "data/tfidf/hinglish_idf.json /content/drive/MyDrive/crf_bootstrap/ && "
                "ls -la /content/drive/MyDrive/crf_bootstrap/\n"
                "print('labels backed up to Drive/crf_bootstrap/')"
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
    metadata: dict = {
        "accelerator": "GPU",
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    }
    if platform == "kaggle":
        metadata["kaggle"] = {
            "accelerator": "GPU",
            "internet": True,
            "language": "python",
        }
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": metadata,
        "cells": cells,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", choices=["colab", "kaggle", "all"], default="all")
    args = ap.parse_args()
    repo_root = BACKEND_ROOT.parent
    platforms = ["colab", "kaggle"] if args.platform == "all" else [args.platform]
    out_map = {"colab": "backend/colab/crf_teacher_colab.ipynb", "kaggle": "backend/kaggle/crf_teacher_kaggle.ipynb"}
    for plat in platforms:
        out = repo_root / out_map[plat]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(build(plat), indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
