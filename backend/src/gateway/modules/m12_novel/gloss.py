from __future__ import annotations

import re

# Word-level Hinglish → English lookup for synthetic gloss generation.
# Coverage tuned to the 60 seed queries; unseen tokens fall back to keep-as-is
# (so code_mix_ratio of gloss drops to ~0). This is intentionally rule-based
# and deterministic — no model call required — so the reasoning-delta experiment
# is reproducible offline.
HINGLISH_TO_EN: dict[str, str] = {
    # pronouns / address
    "mera": "my",
    "meri": "my",
    "mere": "my",
    "tera": "your",
    "teri": "your",
    "tere": "your",
    "mujhe": "me",
    "mujhse": "me",
    "tujhe": "you",
    "hum": "we",
    "aap": "you",
    "tum": "you",
    "yeh": "this",
    "ye": "this",
    "woh": "that",
    "vo": "that",
    # questions
    "kya": "what",
    "kahan": "where",
    "kaise": "how",
    "kab": "when",
    "kyun": "why",
    "kaun": "who",
    "kitna": "how much",
    "kitne": "how many",
    "kitni": "how much",
    # verbs / common
    "hai": "is",
    "hain": "are",
    "tha": "was",
    "thi": "was",
    "the": "were",
    "ho": "is",
    "raha": "is",
    "rahi": "is",
    "rahe": "are",
    "rha": "is",
    "nahi": "not",
    "nahin": "not",
    "matlab": "means",
    "yaar": "friend",
    "bhai": "brother",
    "arre": "oh",
    "na": "",
    "toh": "so",
    "haan": "yes",
    "chal": "go",
    "wala": "",
    "wali": "",
    "wale": "",
    "kar": "do",
    "karo": "do",
    "karna": "to do",
    "karun": "do",
    "batao": "tell",
    "bata": "tell",
    "bhejo": "send",
    "chahiye": "need",
    "chahie": "need",
    "samajh": "understand",
    "samjha": "understand",
    "padega": "will have to",
    "hoga": "will be",
    "hogi": "will be",
    "ka": "of",
    "ki": "of",
    "ke": "of",
    "ko": "to",
    "mein": "in",
    "me": "in",
    "par": "on",
    "se": "from",
    "tak": "until",
    "liye": "for",
    "bhi": "also",
    "hi": "only",
    "bahut": "very",
    "zyada": "much",
    "abhi": "now",
    "kal": "tomorrow",
    "aaj": "today",
    "thoda": "a little",
    "achha": "good",
    "accha": "good",
    "hostel": "hostel",
    "wifi": "wifi",
    "assignment": "assignment",
    "deadline": "deadline",
    "exam": "exam",
    "sir": "sir",
    "madam": "madam",
    "phone": "phone",
    "charge": "charge",
    "slow": "slow",
    "jaldi": "quickly",
    "araam": "rest",
    "basically": "",
    "actually": "",
    "like": "",
    "sun": "listen",
    "dekho": "see",
    "hai,": "is,",
}

_WORD = re.compile(r"(\W+)")


def to_english_gloss(text: str) -> str:
    """Deterministic Hinglish → English gloss for delta experiment.

    Tokenizes on word boundaries, replaces known Hinglish tokens, drops empty
    filler mappings, and preserves punctuation/casing.
    """
    # Use simple split to keep punctuation attached — we normalize lower lookup
    tokens = text.split()
    out: list[str] = []
    for tok in tokens:
        # Separate trailing punctuation for lookup
        m = re.match(r"^([A-Za-z]+)([.,!?;:]*)$", tok)
        if m:
            core, punct = m.group(1), m.group(2)
            low = core.lower()
            if low in HINGLISH_TO_EN:
                eng = HINGLISH_TO_EN[low]
                if eng == "":
                    continue  # filler dropped
                # Preserve capitalisation of original
                if core[0].isupper():
                    eng = eng.capitalize()
                out.append(eng + punct)
            else:
                out.append(tok)
        else:
            # Non-alpha tokens (numbers, code, etc.) keep as is
            low = tok.lower().strip(",.!?;:\"'()[]{}")
            if low in HINGLISH_TO_EN and HINGLISH_TO_EN[low] == "":
                continue
            if low in HINGLISH_TO_EN:
                out.append(HINGLISH_TO_EN[low])
            else:
                out.append(tok)
    gloss = " ".join(out)
    gloss = re.sub(r"\s+", " ", gloss).strip()
    return gloss if gloss else text
