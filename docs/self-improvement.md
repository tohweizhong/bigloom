# Realism self-improvement loop

Status: updated after Round 11, 23 Oct 2026 02:33 SGT. Every part of the loop is built and has run
end-to-end across eleven rounds. This page reports measured numbers and cites the round receipts.

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
| Round 3 | Jetski writer subagent (`policies/writer/round-003.md`, `b739d290…`) | On | Cap three-word openers at two per document and direct thin-fact sections to use dry administrative procedure | **Rejected** (`round3.json`; hard gate failed on `bl-001-docx-5mb-text` rank 4, `unique_sentences` fell from `48.8` to `36.8`, and `commercial_per_k` rose from `2.26` to `4.96`) |
| Round 4 | Jetski writer subagent (`policies/writer/round-004.md`, `b10737ef…`) | On | Cap each commercial word at one use per section across all formats | **Rejected** (`round4.json`; passed all hard gates, improved train `top_opener_share` from `13.0%` to `9.0%`, and gained `+3.669` on holdout, but longer compound sentences reduced train `unique_sentences` from `48.8` to `35.3`) |
| Round 5 | Jetski writer subagent (`policies/writer/round-005.md`, `69b1350e…`) | On | Keep sentences concise (`12` to `18` words) so each 300-word section holds at least 18 sentences | **Rejected** (`round5.json`; passed all hard gates, improved train `unique_sentences` from `48.8` to `65.8`, and gained `+8.279` on holdout, but more paragraphs per section caused train `commercial_per_k` to rise from `2.26` to `4.78` under the once-per-paragraph vocabulary rule) |
| Round 6 | Jetski writer subagent (`policies/writer/round-006.md`, `41278114…`) | On | Cap three-word sentence openers at two per document and require distinct three-word openings across slide sections | **Rejected** (`round6.json`; passed all hard gates, improved train `unique_sentences` from `48.8` to `65.8`, lowered `cross_document_reuse` to `0.0%`, and gained `+9.543` on holdout, but reusing the Seed `2027` writer conversation carried over Round 5's `4.78` `commercial_per_k`) |
| Round 7 | Jetski writer subagent (`policies/writer/round-007.md`, `5fd47221…`) | On | Cap each commercial measure at one use per section across all formats (with fresh writer subagents) | **Rejected** (`round7.json`; passed all hard gates and improved `retail_per_k` (`0.69`) and `top_opener_share` (`11.5%`), but fresh writers wrote ~`2,600` words per seed instead of ~`5,000`, reducing `unique_sentences` to `29.2` and raising `commercial_per_k` per 1000 words to `5.84`) |
| Round 8 | Jetski writer subagent (`policies/writer/round-008.md`, `8c9f8b23…`) | On | Require `95` to `115` percent of `target_words` for every section (`>= 285` words and `16` to `20` sentences per `300`-word section, `>= 4,800` words per seed) | **Rejected** (`round8.json`; passed all hard gates, improved train `top_opener_share` (`11.5%`) and `unique_sentences` (`58.0`), and gained `+5.173` on holdout, but Seed `2027` named commercial measures across multiple paragraphs per section (`commercial_per_k` `4.09` vs `2.26`)) |
| Round 9 | Jetski writer subagent (`policies/writer/round-009.md`, `e940cc6a…`) | On | Cap commercial words at one use per document (at most three across all 21 sections) | **Rejected** (`round9.json`; won on every metric vector dimension—train `commercial_per_k` `2.09`, `top_opener_share` `11.2%`, `unique_sentences` `58.2`, holdout gain `+11.423` with `commercial_per_k` `2.00`—but removing `gross margin` from the DOCX dropped `bl-001-docx-5mb_final.docx` to BM25 rank 4 on `bl-001-docx-5mb-image`) |
| Round 10 | Jetski writer subagent (`policies/writer/round-010.md`, `db8c8714…`) | On | Write `gross margin` once in each section of `ART-0019` while avoiding commercial words in all other documents | **Rejected** (`round10.json`; improved train `top_opener_share` (`11.2%`) and `unique_sentences` (`58.2`) with holdout gain `+10.817`, but `bl-001-docx` is built from `ART-0007` rather than `ART-0019`, and removing `margin` from the PDF raised its BM25 IDF so the PPTX outranked `bl-001-docx-5mb_final.docx` on `bl-001-docx-5mb-image`) |
| Round 11 | Jetski writer subagent (`policies/writer/round-011.md`, `75139cfa…`) | On | Write `gross margin forecast` once in `ART-0007/Standing exposure` and `gross margin` once in `ART-0020/Summary` and `ART-0024/Headline` while avoiding all other commercial words across all 21 sections | **Promoted** (`round11.json`; passed all hard gates, improved train `top_opener_share` (`13.0%` -> `11.2%`) and `unique_sentences` (`48.8` -> `58.2`) with zero worsened dimensions, lowered holdout `commercial_per_k` from `6.30` to `2.27`, gained `+10.893` on holdout, and passed the masked blind judge guard) |

## 3. Metric vector

The metric vector uses no model calls. All columns use the same grader
(`grader_sha256` `eeb607b3b32a…`). Rates are per 1000 words. Sentence reuse compares different
documents only; size twins (the same document type at 2 MB and 5 MB) do not count.

| Metric | Real (11 files) | Round 0 Train | Round 1 Train | Round 2 Train | Round 5 Train | Round 8 Train | Round 9 Train | Round 10 Train | Round 11 Train (Champion) | Round 1 Holdout | Round 2 Holdout | Round 5 Holdout | Round 8 Holdout | Round 9 Holdout | Round 10 Holdout | Round 11 Holdout (Champion) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| WorldLoom IDs per 1000 words | 0.0 | 20.50 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.00** | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | **0.00** |
| Commercial terms per 1000 words | 0.0 | 20.44 | 7.55 | **2.26** | 4.78 | 4.09 | **2.09** | **2.09** | **2.36** | 7.19 | 6.30 | 2.33 | 5.16 | **2.00** | 2.30 | **2.27** |
| Retail terms per 1000 words | 0.78 | 1.40 | 0.21 | 0.21 | 0.21 | 0.18 | 0.18 | 0.18 | 0.18 | 0.20 | 0.23 | 0.24 | 0.19 | 0.19 | 0.19 | 0.19 |
| Repeated sentences in one file | 4.0% | 16.0% | 4.4% | 3.9% | 3.7% | **3.4%** | **3.4%** | **3.4%** | **3.4%** | 3.9% | 4.0% | 5.1% | 3.8% | **3.4%** | **3.4%** | **3.4%** |
| Most common three-word opener | 7.4% | 20.1% | 12.0% | 13.0% | 13.1% | 11.5% | **11.2%** | **11.2%** | **11.2%** | 12.6% | 13.5% | 13.0% | 11.3% | **11.0%** | **11.0%** | **11.0%** |
| Unique sentences per file | 146.7 | 30.5 | 51.3 | 48.8 | **65.8** | 58.0 | 58.2 | 58.2 | **58.2** | 57.2 | 52.0 | 56.5 | 57.2 | **57.3** | **57.3** | **57.3** |
| Sentence reuse across different documents | 0.1% | 6.6% | 0.0% | 0.0% | 0.5% | 0.0% | 0.0% | 0.0% | **0.0%** | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | **0.0%** |
| Dates after the document date | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| Words per MB | 4,032 | 443 | 440 | 435 | 431 | 466 | 467 | 467 | **467** | 450 | 390 | 414 | 491 | 491 | 491 | **492** |

Findings after Round 11:

1. **Commercial terms dropped by 70% in Round 2 (`7.55` to `2.26` on train, `7.19` to `6.30` on
   holdout).** On train, the PDF rate fell from `9.11`/`8.77` to `4.14`/`3.04`, and the deck rate
   fell from `12.53`/`13.64` to `2.56`/`2.55`.
2. **Repeated table cells fixed (`2e2fa95`).** In Round 1, Masked Judge 1 spotted that BigLoom's
   planted text-fact table repeated the measure label twice in the same row (`row.label` and
   `cells["measure"]`). Making the table single-column (`Value`) removed that clue and lowered
   Round 1 train `commercial_per_k` from `8.05` to `7.55`.
3. **Why Round 3 was rejected.** The Round 3 policy (`round-003.md`) changed two rules at once. It
   lowered `top_opener_share` on holdout (`13.5%` to `9.9%`), but writers produced shorter prose,
   which reduced `unique_sentences` from `48.8` to `36.8`, raised `commercial_per_k` to `4.96`, and
   pushed `traps/bl-001-docx-5mb_draft.docx` to BM25 rank 4 on `bl-001-docx-5mb-text`.
4. **Why Round 4 was rejected.** Starting from `round-002.md` with one rule change (`round-004.md`),
   both train and holdout passed all hard gates, train `top_opener_share` improved from `13.0%` to
   `9.0%`, and holdout gained `+3.669` (`commercial_per_k` dropped from `6.30` to `2.24`). However,
   writers used longer compound sentences (`29` to `35` words per sentence vs `21` to `26` in Round
   2), which lowered train `unique_sentences` from `48.8` to `35.3` (beyond the `5.0` band).
5. **Why Round 5 was rejected.** Starting from `round-002.md` with one rule change (`round-005.md`:
   keep sentences `12` to `18` words so each 300-word section has at least 18 sentences), both train
   and holdout passed all hard gates, train `unique_sentences` jumped from `48.8` to `65.8` (`+17.0`
   sentences per file), and holdout gained `+8.279` (`commercial_per_k` fell from `6.30` to `2.33`
   and `unique_sentences` rose from `52.0` to `56.5`). However, on train seed `2027`, shorter
   sentences caused the writer to split sections into more paragraphs while still naming a
   commercial measure once per paragraph (`round-002.md`'s rule), raising train `commercial_per_k`
   from `2.26` to `4.78`.
6. **Why Round 6 was rejected and what it revealed.** Starting from `round-002.md` with one rule
   change (`round-006.md`: cap three-word openers at two per document and require distinct slide
   section openings), holdout gained `+9.543` (`commercial_per_k` `2.24`, `top_opener_share`
   `12.3%`, `unique_sentences` `57.0`). However, because we messaged the existing writer subagents
   instead of spawning fresh subagents, the Seed `2027` writer reused its Round 5 text in context,
   carrying over Round 5's `4.78` `commercial_per_k`.
7. **Why Round 7 was rejected.** Starting from `round-002.md` with one rule change (`round-007.md`:
   cap commercial terms at once per section) and four fresh writer subagents, both gates passed and
   `retail_per_k` (`0.69` vs `0.78` real) and `top_opener_share` (`11.5%` vs `13.0%`) improved.
   However, because WorldLoom `narrate accept` does not enforce the `target_words` floor (`90%` to
   `120%`), the fresh writers wrote `2,523` to `2,785` total words per seed instead of `4,899` to
   `5,486`, which cut `unique_sentences` to `29.2` and increased the per-1000-word commercial term
   density (`5.84`).
8. **Why Round 8 was rejected.** Starting from `round-002.md` with one rule change (`round-008.md`:
   explicit `95%` to `115%` word and sentence floor per section), all four fresh writers wrote full
   lengths (`5,188` to `6,254` words per seed), both gates passed, train `top_opener_share` improved
   (`13.0%` to `11.5%`), train `unique_sentences` improved (`48.8` to `58.0`), and holdout gained
   `+5.173`. However, on Seed `2027` (`5 MB` train), `round-002.md`'s unmodified `VOCABULARY` line
   ("Name each such measure at most once in a paragraph") allowed the writer to use commercial nouns
   across each paragraph of the PDF and PPTX (`8.70` and `8.81` per 1000 words vs `3.61` and `2.31`
   on Seed `2026`), raising train `commercial_per_k` to `4.09`.
9. **Why Round 9 and Round 10 were rejected and the BM25 IDF discovery.** In Round 9 (`round-009.md`)
   and Round 10 (`round-010.md`), capping commercial words won on every metric vector dimension
   (`commercial_per_k` `2.09` on train and `2.00` to `2.30` on holdout, `top_opener_share` `11.2%` on
   train and `11.0%` on holdout, `unique_sentences` `58.2` on train and `57.3` on holdout, holdout
   gain `+11.423` and `+10.817`, zero worsened dimensions). However, `bl-001-docx-5mb-image` ("what
   gross margin forecast does the chart Revised gross margin forecast by business unit show for
   Product & Engineering?") failed its BM25 top-3 retrieval check because `bl-001-docx` is built from
   `ART-0007` (the Incident RCA) rather than `ART-0019`, and removing `margin` from the PDF (`df`
   dropping from `6` to `4`) increased the BM25 IDF of `margin` so the shorter PPTX files (whose chart
   titles contain `margin`) outscored the DOCX (`gross: 1, margin: 1`).
10. **Why Round 11 was promoted as the new champion (`round-011.md`).** Starting from `round-002.md`
    with one rule change in `VOCABULARY`—writing `gross margin forecast` once in `ART-0007/Standing
    exposure` (the DOCX Incident RCA) and `gross margin` once in `ART-0020` (PDF) and `ART-0024` (PPTX)
    while avoiding all other commercial words across all 21 sections—Round 11 passed every hard
    qualification and retrieval gate on both train and holdout. On train, `top_opener_share` improved
    from `13.0%` to `11.2%` and `unique_sentences` jumped from `48.8` to `58.2` with zero worsened
    dimensions (`commercial_per_k` `2.36` vs `2.26` is within the `0.50` band). On holdout,
    `commercial_per_k` dropped by 64% (`6.30` to `2.27`), `top_opener_share` dropped from `13.5%` to
    `11.0%`, `unique_sentences` rose from `52.0` to `57.3`, and normalised holdout gain reached
    `+10.893`. All three masked blind judges ran on Round 11 (`[20, 20, 20]`), passing the judge guard.
    `policies/writer/round-011.md` is now the promoted champion policy.

## 4. Blind judges and correlated series behaviour

| Round | Masking | Correct verdicts (3 judges) | Mean error rate (goal 50%) | Main clues reported by judges |
|---|---|---|---|---|
| Round 0 | Unmasked | `[20, 20, 20]` (60/60) | 0.0% | WorldLoom IDs, lineage tables, formulaic templates, 2026 dates |
| Round 1 | Unmasked | `[20, 20, 20]` (60/60) | 0.0% | Real public GovTech product/framework names on real side (14 to 18 of 20), document type (15 of 20); 0 mentions of WorldLoom IDs, repeats, or 2026 dates |
| Round 1 | Masked (`[PRODUCT-n]`, `[ORG-n]`) | `[20, 0, 0]` (20/60) | 66.7% | Each judge grouped the 20 pairs into two document series; two judges inverted which series was real |
| Round 2 | Masked (`[PRODUCT-n]`, `[ORG-n]`) | `[20, 20, 20]` (60/60) | 0.0% | PDF column/font/table extraction marks and control codes on real side (12 to 13 of 20); dramatic or polished narrative tone in thin-fact sections on synthetic side (4 to 8 of 20) |
| Round 11 | Masked (`[PRODUCT-n]`, `[ORG-n]`) | `[20, 20, 20]` (60/60) | 0.0% | Real external standards/domains (DSS, NIST 800-53, MITRE ATLAS, RFC 2350, ACRA BizFile+, `.gov.sg`) and PDF glyph marks on real side (15 to 17 of 20); mid-sentence capitalised fact splices and document family grouping on synthetic side (3 to 5 of 20) |

Why the judge guard requires all 3 judges to improve on the candidate:

- With product and agency names masked, each judge still sees that the 20 passages come from two
  document families: web/standards extracts with broken PDF columns and font icons vs continuous
  financial and incident narratives.
- Each judge assigns one label to an entire family, so its 20 verdicts are 100% correlated (`20`
  or `0`). Blocking promotion when two judges flip from `0` to `20` treats one binary family flip
  as 40 independent pairs. Therefore `realism_loop.decide` blocks only when **every** judge scores
  higher on the candidate than on the champion and mean error drops by more than `JUDGE_BAND`.

## 5. Remaining tensions for Round 12+

- **Mid-sentence capitalised fact splices.** Masked Judge R11-3 noted that when a WorldLoom fact
  statement starts with a capital letter (`Asset valuation completed`, `ERP logs show no interruption`),
  placing `{{fact:FACT-ID}}` in the middle of a sentence produces a mid-sentence capital letter.
  Placing sentence-valued facts at the start of a sentence (or after a colon) removes that splice.
- **Sentence opener concentration in slide decks.** On PPTX slides (`ART-0024`), `top_opener_share` is
  `0.278` to `0.294` because two or three sentences in the deck share the same three-word opener.
  Requiring every sentence in a slide deck to begin with a distinct three-word opener can lower
  `top_opener_share` below `0.10` across the set.

## 6. Files

| File | Purpose |
|---|---|
| `src/bigloom/realism_metrics.py` | The metric vector and the grader digest |
| `src/bigloom/realism_pairs.py` | Masked blind passage pair builder, scorer, and sample extractor |
| `src/bigloom/realism_loop.py` | Train/holdout preparation, build runner, promotion rule, and receipt writer |
| `src/bigloom/realism.py` | Per-file realism findings checked by `bigloom qualify` |
| `src/bigloom/formats/longform_filter.py` | The appendix and WorldLoom ID filter |
| `policies/PROPOSER.md` | Instructions for the proposer subagent |
| `policies/writer/round-001.md` .. `round-011.md` | Versioned writer policies (`round-011.md` is the promoted champion) |
| `docs/realism/receipts/round0.json` .. `round11.json` | Full round receipts with samples and policy digests |
| `docs/realism/loop/train-002.json` .. `train-011.json` | Train-only receipts visible to the proposer |
