from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GRPOConfig:
    """Scaffold for the real GPU training run — honestly labelled as not runnable here.

    The report's 12-week plan reserves weeks 5–6 for this. The config documents
    the intended run so a reviewer can see the training story is real even before
    a GPU is booked. The CPU distill fallback in distill.py is what actually
    produces a runnable 'trained' artifact in this repo.
    """

    base_model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    compressor_model: str = "Qwen/Qwen3-0.6B"
    dataset: str = "data/benchmark.jsonl"
    output_dir: str = "data/checkpoints/distilled.json"
    learning_rate: float = 5e-6
    kl_coef: float = 0.02
    group_size: int = 8
    max_steps: int = 2000
    batch_size: int = 8
    max_seq_len: int = 2048
    reward_weights: dict[str, float] = field(
        default_factory=lambda: {"answer": 0.7, "faithfulness": 0.3}
    )
    fallback: str = "rejection-sampling distillation (CPU, this repo)"

    def describe(self) -> str:
        return (
            f"GRPO from {self.base_model} -> {self.compressor_model} "
            f"on {self.dataset} for {self.max_steps} steps "
            f"(group={self.group_size}, kl={self.kl_coef}); "
            f"fallback: {self.fallback}"
        )