from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict

import numpy as np

from .study_common import BACKEND_DIR, assert_no_demo_contamination, load_config


def load_records(run_dir, split: str) -> list[dict]:
    comp = { (json.loads(line)["pair_id"], json.loads(line)["arm"], json.loads(line)["requested_kept_rate"]): json.loads(line)
             for line in (run_dir / f"compression_{split}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip() }
    ans = [json.loads(line) for line in (run_dir / f"answers_{split}.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    struct_path = run_dir / f"structured_scores_{split}.jsonl"
    struct = {}
    if struct_path.exists():
        for line in struct_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                struct[(r["pair_id"], r["arm"], r["requested_kept_rate"])] = r
    rows = []
    for a in ans:
        key = (a["pair_id"], a["arm"], a["requested_kept_rate"])
        rows.append({"answer": a, "compression": comp.get(key), "struct": struct.get(key)})
    return rows


def paired_bootstrap(
    groups: dict[str, list[float]], stat: callable, seed: int, replicates: int
) -> tuple[float, float]:
    """Clustered paired bootstrap over dialogue groups. `stat` maps a resampled
    flat list of (base, variant) pairs to the scalar of interest."""
    rng = np.random.default_rng(seed)
    ids = sorted(groups)
    ests = []
    for _ in range(replicates):
        pick = rng.choice(ids, size=len(ids), replace=True)
        flat = [p for i in pick for p in groups[i]]
        ests.append(stat(flat))
    lo, hi = np.percentile(ests, [2.5, 97.5])
    return round(float(lo), 6), round(float(hi), 6)


def choose_safe_rate(rows: list[dict]) -> dict:
    eligible = [x for x in rows if (
        x["delta_quality_ci_low"] >= -0.05
        and x["span_recall_ci_low"] >= 0.995
        and x["failure_rate_delta"] <= 0.02
        and x["end_to_end_cost_saving"] > 0.05
    )]
    if not eligible:
        return {"status": "no_safe_rate"}
    best = sorted(eligible, key=lambda x: (
        x["median_achieved_token_saving"], x["delta_quality_ci_low"],
        x["end_to_end_cost_saving"], -x["p95_latency_ms"],
    ), reverse=True)[0]
    return {"status": "safe", **best}


def analyze_run(cfg: dict, run_id: str, split: str) -> dict:
    run_dir = BACKEND_DIR / "results" / run_id
    assert_no_demo_contamination(run_dir)
    records = load_records(run_dir, split)
    seed = int(cfg["study"]["run_seed"])
    reps = int(cfg["study"]["bootstrap_replicates"])

    # 1:1 join check on pair_id between A0 and each variant
    by_arm_rate: dict[tuple[str, float], dict[str, dict]] = defaultdict(dict)
    lost, multiple = 0, 0
    for r in records:
        c, a = r["compression"], r["answer"]
        if c is None:
            lost += 1
            continue
        key = (a["arm"], a["requested_kept_rate"])
        if a["pair_id"] in by_arm_rate[key]:
            multiple += 1
        by_arm_rate[key][a["pair_id"]] = r

    ref = by_arm_rate.get(("none", 1.0), {})
    main_rows: list[dict] = []
    failures: list[dict] = []
    for (arm, rate), members in sorted(by_arm_rate.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        # join with A0 on pair_id
        pairs = [(m, ref.get(pid)) for pid, m in members.items()]
        pairs = [(m, b) for m, b in pairs if b is not None]
        # dialogue clusters for the paired bootstrap
        clust: dict[str, list] = defaultdict(list)
        for m, b in pairs:
            mc = m["compression"] or {}
            clust[mc.get("dialogue_id_hash", m["answer"]["pair_id"])].append((m, b))

        def q(m, field, default=0.0):
            s = (m.get("struct") or {})
            return s.get(field, default)

        scores = [q(m, "em") for m, _ in pairs]
        deltas = [q(m, "em") - q(b, "em") for m, b in pairs if b is not None] if arm != "none" else [0.0] * len(pairs)
        savings = [1 - (m["compression"] or {}).get("achieved_kept_ratio", 1.0) for m, _ in pairs]
        recalls = [(m["compression"] or {}).get("span_recall", 1.0) for m, _ in pairs]
        statuses = [(m["compression"] or {}).get("compression_status", "ok") for m, _ in pairs]
        fail_rate = sum(1 for s in statuses if s != "ok") / max(1, len(statuses))

        dci = paired_bootstrap(clust, lambda f: float(np.mean([q(m, "em") - q(b, "em") for m, b in f])) if f and f[0][1] is not None else 0.0, seed, reps) if arm != "none" else (0.0, 0.0)
        sci = paired_bootstrap(clust, lambda f: float(np.mean([1 - (m["compression"] or {}).get("achieved_kept_ratio", 1.0) for m, _ in f])), seed + 1, reps)
        rci = paired_bootstrap(clust, lambda f: float(np.mean([(m["compression"] or {}).get("span_recall", 1.0) for m, _ in f])), seed + 2, reps)

        lat = sorted((m["answer"] or {}).get("latency_ms") or 0 for m, _ in pairs)
        costs = [float((m["answer"] or {}).get("answer_cost_usd") or 0) for m, _ in pairs]
        base_costs = [float((b["answer"] or {}).get("answer_cost_usd") or 0) for _, b in pairs if b is not None]
        cost_save = 1 - (float(np.mean(costs)) / float(np.mean(base_costs))) if base_costs and float(np.mean(base_costs)) > 0 else 0.0

        main_rows.append({
            "arm": arm, "requested_rate": rate, "n": len(pairs),
            "median_achieved_saving": round(float(np.median(savings)) if savings else 0.0, 6),
            "mean_score": round(float(np.mean(scores)) if scores else 0.0, 6),
            "delta_quality": round(float(np.mean(deltas)) if deltas else 0.0, 6),
            "delta_quality_ci_low": dci[0], "delta_quality_ci_high": dci[1],
            "span_recall": round(float(np.mean(recalls)) if recalls else 1.0, 6),
            "span_recall_ci_low": rci[0], "span_recall_ci_high": rci[1],
            "cost_saving": round(cost_save, 6),
            "saving_ci_low": sci[0], "saving_ci_high": sci[1],
            "p50_latency_ms": round(float(lat[len(lat) // 2]) if lat else 0.0, 1),
            "p95_latency_ms": round(float(lat[int(len(lat) * 0.95)]) if lat else 0.0, 1),
            "failure_rate": round(fail_rate, 6),
            "failure_rate_delta": 0.0,  # filled vs A0 below
            "end_to_end_cost_saving": round(cost_save, 6),
            "median_achieved_token_saving": round(float(np.median(savings)) if savings else 0.0, 6),
        })
        for m, _ in pairs:
            mc = m["compression"] or {}
            if mc.get("compression_status", "ok") != "ok" or (m["answer"] or {}).get("status") != "ok":
                failures.append({
                    "pair_id": m["answer"]["pair_id"], "arm": arm, "requested_rate": rate,
                    "compression_status": mc.get("compression_status"),
                    "compression_error": mc.get("error_type"),
                    "answer_status": (m["answer"] or {}).get("status"),
                })

    a0_fail = next((r["failure_rate"] for r in main_rows if r["arm"] == "none"), 0.0)
    for r in main_rows:
        r["failure_rate_delta"] = round(r["failure_rate"] - a0_fail, 6)

    safe = choose_safe_rate([{**r, "p95_latency_ms": r["p95_latency_ms"]} for r in main_rows if r["arm"] != "none"])
    summary = {
        "run_id": run_id, "split": split, "n_pairs_joined": sum(r["n"] for r in main_rows),
        "join_lost": lost, "join_multiple": multiple,
        "bootstrap": {"replicates": reps, "seed": seed, "cluster": "dialogue"},
        "main_table": main_rows,
        "failure_count": len(failures),
        "safe_rate": safe,
    }
    (run_dir / f"summary_{split}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (run_dir / f"main_table_{split}.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(main_rows[0].keys()) if main_rows else ["arm"])
        w.writeheader()
        w.writerows(main_rows)
    with (run_dir / f"failure_table_{split}.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["pair_id", "arm", "requested_rate", "compression_status", "compression_error", "answer_status"])
        w.writeheader()
        w.writerows(failures)
    print(f"analyze {split}: {len(main_rows)} arm×rate rows, {len(failures)} failures -> {run_dir}")
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--split", default="smoke")
    args = ap.parse_args()
    analyze_run(load_config(args.config), args.run_id, args.split)


if __name__ == "__main__":
    main()
