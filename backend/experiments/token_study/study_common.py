from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

STUDY_DIR = Path(__file__).resolve().parent
BACKEND_DIR = STUDY_DIR.parents[1]
RESULTS_DIR = BACKEND_DIR / "results"


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_dotenv() -> None:
    """Load backend/.env (KEY=VALUE lines) into os.environ without overwriting.

    Keeps provider keys out of committed config while making every experiment
    process see them. Never prints values."""
    env_path = BACKEND_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = val


load_dotenv()


def groq_keys() -> list[str]:
    """All configured provider keys (comma-separated GROQ_API_KEY or
    GROQ_API_KEY2/3/...). Values are never logged; only the count is reported."""
    keys: list[str] = []
    raw = os.environ.get("GROQ_API_KEY", "")
    keys.extend(k.strip().strip("'\"") for k in raw.split(",") if k.strip())
    i = 2
    while f"GROQ_API_KEY{i}" in os.environ:
        val = os.environ[f"GROQ_API_KEY{i}"].strip().strip("'\"")
        if val:
            keys.append(val)
        i += 1
    seen, uniq = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    return uniq


def load_config(path: str | Path | None = None) -> dict:
    cfg_path = Path(path) if path else STUDY_DIR / "config.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"missing study config: {cfg_path} (copy config.example.yaml)")
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8"))


def config_sha256(cfg: dict) -> str:
    canon = json.dumps(cfg, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=BACKEND_DIR.parent, timeout=15
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def pair_id(source_name: str, dialogue_id: str, turn_index: int, template_version: str) -> str:
    raw = f"{source_name}|{dialogue_id}|{turn_index}|{template_version}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def pip_freeze() -> list[str]:
    try:
        out = subprocess.run(
            ["python", "-m", "pip", "freeze"], capture_output=True, text=True, timeout=60
        )
        if out.returncode == 0:
            return sorted(out.stdout.splitlines())
    except Exception:
        pass
    return []


def build_manifest(cfg: dict, run_id: str, extra: dict | None = None) -> dict:
    manifest = {
        "run_id": run_id,
        "created_utc": utcnow(),
        "git_sha": git_sha(),
        "config_sha256": config_sha256(cfg),
        "config": cfg,
        "packages": pip_freeze(),
        "extra": extra or {},
    }
    return manifest


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


OFFICIAL_URL_ALLOWLIST = (
    "https://precog.iiit.ac.in/projects/codemix_project/",
    # PRESTO v1 (CC BY 4.0): download URL taken verbatim from the official
    # release repo google-research-datasets/presto README (owner-decided pivot,
    # DECISIONS.md §3). License: https://creativecommons.org/licenses/by/4.0/
    "https://storage.googleapis.com/gresearch/presto/presto_v1.zip",
)


def assert_official_url(url: str) -> None:
    if url not in OFFICIAL_URL_ALLOWLIST:
        raise ValueError(
            f"refusing non-allowlisted dataset URL: {url!r}. "
            f"Add the verified official release to OFFICIAL_URL_ALLOWLIST with license evidence first."
        )


def assert_no_demo_contamination(run_dir: Path) -> None:
    """research_mode guard: experiment outputs must never mix with demo data."""
    offenders = []
    for name in ("pilot.sqlite", "pilot.sqlite-shm", "pilot.sqlite-wal",
                 "benchmark.jsonl", "calibration.jsonl", "seed_hinglish.jsonl"):
        if (run_dir / name).exists():
            offenders.append(name)
    if offenders:
        raise ValueError(f"demo data inside experiment run dir {run_dir}: {offenders}")
