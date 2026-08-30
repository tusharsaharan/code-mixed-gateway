import { describe, expect, it } from "vitest";

import { countChar4Proxy, countWhitespace, estimateCostUsd } from "../tokenizer";

describe("countWhitespace", () => {
  it("counts words", () => {
    expect(countWhitespace("hello world")).toBe(2);
    expect(countWhitespace("  hello   world  ")).toBe(2);
    expect(countWhitespace("")).toBe(0);
    expect(countWhitespace("   ")).toBe(0);
  });

  it("handles single token", () => {
    expect(countWhitespace("yaar")).toBe(1);
  });
});

describe("countChar4Proxy", () => {
  it("byte-length /4 ceiling, min 1", () => {
    expect(countChar4Proxy("")).toBe(1);
    expect(countChar4Proxy("a")).toBe(1);
    expect(countChar4Proxy("abcd")).toBe(1);
    expect(countChar4Proxy("abcde")).toBe(2);
  });

  it("handles Hinglish and Devanagari", () => {
    const v = countChar4Proxy("yaar mera phone");
    expect(v).toBeGreaterThanOrEqual(1);
    const dev = countChar4Proxy("यार मेरा");
    // Devanagari is multi-byte, so larger
    expect(dev).toBeGreaterThanOrEqual(v);
  });

  it("is monotonic", () => {
    const short = countChar4Proxy("hi");
    const long = countChar4Proxy("hi hello world this is longer text");
    expect(long).toBeGreaterThanOrEqual(short);
  });
});

describe("estimateCostUsd", () => {
  it("scales linearly", () => {
    expect(estimateCostUsd(1000, 0.0025)).toBeCloseTo(0.0025, 6);
    expect(estimateCostUsd(2000, 0.0025)).toBeCloseTo(0.005, 6);
    expect(estimateCostUsd(0)).toBe(0);
  });

  it("supports cheap vs premium", () => {
    const cheap = estimateCostUsd(1000, 0.00006);
    const premium = estimateCostUsd(1000, 0.0025);
    expect(premium).toBeGreaterThan(cheap);
    expect(cheap).toBeCloseTo(0.00006, 6);
  });
});

describe("js-tiktoken async (fallback path)", () => {
  it("countTokensCl100k fallback is callable", async () => {
    const { countTokensCl100k } = await import("../tokenizer");
    const n = await countTokensCl100k("hello world");
    expect(n).toBeGreaterThanOrEqual(1);
  });
});
