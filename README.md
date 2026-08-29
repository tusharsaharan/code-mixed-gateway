# Code-Mixed Gateway

That research proposal you attached changes things worth flagging first, then let's build the real plan.

## Quick reality check

Your submitted proposal is intentionally light: _"no model training required... compute needs are small... runs on CPU or free-tier Colab... light-touch workload."_ That was the right call for a scoped, low-risk first proposal. What you're asking for now — real training, live deployment, real users, 3 months of serious effort — is a genuinely different (bigger, better) project. Before you sink weeks into this: **send your professor a two-line update** saying you want to expand scope from an evaluation study to a built system with training and a live pilot. Professors almost always say yes to "we want to do more than we promised" — but you want that on record, not discovered in week 10.

## The anchor idea

Your proposal already found the real gap: published compression/routing numbers are benchmarked on clean English text (GSM8K, MeetingBank, ShareGPT), and nobody has rigorously tested whether they hold on **real-world, code-mixed text** — the Hindi-English (Hinglish) mix that's the actual language of Indian customer support, WhatsApp business chat, and campus life. Your tokenizer-fairness citation (Petrov et al.) already tells you _why_ this matters economically: tokenizers can produce **up to 15x more tokens** for the same content depending on language, meaning code-mixed text may be quietly expensive in ways nobody's measured.

So instead of "evaluate an existing library on some new text" (your proposal) or "generic LLM routing system" (the report), do this:

**Build and train the first open, reward-optimized compression + calibrated-routing gateway specifically for code-mixed/real-world business text — then deploy it to real users who actually speak that way.**

This keeps your proposal's novelty (the domain gap), upgrades it from "call a library" to "train real models," and gives you a real audience that makes sense organically (your own campus community already speaks Hinglish daily — you're not manufacturing a use case).

## The four pillars (the actual work, not the wrapper)

