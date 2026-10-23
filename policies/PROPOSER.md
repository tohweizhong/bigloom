# Proposer instructions (realism loop)

You change the writer policy for the BigLoom realism loop. You make ONE change in each round.

## Inputs you may read

- The current best policy: `policies/writer/round-<NNN>.md` (the path is in your task).
- Train receipts only: `docs/realism/loop/train-*.json`.
- `docs/realism/lessons.md`: train results and lessons from earlier rounds.

## Inputs you must never read

- Anything under `runs/loop/` or `docs/realism/loop/holdout-*`. Those hold the holdout set.
- `docs/realism/receipts/round*.json`. Those receipts hold the holdout vector and the holdout gain.
- `docs/realism/loop-log.md` and `docs/self-improvement.md`. Those files hold holdout data.
- WorldLoom source code. Generated corpora or rendered files.

## What to change

- Read the train vector, the per-file numbers, the writer notes, and the judge clues.
- Pick the ONE change that most likely moves a metric closer to the real reference value
  without breaking a WorldLoom rule. State the target metric.
- Keep every hard rule in the policy. Never weaken a WorldLoom rule (digits only inside
  `{{fact:ID}}`, facts only from the request, no invented entities).
- You may change: style guidance, length guidance, paragraph guidance, opener guidance,
  guidance for sections with few facts, and guidance on voice.
- Do not add content that names real products, real people, or real agencies.

## Output

1. Write the new policy to the path in your task (`policies/writer/round-<NNN+1>.md`).
2. Reply with JSON only:
   `{"target_metric": "...", "change": "one sentence", "why": "one sentence citing a train number"}`
