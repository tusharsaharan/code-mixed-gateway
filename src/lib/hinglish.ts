// Shared Hinglish lexicon mirrored from backend hinglish.py / gloss.py
// Used for client-side visualizer and slider without round-trip

export const HINGLISH_TO_EN: Record<string, string> = {
  mera: "my", meri: "my", mere: "my", tera: "your", teri: "your", tere: "your",
  mujhe: "me", mujhse: "me", tujhe: "you", hum: "we", aap: "you", tum: "you",
  yeh: "this", ye: "this", woh: "that", vo: "that",
  kya: "what", kahan: "where", kaise: "how", kab: "when", kyun: "why", kaun: "who",
  kitna: "how much", kitne: "how many", kitni: "how much",
  hai: "is", hain: "are", tha: "was", thi: "was", the: "were", ho: "is",
  raha: "is", rahi: "is", rahe: "are", rha: "is", nahi: "not", nahin: "not",
  matlab: "means", yaar: "friend", bhai: "brother", arre: "oh", na: "", toh: "so",
  haan: "yes", chal: "go", wala: "", wali: "", wale: "",
  kar: "do", karo: "do", karna: "to do", karun: "do", batao: "tell", bata: "tell",
  bhejo: "send", chahiye: "need", chahie: "need", samajh: "understand", samjha: "understand",
  padega: "will have to", hoga: "will be", hogi: "will be",
  ka: "of", ki: "of", ke: "of", ko: "to", mein: "in", me: "in", par: "on", se: "from",
  tak: "until", liye: "for", bhi: "also", hi: "only",
  bahut: "very", zyada: "much", abhi: "now", kal: "tomorrow", aaj: "today",
  thoda: "a little", achha: "good", accha: "good",
  hostel: "hostel", wifi: "wifi", assignment: "assignment", deadline: "deadline",
  exam: "exam", sir: "sir", madam: "madam", phone: "phone", charge: "charge", slow: "slow",
  jaldi: "quickly", basically: "", actually: "", like: "", sun: "listen", dekho: "see",
};

const DEVANAGARI_MAP: Record<string, string> = {
  yaar: "यार", mera: "मेरा", meri: "मेरी", mere: "मेरे", hostel: "हॉस्टल", wifi: "वाईफाई",
  bahut: "बहुत", slow: "स्लो", hai: "है", hain: "हैं", nahi: "नहीं", kahan: "कहाँ",
  karun: "करूँ", complaint: "शिकायत", kya: "क्या", kaise: "कैसे", bhai: "भाई",
  kal: "कल", assignment: "असाइनमेंट", submit: "सबमिट", karna: "करना", chahiye: "चाहिए",
  phone: "फ़ोन", charge: "चार्ज", ho: "हो", raha: "रहा", dekho: "देखो", bhej: "भेज",
  batao: "बताओ", jaldi: "जल्दी", arre: "अरे", toh: "तो", haan: "हाँ",
  sir: "सर", madam: "मैडम", exam: "एग्जाम", deadline: "डेडलाइन",
};

export function toEnglishGloss(text: string): string {
  const tokens = text.split(/\s+/);
  const out: string[] = [];
  for (const tok of tokens) {
    const m = tok.match(/^([A-Za-z]+)([.,!?;:]*)$/);
    if (m) {
      const core = m[1]!;
      const punct = m[2] ?? "";
      const low = core.toLowerCase();
      if (low in HINGLISH_TO_EN) {
        const eng = HINGLISH_TO_EN[low]!;
        if (eng === "") continue;
        const final = core[0] === core[0]?.toUpperCase() ? eng.charAt(0).toUpperCase() + eng.slice(1) : eng;
        out.push(final + punct);
      } else out.push(tok);
    } else {
      const low = tok.toLowerCase().replace(/[,.!?;:"'()[\]{}]/g, "");
      if (low in HINGLISH_TO_EN && HINGLISH_TO_EN[low] === "") continue;
      if (low in HINGLISH_TO_EN) out.push(HINGLISH_TO_EN[low]!);
      else out.push(tok);
    }
  }
  const j = out.join(" ").replace(/\s+/g, " ").trim();
  return j || text;
}

export function toDevanagariApprox(text: string): string {
  // Very small deterministic transliteration for visualizer demo — covers presets + common words
  const tokens = text.split(/(\s+)/);
  return tokens.map((tok) => {
    if (/^\s+$/.test(tok)) return tok;
    const m = tok.match(/^([A-Za-z]+)([.,!?;:]*)$/);
    if (!m) return tok;
    const core = m[1]!;
    const punct = m[2] ?? "";
    const low = core.toLowerCase();
    if (low in DEVANAGARI_MAP) return DEVANAGARI_MAP[low]! + punct;
    return tok;
  }).join("");
}

export function codeMixRatio(text: string): number {
  const dev = (text.match(/[\u0900-\u097F]/g) || []).length ? text.split(/\s+/).filter((t) => /[\u0900-\u097F]/.test(t)).length : 0;
  const toks = text.split(/\s+/);
  const n = toks.length || 1;
  const roman = toks.filter((t) => {
    const low = t.toLowerCase().replace(/[,.!?;:"'()[\]{}]/g, "");
    return low in HINGLISH_TO_EN || ["ka","ki","ke","ko","mein","me","par","se","tak","liye","bhi","hi"].includes(low);
  }).length;
  return Math.min(1, (dev + roman) / n);
}
