// Client-side tokenizer via js-tiktoken (MIT, pure JS, no backend)
// Uses cl100k_base (GPT-4o style) — same family as backend's tiktoken_cl100k_base
// Falls back to whitespace if encoder fails to load.

let enc: { encode: (s: string) => number[]; decode: (t: number[]) => string } | null = null;
let encPromise: Promise<unknown> | null = null;

async function getEnc() {
  if (enc) return enc;
  if (!encPromise) {
    encPromise = import("js-tiktoken")
      .then(async (m) => {
        // js-tiktoken exports `encodingForModel` and `getEncoding`
        const { getEncoding } = m as unknown as { getEncoding: (name: string) => unknown };
        try {
          const e = getEncoding("cl100k_base") as {
            encode: (s: string) => number[];
            decode: (t: number[]) => string;
          };
          enc = e;
        } catch {
          enc = null;
        }
      })
      .catch(() => {
        enc = null;
      });
  }
  await encPromise;
  return enc;
}

export async function countTokensCl100k(text: string): Promise<number> {
  const e = await getEnc();
  if (!e) return text.trim() ? text.trim().split(/\s+/).length : 0;
  try {
    return e.encode(text).length;
  } catch {
    return text.trim() ? text.trim().split(/\s+/).length : 0;
  }
}

export async function tokenChips(
  text: string,
): Promise<{ id: number; text: string; token: number }[]> {
  const e = await getEnc();
  if (!e) {
    const words = text.split(/(\s+)/);
    let idx = 0;
    return words.filter((w) => w.trim()).map((w) => ({ id: idx++, text: w, token: idx }));
  }
  try {
    const tokens = e.encode(text);
    // Decode each token individually for chip text; js-tiktoken decode may add leading space
    const chips: { id: number; text: string; token: number }[] = [];
    for (let i = 0; i < tokens.length; i++) {
      try {
        const piece = e.decode([tokens[i]!]);
        chips.push({ id: i, text: piece, token: tokens[i]! });
      } catch {
        chips.push({ id: i, text: "�", token: tokens[i]! });
      }
    }
    return chips;
  } catch {
    return [{ id: 0, text, token: 0 }];
  }
}

// Synchronous whitespace fallback (always available, zero async cost)
export function countWhitespace(text: string): number {
  const t = text.trim();
  return t ? t.split(/\s+/).length : 0;
}

// Approximate char4 proxy (backend's char4_proxy) — byte-length /4
export function countChar4Proxy(text: string): number {
  return Math.max(1, Math.ceil(new TextEncoder().encode(text).length / 4));
}

export function estimateCostUsd(tokens: number, per1k = 0.0025): number {
  return (tokens * per1k) / 1000;
}
