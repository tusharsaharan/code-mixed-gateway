"""Generate diverse Hinglish training prompts (offline, deterministic).

Usage:
    python scripts/generate_hinglish_prompts.py --n 5000 --seed 7 \\
        --out data/training/prompts.jsonl [--variants 2]

Each base prompt optionally yields spelling-variant copies via
inject_spelling_variants() to teach the CRF spelling-entropy robustness.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

# (template, domain) pairs. {x} slots are filled from small vocab lists.
TEMPLATES: list[tuple[str, str]] = [
    ("yaar {place} ka wifi bahut slow chal raha hai", "campus"),
    ("arre bhai mera {item} {problem} ho raha hai", "campus"),
    ("hello sir, mera {item} {task} hai, deadline kab hai", "campus"),
    ("namaste, hostel room {num} ka {item} kaam nahi kar raha", "campus"),
    ("suno, mera phone charge nahi ho raha, charger kharab hai", "tech"),
    ("achha toh ye error aa raha hai: {error}, kya karein", "tech"),
    ("bhai mera app baar baar crash ho raha hai, please fix karo", "tech"),
    ("matlab mera {item} update ke baad slow ho gaya hai", "tech"),
    ("mera order {num} abhi tak deliver nahi hua, status kya hai", "ecommerce"),
    ("total Rs. {num} ka payment fail ho gaya, refund kab milega", "ecommerce"),
    ("please mera {item} return karo, size galat aaya hai", "ecommerce"),
    ("kal {time} baje meeting hai, agenda mail kar do na", "general"),
    ("kya {place} ka rasta bata sakte ho, jaldi pahunchna hai", "general"),
    ("basically mujhe {item} ke liye leave application likhni hai", "general"),
    ("aur suno, {item} ka bill user@example.com par bhej do", "general"),
    # Mid-sentence fillers / politeness / auxiliaries (position diversity
    # so the CRF learns fillers are droppable anywhere, not just initially).
    ("mera wifi toh bahut slow chal raha hai yaar", "campus"),
    ("bhai suno mera {item} {problem} ho gaya hai, please help karo", "campus"),
    ("yaar tumne mera {item} dekha kya, room me nahi mil raha", "campus"),
    ("hello sir please mera {item} approve kar do, bahut urgent hai", "campus"),
    ("arre mera order wala please cancel kar do na", "ecommerce"),
    ("toh basically mujhe kal {time} baje tak {item} chahiye", "general"),
    ("matlab ye wala issue phir se aa gaya hai, please dekho", "tech"),
    ("phone toh charge ho raha hai par bahut slow hai bhai", "tech"),
    # Guard-contrast cases (distill lexicon guards into the CRF):
    # mid-sentence matlab = filler (drop) vs tech/initial matlab (keep).
    ("hostel ka wifi matlab bahut slow chal raha hai", "campus"),
    ("download matlab free version for students", "tech"),
    ("matlab ek numerical tool hai", "general"),
    # bhai vocative (drop) vs kinship/genitive (keep).
    ("bhai mera assignment submit nahi hua", "campus"),
    ("mere bhai ka phone kho gaya hai", "campus"),
    ("mera bhai kal aayega", "general"),
    # Homograph keeps: like-verb, sun-noun, you-pronoun.
    ("I like this hostel room", "general"),
    ("the sun rises in the east", "general"),
    ("can you submit the form", "campus"),
    ("you know the deadline is tomorrow", "campus"),
    # Stacked initial fillers (common in the wild: both must drop).
    ("yaar matlab mera email user@example.com par bhejo na", "general"),
    ("arre yaar mera {item} {problem} ho gaya hai", "campus"),
    ("arre bhai suno mera {item} {task} hai", "campus"),
]

SLOT_VALUES: dict[str, list[str]] = {
    "place": ["hostel", "campus", "library", "canteen", "station"],
    "item": ["assignment", "form", "phone", "laptop", "wifi", "charger", "room"],
    "problem": ["submit nahi", "slow", "kharab", "missing"],
    "task": ["bharna", "submit karna", "jama karna"],
    "error": ["index out of range", "null pointer", "timeout", "404 not found"],
    "num": ["305", "12", "2,500", "15"],
    "time": ["10", "3", "5"],
}

#: Canonical -> wild spelling variants for entropy injection.
VARIANT_MAP: dict[str, list[str]] = {
    "kar": ["kr"],
    "raha": ["rha", "raha"],
    "rahi": ["rhi"],
    "rahe": ["rhe"],
    "hai": ["h", "hai"],
    "nahi": ["nhi", "nai", "nahin"],
    "mat": ["mt"],
    "mera": ["mra"],
    "mere": ["mre"],
    "meri": ["mri"],
    "kuch": ["kch"],
    "baat": ["bt"],
    "bas": ["bs"],
    "phone": ["fone", "fon"],
    "message": ["msg"],
    "please": ["plz", "pls"],
    "because": ["bcz", "bcoz"],
    "yaar": ["yr"],
    "nahin": ["nhi", "nahi"],
}


def inject_spelling_variants(prompt: str, rng: random.Random, p: float = 0.3) -> str:
    """Randomly replace tokens with wild spellings + repeat-char emphasis."""
    out: list[str] = []
    for tok in prompt.split():
        low = tok.lower().strip(",.!?;:")
        if low in VARIANT_MAP and rng.random() < p:
            variant = rng.choice(VARIANT_MAP[low])
            # Preserve trailing punctuation of the original token.
            trail = tok[len(tok.rstrip(",.!?;:")) :] if tok.rstrip(",.!?;:") != tok else ""
            lead = tok[: len(tok) - len(tok.lstrip(",.!?;:"))] if tok.lstrip(",.!?;:") != tok else ""
            out.append(lead + variant + trail)
        elif rng.random() < 0.05 and len(tok) > 3 and tok.isalpha():
            # Emphasis elongation: "hai" -> "haai".
            out.append(tok + tok[-1])
        else:
            out.append(tok)
    return " ".join(out)


def generate(n: int, seed: int, variants: int) -> list[dict]:
    rng = random.Random(seed)
    prompts: list[dict] = []
    i = 0
    while len(prompts) < n:
        template, domain = rng.choice(TEMPLATES)
        text = template
        for slot, values in SLOT_VALUES.items():
            if "{" + slot + "}" in text:
                text = text.replace("{" + slot + "}", rng.choice(values), 1)
        prompts.append({"id": f"hing-{i:05d}", "text": text, "domain": domain})
        i += 1
        for v in range(variants):
            if len(prompts) >= n:
                break
            prompts.append(
                {
                    "id": f"hing-{i:05d}",
                    "text": inject_spelling_variants(text, rng),
                    "domain": domain,
                    "variant_of": f"hing-{i - v - 1:05d}",
                }
            )
            i += 1
    return prompts[:n]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variants", type=int, default=2)
    ap.add_argument("--out", type=str, default="data/training/prompts.jsonl")
    args = ap.parse_args()

    backend_root = Path(__file__).resolve().parents[1]
    out = Path(args.out)
    if not out.is_absolute():
        out = backend_root / out
    prompts = generate(args.n, args.seed, args.variants)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for p in prompts:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"wrote {len(prompts)} prompts -> {out}")


if __name__ == "__main__":
    main()
