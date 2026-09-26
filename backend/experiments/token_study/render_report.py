from __future__ import annotations

import argparse
import csv
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .study_common import BACKEND_DIR, load_config


def _fig(path, title, xlabel, ylabel, series, ref_point=None):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for label, xs, ys, lo, hi in series:
        ax.errorbar(xs, ys, yerr=[ys[i] - lo[i] for i in range(len(ys))], fmt="o-", capsize=3, label=label)
        for x, y in zip(xs, ys):
            ax.annotate(f"{y:.2f}", (x, y), fontsize=7)
    if ref_point:
        ax.scatter([ref_point[0]], [ref_point[1]], c="black", marker="x", s=80, label="A0 uncompressed")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def render(cfg: dict, run_id: str, split: str) -> dict:
    run_dir = BACKEND_DIR / "results" / run_id
    summary = json.loads((run_dir / f"summary_{split}.json").read_text(encoding="utf-8"))
    rows = summary["main_table"]
    by_arm: dict[str, list[dict]] = {}
    for r in rows:
        by_arm.setdefault(r["arm"], []).append(r)
    for arm_rows in by_arm.values():
        arm_rows.sort(key=lambda r: r["requested_rate"], reverse=True)

    fig_dir = run_dir / "figures"
    fig_dir.mkdir(exist_ok=True)
    a0 = next((r for r in rows if r["arm"] == "none"), None)
    ref = (0.0, a0["mean_score"]) if a0 else None
    series = []
    for arm, arm_rows in sorted(by_arm.items()):
        if arm == "none":
            continue
        xs = [r["median_achieved_saving"] for r in arm_rows]
        ys = [r["mean_score"] for r in arm_rows]
        lo = [r["delta_quality_ci_low"] + r["mean_score"] - r["delta_quality"] for r in arm_rows]
        hi = [r["delta_quality_ci_high"] + r["mean_score"] - r["delta_quality"] for r in arm_rows]
        series.append((arm, xs, ys, lo, hi))
    figs = {}
    if series:
        p1 = fig_dir / f"quality_vs_saving_{split}.png"
        _fig(p1, "Quality vs achieved token saving (95% CI)", "median token saving",
             "mean structured EM", series, ref)
        figs["quality_vs_saving"] = p1.name
        pseries = []
        for arm, arm_rows in sorted(by_arm.items()):
            xs = [round(1 - r["cost_saving"], 4) for r in arm_rows]
            ys = [r["mean_score"] for r in arm_rows]
            pseries.append((arm, xs, ys, list(ys), list(ys)))
        p2 = fig_dir / f"pareto_{split}.png"
        ref_cost = (round(1 - a0["cost_saving"], 4), a0["mean_score"]) if a0 else None
        _fig(p2, "Relative cost vs retained quality (measured points only)",
             "relative end-to-end cost (A0 = 1.0)", "mean structured EM", pseries, ref_cost)
        figs["pareto"] = p2.name

    lines = [
        f"# Results — run {run_id} (split {split})",
        "",
        f"N pairs joined: {summary['n_pairs_joined']}; bootstrap: "
        f"{summary['bootstrap']['replicates']} replicates, seed {summary['bootstrap']['seed']}, "
        f"cluster={summary['bootstrap']['cluster']}.",
        "",
        "## Main table",
        "",
        "| arm | rate | n | median saving | score | delta vs A0 [95% CI] | span recall | cost saving | p50/p95 ms | failures |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['arm']} | {r['requested_rate']} | {r['n']} | {r['median_achieved_saving']} | "
            f"{r['mean_score']} | {r['delta_quality']} [{r['delta_quality_ci_low']}, {r['delta_quality_ci_high']}] | "
            f"{r['span_recall']} | {r['cost_saving']} | {r['p50_latency_ms']}/{r['p95_latency_ms']} | {r['failure_rate']} |"
        )
    safe = summary.get("safe_rate", {})
    lines += ["", "## Safe-rate decision",
              "", f"```json\n{json.dumps(safe, indent=2)}\n```",
              "", "## Failure counts",
              "", f"failure rows: {summary['failure_count']} (see failure_table_{split}.csv)",
              "", "## Figures", ""]
    for name, fname in figs.items():
        lines.append(f"- {name}: `figures/{fname}`")
    (run_dir / f"RESULTS_{split}.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"rendered RESULTS_{split}.md + {len(figs)} figures -> {run_dir}")
    return {"results_md": f"RESULTS_{split}.md", "figures": figs}


def render_not_run(cfg: dict, run_id: str, blocked: list[str]) -> str:
    run_dir = BACKEND_DIR / "results" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RESULTS NOT RUN",
        "",
        f"Run slot `{run_id}` was prepared but the locked test was never executed.",
        "No headline number below is a measurement. Every implementable part is complete;",
        "only the blocked external inputs below are missing.",
        "",
        "## Blocked inputs (exact)",
        "",
    ]
    for b in blocked:
        lines.append(f"- {b}")
    lines += [
        "",
        "## What is ready",
        "",
        "- `experiments/token_study/` package with gate-enforced CLIs (schemas → analyze).",
        "- Unit tests for invariants and failure categories.",
        "- G2 compressor smoke evidence (real library+checkpoint; synthetic prompts; labelled non-evidence).",
        "- `docs/research/DECISIONS.md` (frozen scope) and this run's `manifest.json`.",
        "",
        "## Unblock commands",
        "",
        "```powershell",
        "python -m experiments.token_study.run_all --split test --run-id <NEW_RUN_ID>",
        "python -m experiments.token_study.analyze --run-id <NEW_RUN_ID>",
        "python -m experiments.token_study.render_report --run-id <NEW_RUN_ID>",
        "```",
    ]
    out = run_dir / "RESULTS_NOT_RUN.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    return str(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--split", default="smoke")
    args = ap.parse_args()
    render(load_config(args.config), args.run_id, args.split)


if __name__ == "__main__":
    main()
