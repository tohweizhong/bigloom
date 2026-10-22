# Realism self-improvement loop

Status: updated after Round 2, 23 Oct 2026 00:02 SGT. Every part of the loop is built and has run
end-to-end. This page reports measured numbers and cites the round receipts.

BigLoom builds large files that must read like real agency documents. This page describes the loop
that measures realism, the rounds that have run, and the findings from each round. The design
follows WorldLoom `evalrun improve`: change one policy, measure on a train set and an unseen
holdout set, and keep the change only when it wins on both.

## 1. Loop design

| Loop part | In BigLoom | State |
|---|---|---|
| Agent under test | The writer that answers WorldLoom narration requests (`bigloom narrate prepare`, then `accept`) | Built (`src/bigloom/narration.py`) |
| Policy | Versioned writer instructions in `policies/writer/round-<NNN>.md` | Built |
| Hard gates, never optimized | `bigloom narrate accept` (WorldLoom claim checks), `bigloom qualify` (leakage, retrieval, realism findings), text and image fact depth | Built (`src/bigloom/qualify.py`, `src/bigloom/realism.py`) |
| Score | The metric vector (section 3) and the masked blind judge guard (section 4) | Built (`src/bigloom/realism_metrics.py`, `src/bigloom/realism_pairs.py`) |
| Proposer | A subagent that reads train receipts and makes one change to the writer policy | Built (`policies/PROPOSER.md`) |
| Holdout | Seeds `3101` (2 MB) and `3102` (5 MB) that the proposer never sees | Built (`src/bigloom/realism_loop.py`) |
| Promotion rule | At least one train dimension improves beyond its band, no train dimension worsens beyond its band, holdout normalised distance falls, and the judge guard does not trip | Built (`realism_loop.decide`) |
| Receipt | One JSON file for each round in `docs/realism/receipts/round<N>.json` (and train-only view in `docs/realism/loop/train-<NNN>.json`) | Built |

Rules that apply to every round:

- The grader does not change during a loop. Each receipt records `grader_sha256`
  (`eeb607b3b32acbfc02a99f24c97da73e0a94d871c1272b4d2e456b66f56dd32b`), the policy digests, and
  the judge prompt digest.
- One policy change per round. Champion and candidate run on the same cached world seeds (`2026`
  and `2027` for train, `3101` and `3102` for holdout).
- The proposer reads train receipts only. It never sees holdout passages or holdout vectors.
- Product and organisation names are masked (`[PRODUCT-1]`, `[ORG-1]`) on both sides of every
  blind judge pair (`realism_pairs.mask_names`).
- Each round receipt stores two sample passages of about 150 words from the promoted set.
- All model roles are Jetski subagents. No Vertex AI.

## 2. Changes across rounds

| Round | Writer and policy | Filter | Policy change under test | Result |
|---|---|---|---|---|
| Round 0 | WorldLoom template writer (`ComposedProvider`) | Off | Baseline | Baseline (`round0.json`) |
| Round 1 | Jetski writer subagent (`policies/writer/round-001.md`, `bda2a5cd…`) | On (`longform_filter.py`) | Handshake writer + appendix/ID filter + single-column measure table (`2e2fa95`) | Champion baseline (`round1.json`) |
| Round 2 | Jetski writer subagent (`policies/writer/round-002.md`, `a60c857a…`) | On | Add `VOCABULARY` rule: name commercial measures at most once per paragraph and use public-sector words (`income`, `funding drawn`, `surplus`, `cost recovery`) for repeat references | **Promoted** (`round2.json`, holdout gain `+0.051`) |

## 3. Metric vector

The metric vector uses no model calls. All columns use the same grader
(`grader_sha256` `eeb607b3b32a…`). Rates are per 1000 words. Sentence reuse compares different
documents only; size twins (the same document type at 2 MB and 5 MB) do not count.

| Metric | Real (11 files) | Round 0 Train | Round 1 Train (re-baselined) | Round 2 Train | Round 1 Holdout | Round 2 Holdout |
|---|---|---|---|---|---|---|
| WorldLoom IDs per 1000 words | 0.0 | 20.50 | 0.00 | 0.00 | 0.00 | 0.00 |
| Commercial terms per 1000 words | 0.0 | 20.44 | 7.55 | **2.26** | 7.19 | **6.30** |
| Retail terms per 1000 words | 0.78 | 1.40 | 0.21 | 0.21 | 0.20 | 0.23 |
| Repeated sentences in one file | 4.0% | 16.0% | 4.4% | **3.9%** | 3.9% | 4.0% |
| Most common three-word opener | 7.4% | 20.1% | 12.0% | 13.0% | 12.6% | 13.5% |
| Unique sentences per file | 146.7 | 30.5 | 51.3 | 48.8 | 57.2 | 52.0 |
| Sentence reuse across different documents | 0.1% | 6.6% | 0.0% | 0.0% | 0.0% | 0.0% |
| Dates after the document date | 0 | 0 | 0 | 0 | 0 | 0 |
| Words per MB | 4,032 | 443 | 440 | 435 | 450 | 390 |

