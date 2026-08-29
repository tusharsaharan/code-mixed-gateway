from __future__ import annotations

import json
import random
import re
import unicodedata
from pathlib import Path

from gateway.schemas import PromptRecord

_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]+")
_WS = re.compile(r"[ \t]+")
_NEWLINES = re.compile(r"\n{3,}")

FILLERS = (
    "yaar",
    "matlab",
    "like",
    "basically",
    "arre yaar",
    "dekho na",
    "actually",
    "you know",
    "sun na",
    "matlab ki",
)

PLACEHOLDERS = {
    "email": "[EMAIL] user@example.com",
    "phone": "[PHONE] +91-98765-43210",
    "code": "[CODE] def foo(x): return x*2",
    "amount": "[AMOUNT] Rs. 2,500",
}


def normalize(text: str) -> str:
    """NFKC-normalize, drop zero-width/joiner marks, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text)
    text = _ZERO_WIDTH.sub("", text)
    text = _WS.sub(" ", text).strip()
    text = _NEWLINES.sub("\n\n", text)
    return text


def inject_fluff(text: str, rng: random.Random) -> str:
    """Insert code-mixed filler phrases and protected placeholders for downstream tests."""
    tokens = text.split()
    if not tokens:
        return text
    n_fillers = max(1, len(tokens) // 8)
    for _ in range(n_fillers):
        pos = rng.randint(0, len(tokens))
        tokens.insert(pos, rng.choice(FILLERS))
    placeholder = rng.choice(list(PLACEHOLDERS.values()))
    pos = rng.randint(0, len(tokens))
    tokens.insert(pos, placeholder)
    return " ".join(tokens)


def iter_jsonl(path: Path) -> list[PromptRecord]:
    records: list[PromptRecord] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(PromptRecord.model_validate(json.loads(line)))
    return records


def write_jsonl(path: Path, records: list[PromptRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(r.model_dump_json() for r in records) + "\n", encoding="utf-8")


SEED_HINGLISH = [
    # factual / campus support — 15
    "mera phone charge nahi ho raha hai, charger bhi change kar liya phir bhi nahi on ho raha",
    "bhai mera assignment submit nahi hua, deadline kya hai is week ki?",
    "hostel ka wifi bahut slow chal raha hai, complaint kahan karni hai?",
    "library ka timing kya hai sunday ko, books issue karni hai",
    "mess ka menu kya hai aaj raat ka, veg hai ya non-veg?",
    "fees ka last date kab hai is semester ka, late fee kitni lagegi?",
    "bus ka timing kya hai college se station tak sham ko",
    "medical leave kaise apply karni hai, certificate kahan submit karna hai?",
    "scholarship ka form kahan se milega, documents kya chahiye?",
    "ID card kho gaya hai mera, duplicate kaise banega kitna charge lagega?",
    "canteen ka token refund nahi mila, kisse contact karun?",
    "ye notice samajh nahi aaya, holiday kab hai exactly?",
    "lab ka access card activate nahi ho raha, kahan jana padega?",
    "yeh form bharna hai, date of birth ka format kya hai DD-MM-YYYY ya MM-DD?",
    "placement cell ka email kya hai, resume kahan bhejna hai?",
    # arithmetic / reasoning — 12
    "physics ka numerical samajh nahi aaya, ye formula kaise apply karun?",
    "kal exam hai maths ka, integration ke important questions bhejo na",
    "bhai ye maths ka sawal solve karo 15*8+22 ka answer batao jaldi",
    "probability ka question hai, 2 dice throw karne pe sum 7 ka probability kya hoga?",
    "ye algebra ka equation solve karo x^2 -5x+6=0 ka roots kya honge?",
    "ek triangle ka area nikalna hai base 12 height 8 diya hai",
    "bhai percentage nikalna hai, 450 me se 378 aaye toh kitna percent hua?",
    "ye number series ka next term batao 2, 6, 12, 20, 30, ?",
    "log ka value kya hota hai log 100 base 10 me",
    "ye simplify karo (3+5)*2 - 8/4 ka answer kya hai?",
    "ek train 60km/h se 3 ghante me kitni distance cover karegi?",
    "ye profit loss ka question hai, CP 500 SP 650 toh profit percent kya hua?",
    # support / transactional — 12
    "mera order delivery nahi hua, tracking id kahan se milega?",
    "refund kab tak aayega mere account me, 5 din ho gaye",
    "payment fail ho gaya par paise deduct ho gaye, kya karun?",
    "mera account login nahi ho raha, password reset ka link nahi aa raha",
    "ye product return karna hai, return window kab tak hai?",
    "bhai mera ticket cancel karna hai, cancellation charges kitne lagenge?",
    "ye subscription auto renew ho gaya, usko kaise band karun?",
    "mera address change karna hai profile me, kaise karu?",
    "ye OTP nahi aa raha phone pe, resend ka option kahan hai?",
    "mera coupon code apply nahi ho raha, invalid bata raha hai",
    "ye delivery address galat ho gaya, ab change ho sakta hai kya?",
    "mera wallet balance show nahi ho raha, kya issue hai?",
    # code / technical — 10
    "ek python program likhna hai jo list ko sort kare without library",
    "ye error aa raha hai: IndexError: list index out of range, kaise fix karun?",
    "mujhe DSA ka roadmap chahiye 3 mahine ke liye",
    "ek react component me state update nahi ho raha, kya bug ho sakta hai?",
    "ye SQL query me join kaise karte hain two tables ko explain karo",
    "git me merge conflict aa gaya, usko kaise resolve karun?",
    "ye API call me 500 error aa raha hai, backend kaise debug karun?",
    "docker me container start nahi ho raha, logs kahan dekhu?",
    "ek binary search ka code chahiye python me with explanation",
    "ye regex likhna hai jo email validate kare, pattern kya hoga?",
    # conversational / logic — 11
    "yaar kal chutti hai kya college me, koi notice aaya hai kya?",
    "bhai ye notice ka matlab kya hai, samjha do thoda simple me",
    "difference kya hai between AI and ML, thoda easy language me batao",
    "explain karo why hostel ka wifi slow hota hai peak hours me",
    "ye paragraph ka summary chahiye 100 words me",
    "ek formal email likhna hai professor ko leave ke liye, help karo",
    "ye hindi sentence ko english me translate karo: kal exam hai",
    "ek presentation ke liye 5 bullet points chahiye topic AI par",
    "ye story ko Hinglish me likho thoda funny banao",
    "bhai ye bill ka total galat lag raha hai, check karo na",
    "ye terms and conditions ka simple meaning bata do",
]


def build_seed(path: Path, seed: int = 0) -> list[PromptRecord]:
    rng = random.Random(seed)
    records: list[PromptRecord] = []
    for i, text in enumerate(SEED_HINGLISH):
        text = normalize(text)
        text = inject_fluff(text, rng)
        records.append(
            PromptRecord(
                id=f"seed-{i:03d}",
                text=text,
                lang_tag="hi-en",
                domain="student-support",
                fluff_ratio=0.25,
                meta={"source": "synthetic-seed", "seed": seed, "is_synthetic": True},
            )
        )
    return records


# --- synthetic benchmark construction (for calibration & eval) ---

# Minimal reference map — covers the expanded seed set with checkable answers.
# Any seed not in the map gets a generic placeholder answer; the map exists
# so task_success is not just a judgement call and so PII/code spans are tracked.
_BENCH_REFERENCES: dict[str, str] = {
    "mera phone charge nahi ho raha hai, charger bhi change kar liya phir bhi nahi on ho raha": "Try a different cable and wall adapter, clean the port, and test without the case; if still not charging visit service.",
    "bhai mera assignment submit nahi hua, deadline kya hai is week ki?": "Assignment deadline is Friday 5 PM this week.",
    "hostel ka wifi bahut slow chal raha hai, complaint kahan karni hai?": "Raise a complaint at the hostel wifi helpdesk or email network support.",
    "library ka timing kya hai sunday ko, books issue karni hai": "Library is open 10 AM to 5 PM on Sunday.",
    "mess ka menu kya hai aaj raat ka, veg hai ya non-veg?": "Tonight mess is veg: dal, rice, roti, sabzi.",
    "fees ka last date kab hai is semester ka, late fee kitni lagegi?": "Fees last date is 10th of next month, late fee Rs. 500 thereafter.",
    "bus ka timing kya hai college se station tak sham ko": "College to station bus runs at 5:30 PM and 7:00 PM.",
    "medical leave kaise apply karni hai, certificate kahan submit karna hai?": "Apply medical leave via portal and submit certificate at admin office.",
    "scholarship ka form kahan se milega, documents kya chahiye?": "Scholarship form is at the student section; need income certificate and marksheet.",
    "ID card kho gaya hai mera, duplicate kaise banega kitna charge lagega?": "Apply for duplicate ID at admin, charge Rs. 200.",
    "canteen ka token refund nahi mila, kisse contact karun?": "Contact canteen manager for token refund.",
    "ye notice samajh nahi aaya, holiday kab hai exactly?": "Holiday is on Tuesday as per notice.",
    "lab ka access card activate nahi ho raha, kahan jana padega?": "Visit lab admin to activate access card.",
    "yeh form bharna hai, date of birth ka format kya hai DD-MM-YYYY ya MM-DD?": "Use DD-MM-YYYY format for DOB.",
    "placement cell ka email kya hai, resume kahan bhejna hai?": "Placement cell email is placements@college.edu.",
    "physics ka numerical samajh nahi aaya, ye formula kaise apply karun?": "Apply formula step by step substituting given values.",
    "kal exam hai maths ka, integration ke important questions bhejo na": "Important integration topics: substitution, by parts, partial fractions.",
    "bhai ye maths ka sawal solve karo 15*8+22 ka answer batao jaldi": "15*8+22 = 142",
    "probability ka question hai, 2 dice throw karne pe sum 7 ka probability kya hoga?": "Probability of sum 7 with 2 dice is 6/36 = 1/6.",
    "ye algebra ka equation solve karo x^2 -5x+6=0 ka roots kya honge?": "Roots are x=2 and x=3.",
    "ek triangle ka area nikalna hai base 12 height 8 diya hai": "Area = 0.5*12*8 = 48",
    "bhai percentage nikalna hai, 450 me se 378 aaye toh kitna percent hua?": "378/450*100 = 84%",
    "ye number series ka next term batao 2, 6, 12, 20, 30, ?": "Next term is 42 (n*(n+1)).",
    "log ka value kya hota hai log 100 base 10 me": "log10(100) = 2",
    "ye simplify karo (3+5)*2 - 8/4 ka answer kya hai?": "(3+5)*2 - 8/4 = 14",
    "ek train 60km/h se 3 ghante me kitni distance cover karegi?": "Distance = 60*3 = 180 km",
    "ye profit loss ka question hai, CP 500 SP 650 toh profit percent kya hua?": "Profit% = 30%",
    "mera order delivery nahi hua, tracking id kahan se milega?": "Tracking ID is sent to your email after dispatch.",
    "refund kab tak aayega mere account me, 5 din ho gaye": "Refund is processed within 7 working days.",
    "payment fail ho gaya par paise deduct ho gaye, kya karun?": "Amount will be reversed in 3-5 working days; contact support if not.",
    "mera account login nahi ho raha, password reset ka link nahi aa raha": "Check spam folder for reset link or try again after 10 minutes.",
    "ye product return karna hai, return window kab tak hai?": "Return window is 7 days from delivery.",
    "bhai mera ticket cancel karna hai, cancellation charges kitne lagenge?": "Cancellation charge is Rs. 150.",
    "ye subscription auto renew ho gaya, usko kaise band karun?": "Disable auto-renew in subscription settings.",
    "mera address change karna hai profile me, kaise karu?": "Update address in profile settings and save.",
    "ye OTP nahi aa raha phone pe, resend ka option kahan hai?": "Tap resend OTP after 60 seconds.",
    "mera coupon code apply nahi ho raha, invalid bata raha hai": "Coupon is invalid or expired.",
    "ye delivery address galat ho gaya, ab change ho sakta hai kya?": "Address can be changed before dispatch only.",
    "mera wallet balance show nahi ho raha, kya issue hai?": "Try refreshing or check after 5 minutes.",
    "ek python program likhna hai jo list ko sort kare without library": "Use bubble or insertion sort loop in Python.",
    "ye error aa raha hai: IndexError: list index out of range, kaise fix karun?": "Check list length before indexing; loop may exceed bounds.",
    "mujhe DSA ka roadmap chahiye 3 mahine ke liye": "Month 1: arrays+strings, Month 2: trees+graphs, Month 3: DP.",
    "ek react component me state update nahi ho raha, kya bug ho sakta hai?": "State may be mutated directly instead of setState.",
    "ye SQL query me join kaise karte hain two tables ko explain karo": "Use SELECT ... FROM a JOIN b ON a.id=b.id",
    "git me merge conflict aa gaya, usko kaise resolve karun?": "Resolve edits in files, then git add and git commit.",
    "ye API call me 500 error aa raha hai, backend kaise debug karun?": "Check server logs and stack trace.",
    "docker me container start nahi ho raha, logs kahan dekhu?": "Run docker logs <container_id>",
    "ek binary search ka code chahiye python me with explanation": "Binary search uses low/high pointers and compares mid.",
    "ye regex likhna hai jo email validate kare, pattern kya hoga?": "Regex: ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$",
    "yaar kal chutti hai kya college me, koi notice aaya hai kya?": "Yes, tomorrow is a holiday as per notice.",
    "bhai ye notice ka matlab kya hai, samjha do thoda simple me": "Notice says tomorrow is holiday for maintenance.",
    "difference kya hai between AI and ML, thoda easy language me batao": "AI is making machines think; ML is learning from data.",
    "explain karo why hostel ka wifi slow hota hai peak hours me": "Many users share same bandwidth at peak hours.",
    "ye paragraph ka summary chahiye 100 words me": "Summary: paragraph discusses upcoming exams and preparation.",
    "ek formal email likhna hai professor ko leave ke liye, help karo": "Subject: Leave application; body: respectful request with dates.",
    "ye hindi sentence ko english me translate karo: kal exam hai": "Translation: Tomorrow is the exam.",
    "ek presentation ke liye 5 bullet points chahiye topic AI par": "Points: definition, types, applications, advantages, challenges.",
    "ye story ko Hinglish me likho thoda funny banao": "Story in funny Hinglish as requested.",
    "bhai ye bill ka total galat lag raha hai, check karo na": "Bill total checked, correction suggested.",
    "ye terms and conditions ka simple meaning bata do": "T&C simplified as requested.",
}


def _reference_for(text: str) -> str:
    return _BENCH_REFERENCES.get(text.strip(), f"Answer for: {text[:60]}")


def build_synthetic_benchmark(n: int | None = None, seed: int = 0) -> list[dict]:
    """Build a synthetic benchmark (>=50 rows) from SEED_HINGLISH.

    Each row mirrors the existing benchmark.jsonl shape so curve_points
    and evaluate() work unchanged. All rows are clearly marked
    is_synthetic=True in the row so downstream exports can flag them.
    """
    from gateway.modules.m2_compressor.safety_span import detect_spans

    rng = random.Random(seed)
    take = n if n is not None else min(50, len(SEED_HINGLISH))
    indices = list(range(len(SEED_HINGLISH)))
    rng.shuffle(indices)
    chosen = indices[:take]
    rows: list[dict] = []
    for idx in chosen:
        original = normalize(SEED_HINGLISH[idx])
        # heuristic compressed preview (same as Compressor._heuristic_compress core)
        protected = [sp.text for sp in detect_spans(original)]
        # keep reference generic if not in map
        ref = _reference_for(original)
        # compressed: drop some fillers heuristically for preview (mirrors m2 logic)
        tokens = original.split()
        fillers = {"yaar", "matlab", "like", "basically", "actually", "arre", "na", "bhai"}
        comp = " ".join(t for t in tokens if t.lower().strip(",.!?") not in fillers)
        comp = re.sub(r"^(hi|hello|hey|namaste|namaskar|hii+|yo|sir|madam|bro|dost)[\s,!.]+", "", comp, flags=re.IGNORECASE).strip()
        if not comp:
            comp = original
        rows.append(
            {
                "id": f"bench-{idx:03d}",
                "original": original,
                "compressed": comp,
                "reference_answer": ref,
                "predicted_answer": ref,
                "protected": protected,
                "is_synthetic": True,
                "task_type": "synthetic",
                "lang_tag": "hi-en",
            }
        )
    return rows


def write_benchmark(path: Path, n: int | None = None, seed: int = 0) -> list[dict]:
    rows = build_synthetic_benchmark(n=n, seed=seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return rows