**A. A reward-trained compressor for code-mixed text** — Instead of using off-the-shelf LLMLingua-2, train your own small compressor (start from Qwen3.6's small dense variant or Gemma 4 4B) using GRPO or DPO-style RL, where the reward is _actual downstream task correctness on code-mixed text_, not proxy perplexity. This is exactly the OSCAR/CORE/TACO direction your report flagged as the 2026 frontier — except nobody's built an open version of it for this domain. This is your strongest "we did something nobody else has" claim.

**B. A conformally-calibrated cascade router** — Don't just calibrate confidence scores; wrap the escalation decision in **conformal risk control**, which is a very active 2026 research line (recent work like Conformal Cascade and RouteNLP frame routing this way to give a distribution-free, finite-sample guarantee on cascade accuracy instead of a heuristic threshold). One real deployment using this approach reported real inference costs exceeding $200K/month with over 70% of queries being routine, and closed the loop with a conformally-calibrated cascade plus targeted distillation, validated in an eight-week pilot deployment that matched simulation predictions within a 4-point gap on cost reduction. That's your template _and_ your target to benchmark against. This gives you a genuine, defensible line for your professor: **"our system has a mathematically provable bound on error rate,"** not just "it seems to work."

**C. A reasoning-budget controller** — Using an open reasoning model (DeepSeek-R1-distill or gpt-oss-20b), train a small predictor that estimates how many "thinking tokens" a query actually needs before generating. Bonus research question nobody's asked: **does a Hinglish math/logic query need a different reasoning budget than its English equivalent?** That's a genuinely publishable side-finding.

**D. Serving infrastructure (the fast part)** — vLLM or SGLang for prefix caching and speculative decoding, wired into one OpenAI-compatible gateway. This is the "Antigravity builds it fast" layer — assign it to whoever's doing the 10% engineering role.

## The benchmark you get to own

Build and release **"the first open code-mixed LLM cost/quality benchmark"** — real support-chat-style Hinglish queries, graded for task accuracy at multiple compression ratios, with cost converted to actual ₹/$ at current API pricing (exactly what your proposal asked for). Release it on Hugging Face as a dataset. Even if the training experiments hit snags, a clean, citable dataset is a real, standalone contribution a professor can point to.

## Where your real audience actually lives

- **A WhatsApp or Telegram bot** (free Bot APIs) that answers real student questions in natural Hinglish, routed through your gateway — deploy it in actual campus/course WhatsApp groups.
- **An OpenAI-compatible endpoint** classmates can point Continue.dev/Cline/aider at for coding help — real developer traffic, real savings data.
- **A Hugging Face Space** for the public demo + live dashboard (see ZeroGPU note below — free H200 access makes this free to host).
- Once stable: post to r/developersIndia or r/LocalLLaMA for outside feedback — a real community that cares specifically about this angle.
- **One practical note:** since you're logging real people's queries for research, tell users their (anonymized) queries may be used for the project, and don't log anything identifying. Ask your professor if your institute wants a lightweight consent/ethics sign-off — a two-line thing to sort now, not after you have data.

## Where to actually train and host

Kaggle gives a visible, guaranteed weekly quota of about 30 GPU-hours on a P100 or two T4s, and is more reliable than Colab's free T4 tier, which gives roughly 15–30 hours a week with 12-hour session limits — use Kaggle as your daily driver, Colab as overflow. For hosting your public demo, Hugging Face's ZeroGPU gives shared access to H200 GPUs (70–141GB VRAM) for Spaces, with no credit card required — genuinely powerful hardware for free. Lightning AI adds 80 more free GPU hours a month in a persistent workspace. For the heavier GRPO/DPO training runs that won't fit free tiers, rent A100/H100 spot instances on RunPod or Vast.ai by the hour (cheap, no commitment). Skip AWS SageMaker Studio Lab — it stopped accepting new signups on July 30, 2026.

| Tier                               | Use it for                                       | Notes                                                                                              |
| ---------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| Kaggle (free)                      | Daily experimentation, small training runs       | 30 hrs/week, most reliable free option                                                             |
| Colab (free)                       | Overflow, quick tests                            | Unreliable GPU availability                                                                        |
| HF ZeroGPU Spaces (free)           | Hosting your public demo/dashboard               | H200-class hardware, free                                                                          |
| Lightning AI (free)                | Persistent dev environment                       | 80 hrs/month                                                                                       |
| RunPod / Vast.ai (cheap, ~$1–2/hr) | GRPO/DPO training bursts                         | Use sparingly, budget it                                                                           |
| Groq / Cerebras (free API)         | Fast inference for your "big model" cascade tier | Free API access to hosted open models on specialized hardware — no training access, inference only |
| Your department                    | Ask directly, given the expanded scope           | Many CS depts have a cluster or can requisition credits for supervised research                    |

**Model stack** (current as of this year): Qwen3.6's open-weight line (35B-A3B MoE and 27B dense) is Apache 2.0 — clean license, good backbone for your compressor and mid-tier cascade model. Gemma 4 ships in 1B/4B/12B/27B sizes with 128K context and support for 140+ languages on a single GPU — genuinely useful for the code-mixed angle. For the reasoning-budget pillar, use DeepSeek-R1-distill or gpt-oss, OpenAI's open-weight models — its first since GPT-2.

## Team split (80 / 10 / 10)

| Member               | Share | Owns                                                                                                                                      | Why this split works                                                                                         |
| -------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **Research Lead**    | 80%   | Pillars A, B, C: training the compressor, building the conformal router, the reasoning-budget controller, the actual experiments, writeup | This is the genuinely novel, exploratory ML work — it can't be parallelized easily and needs deep continuity |
| **Data & Eval Lead** | 10%   | Building the code-mixed benchmark, running the eval suite across all pillars, producing charts/tables, scheduling compute jobs            | Structured, scriptable work — real, meaningful, but doesn't need constant judgment calls                     |
| **Platform Lead**    | 10%   | Gateway engineering via Antigravity, the WhatsApp/Telegram bot, HF Space + dashboard, user recruitment, monitoring                        | Building is fast with AI tools now — this genuinely doesn't need more time to be a real contribution         |

## The 12-week plan

| Weeks | Focus       | Key milestones                                                                                                                                                   |
| ----- | ----------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1–2   | Setup       | Compute accounts live (Kaggle/Colab/HF/RunPod), gateway skeleton up, professor scope email sent, benchmark v0 collection started, reproduce LLMLingua-2 baseline |
| 3–4   | Baselines   | Baseline compression + naive cascade numbers on your code-mixed benchmark; recruit first ~10 test users early                                                    |
| 5–6   | Pillar A    | Train the reward-based compressor (GRPO/DPO); compare against baseline on your Fig-1-style ratio-vs-accuracy chart                                               |
| 7     | Pillar B    | Build the conformal cascade router; measure calibration (ECE) before/after                                                                                       |
| 8     | Pillar C    | Reasoning-budget controller on open reasoning model; test the Hinglish-vs-English budget question                                                                |
| 9     | Integration | Merge all pillars into one gateway; stand up dashboard                                                                                                           |
| 10    | Live pilot  | Deploy WhatsApp/Telegram bot + coding-assistant endpoint to real users; collect 1–2 weeks of live traffic                                                        |
| 11    | Analysis    | Analyze real traffic vs. benchmark predictions; refine thresholds                                                                                                |
| 12    | Wrap-up     | Final report/optional arXiv preprint, open-source release, demo day, community post                                                                              |

## What "impressive" actually looks like (set these as targets)

- ≥15x compression on code-mixed text at ≤5–8% accuracy loss (beating that would put you near OSCAR's generic-domain numbers)
- A **provable** conformal accuracy bound you can state as a guarantee, not an estimate
- ≥40% real cost reduction measured on live traffic against a naive always-large-model baseline — a comparable real pilot reported 58% cost reduction against 62% predicted from benchmarks, so this is a realistic bar
- A real number of real users and real queries from the pilot — this single fact will matter more to your professor than any benchmark table
- Open GitHub repo + HF dataset release; arXiv preprint as a stretch goal

## If something breaks

GRPO/DPO training is unstable sometimes → have a fallback of simpler rejection-sampling distillation ready. Conformal guarantees need enough calibration data → make sure benchmark v0 is sizeable before week 5. User recruitment is often slower than expected → start recruiting in week 1–2, not week 10.

## This week

1. Send the professor the scope-change note.
2. Create the GitHub repo + Kaggle/HF/RunPod accounts.
3. Start collecting code-mixed sample queries (even 50–100 real messages from friends/group chats, anonymized, is enough to start).
4. Stand up the barest gateway skeleton so it's "live" early, even if dumb.

Want me to start on any specific piece next — the GRPO training script scaffold, the conformal router implementation, or a one-page scope-update doc for your professor. Now let me validate the JSX syntax before presenting it.Bundle succeeded. Now let's actually render it to catch any runtime errors in the initial state.Good news first: **none of this actually needed training skills** — I just hadn't separated "training-free" from "trained" clearly enough last time. Here's the honest split:

- **Compression** → can be done by _prompting_ a model to compress (what this demo does), or by classic non-trained methods like perplexity pruning. No training required either way.
- **Calibrated routing** → conformal calibration is statistics applied to a model's existing outputs, not a trained neural net. Still fully in play.
- **Reasoning-budget control** → can be done via prompting/API parameters instead of a trained predictor.

So the research direction survives. What changes is _how_ each pillar gets built.

## What I built

A working, live demo (not a mockup) — **`gateway_live_demo.jsx`**. Open it and click "Run through the gateway." It genuinely:

1. **Compresses** your prompt with a real model call (prompted to preserve every task-critical detail, drop the rest)
2. **Scores difficulty** with a second real call, and decides — based on a threshold you can drag — whether this would route to a cheap or premium tier
3. **Answers** using the _compressed_ prompt, so you can see it still gives a correct, coherent answer
4. Shows real word-level highlighting of what got cut, real (approximate) token counts, and a running session dashboard with a live chart

Try the Hinglish preset first — it's the one tied to your actual research angle.

**What's honestly real vs. illustrative** (I built it this way on purpose, and I'd keep this distinction visible in your own version too — it's exactly the kind of rigor that impresses a professor): the compression, scoring, and answer are real live model calls. The _tier names and pricing_ are reference numbers from published 2026 API rates, standing in for the multiple real open models a full deployment would route across — since this demo only has one model available to call directly. The footer says this explicitly. Don't let Antigravity quietly drop that disclaimer when it expands this — that honesty is part of the "real work," not a hedge.

## Where Antigravity takes it from here

This is a clean base to hand off. Natural next additions, all still training-free:

- Swap the single simulated tier for real calls to actual cheap/premium models (Groq for Llama/Gemma, a frontier API for the premium tier) — turns the "illustrative" cost math into fully real numbers
- Add the conformal calibration layer on top of the difficulty scores you're already collecting
- Wire in the WhatsApp/Telegram bot so real campus queries flow through this same pipeline

Want me to build the real multi-model version next (actually calling a cheap open model + a premium model instead of simulating the tier), or wire up the conformal calibration logic on top of what's here. make a website for this professional and soft frontend.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/d37bd54b-0786-4c93-a4af-b67e4a4c5c73).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