Findings after Round 2:

1. **Commercial terms dropped by 70% on train (`7.55` to `2.26`) and by 12% on holdout (`7.19` to
   `6.30`).** On train, the PDF rate fell from `9.11`/`8.77` to `4.14`/`3.04`, and the deck rate
   fell from `12.53`/`13.64` to `2.56`/`2.55`.
2. **Repeated table cells fixed (`2e2fa95`).** In Round 1, Masked Judge 1 spotted that BigLoom's
   planted text-fact table repeated the measure label twice in the same row (`row.label` and
   `cells["measure"]`). Making the table single-column (`Value`) removed that clue and lowered
   Round 1 train `commercial_per_k` from `8.05` to `7.55`.
3. **Top opener share in PDF (`0.087` on 5 MB train) and PPTX (`0.312`).** In Seed 2027 `ART-0020`,
   the writer started six sentences with `The finance team`. In PPTX, five slide bullets start with
   the date `# April #` from WorldLoom's slide layout.

## 4. Blind judges and correlated series behaviour

| Round | Masking | Correct verdicts (3 judges, `pro`) | Mean error rate (goal 50%) | Main clues reported by judges |
|---|---|---|---|---|
| Round 0 | Unmasked | `[20, 20, 20]` (60/60) | 0.0% | WorldLoom IDs, lineage tables, formulaic templates, 2026 dates |
| Round 1 | Unmasked | `[20, 20, 20]` (60/60) | 0.0% | Real public GovTech product/framework names on real side (14 to 18 of 20), document type (15 of 20); 0 mentions of WorldLoom IDs, repeats, or 2026 dates |
| Round 1 | Masked (`[PRODUCT-n]`, `[ORG-n]`) | `[20, 0, 0]` (20/60) | 66.7% | Each judge grouped the 20 pairs into two document series; two judges inverted which series was real |
| Round 2 | Masked (`[PRODUCT-n]`, `[ORG-n]`) | `[20, 20, 20]` (60/60) | 0.0% | PDF column/font/table extraction marks and control codes on real side (12 to 13 of 20); dramatic or polished narrative tone in thin-fact sections on synthetic side (4 to 8 of 20) |

Why the judge guard requires all 3 judges to improve on the candidate:

- With product and agency names masked, each judge still sees that the 20 passages come from two
  document families: web/standards extracts with broken PDF columns and font icons vs continuous
  financial and incident narratives.
- Each judge assigns one label to an entire family, so its 20 verdicts are 100% correlated (`20`
  or `0`). Blocking promotion when two judges flip from `0` to `20` treats one binary family flip
  as 40 independent pairs. Therefore `realism_loop.decide` blocks only when **every** judge scores
  higher on the candidate than on the champion and mean error drops by more than `JUDGE_BAND`.

## 5. Remaining tensions for Round 3+

- **Thin-fact sections vs 300-word brief.** Sections with 2 to 3 facts (`ART-0007` incident RCA,
  `Close and assurance`, `Operations`, `Standing exposure`) still have a 300-word target. Writers
  pad them with reflective commentary ("That override is a person's action taken under time
  pressure, not a control"), which Masked Judges R2-1 and R2-3 flagged as "dramatic narrative
  tone".
- **Sentence opener concentration.** Writers occasionally reuse one subject noun phrase (`The
  finance team`, `The division`, `The cluster head`) at the start of 4 to 6 sentences in a document.

## 6. Files

| File | Purpose |
|---|---|
| `src/bigloom/realism_metrics.py` | The metric vector and the grader digest |
| `src/bigloom/realism_pairs.py` | Masked blind passage pair builder, scorer, and sample extractor |
| `src/bigloom/realism_loop.py` | Train/holdout preparation, build runner, promotion rule, and receipt writer |
| `src/bigloom/realism.py` | Per-file realism findings checked by `bigloom qualify` |
| `src/bigloom/formats/longform_filter.py` | The appendix and WorldLoom ID filter |
| `policies/PROPOSER.md` | Instructions for the proposer subagent |
| `policies/writer/round-001.md`, `round-002.md` | Versioned writer policies |
| `docs/realism/receipts/round0.json` .. `round2.json` | Full round receipts with samples and policy digests |
| `docs/realism/loop/train-002.json` | Train-only receipt visible to the proposer |
