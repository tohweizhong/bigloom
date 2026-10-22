# Realism self-improvement loop

Status: first draft, 22 Oct 2026 23:35 SGT. It reports measured numbers only. Parts that do
not exist yet are marked **not built**.

BigLoom must make large files that read like real agency documents. This page describes the loop
that measures realism, the two rounds that have run, and the work that remains. The design follows
WorldLoom `evalrun improve`: change one policy, measure, and keep the change only when it wins on
documents that the proposer never saw.

## 1. Loop design

| Loop part | In BigLoom | State |
|---|---|---|
| Agent under test | The writer that answers WorldLoom narration requests (`bigloom narrate prepare`, then `accept`) | Built |
| Policy | The writer instructions (`runs/r1/writer_policy.md` in round 1). Later also pack fields. | Built (one fixed policy) |
| Hard gates, never optimized | `bigloom narrate accept` (WorldLoom claim checks), `bigloom qualify` (leakage, retrieval, realism findings), text and image fact depth | Built |
| Score | The metric vector (section 3) and the blind judge error rate (section 4) | Built |
| Proposer | An agent that reads the receipts and changes the policy | **Not built** |
| Holdout | A new seed and document types that the proposer never sees | **Not built** |
| Promotion rule | At least one dimension improves, no dimension falls by more than its band, and the holdout also gains | **Not built** |
| Receipt | One JSON file for each round in `docs/realism/receipts/` | Built |

Rules that apply to every round:

- The grader does not change during a loop. Each receipt records `grader_sha256`, the digest of
  `src/bigloom/realism_metrics.py`, and the digest of the judge prompt.
- The proposer never sees holdout passages or holdout results. The proposer is never a judge.
- All model roles are Jetski subagents. No Vertex AI.

## 2. What changed between round 0 and round 1

| Change | Round 0 | Round 1 |
|---|---|---|
| Writer | WorldLoom template writer (`ComposedProvider`) | Jetski writer subagent through the WorldLoom handshake |
| Appendix and ID filter | Off | On (`src/bigloom/formats/longform_filter.py`) |
| Build | `--sizes-mb 2,5 --formats docx,pdf,pptx --world-pack packs/govtech.json --seed 2026` | Same pack, seeds 2026 (2 MB) and 2027 (5 MB), same formats |
| WorldLoom pin | `53bb44a` | `53bb44a` |

In round 1, WorldLoom accepted the writer prose after 2 rounds (seed 2026, 4,861 words) and
1 round (seed 2027, 5,444 words). All six files passed `bigloom qualify`.

## 3. Metric vector

The metric vector has no model calls. All three columns use one grader
(`grader_sha256` `eeb607b3b32a…`). Rates are per 1000 words. Sentence reuse compares different
documents only: files of the same document type at two sizes are size twins and do not count.

| Metric | Real (11 files) | Round 0 (6 files) | Round 1 (6 files) |
|---|---|---|---|
| WorldLoom IDs per 1000 words | 0.0 | 20.5 | 0.0 |
| Commercial terms per 1000 words | 0.0 | 20.4 | 8.1 |
| Retail terms per 1000 words | 0.78 | 1.40 | 0.21 |
| Repeated sentences in one file | 4.0% | 16.0% | 4.4% |
| Most common three-word opener | 7.4% | 20.1% | 12.0% |
| Unique sentences per file | 146.7 | 30.5 | 51.3 |
| Sentence reuse across different documents | 0.1% | 6.6% | 0.0% |
| Dates after the document date | 0 | 0 | 0 |
| Words per MB | 4,032 | 443 | 442 |

The real set is 11 files from the SharePoint test site: 9 GovTech product and standards PDFs,
1 procedure manual (`.docx`), and 1 data protection officer guide (PDF).

Findings:

1. The filter removed all WorldLoom IDs. It also removed the ledger appendices, the hidden
   workbook "Lineage" sheet, and the IDs in file properties.
2. The writer brought repeated sentences down to 4.4%, close to the real 4.0%. Reuse across
   different documents fell to 0.0%.
3. Commercial terms remain at 8.1 per 1000 words. The GovTech pack uses `"base": "retail"`, so the
   facts are gross profit and gross margin. The PDF has about 10 and the deck about 13 per 1000 words.
4. The deck has a 29% opener share. The WorldLoom deck renderer builds slides from several documents.
5. Words per MB did not change. Padding sets the file size, so this metric does not measure the writer.

## 4. Blind judges

| Item | Round 0 | Round 1 |
|---|---|---|
| Pairs | 20 (seed 2026), 110 to 170 words each | 20 (seed 2026) |
| Judges | 3 subagents, model option `pro` | 3 subagents, model option `pro` |
| Prompt | Round 0 prompt | Round 0 prompt plus "A 2026 date is not a clue" (`prompt_sha256` `1f8fb661…`) |
| Correct verdicts | 60 of 60 | 60 of 60 |
| Judge error rate (goal 50%) | 0% | 0% |

The answer key stayed in the orchestrating conversation until all judges replied. The judges read
only the pairs file.

Round 1 clues, from the judges' own reasons:

| Clue | Judge 1 | Judge 2 | Judge 3 |
|---|---|---|---|
| Names of real public GovTech products or standards on the real side (SearchSG, Corppass, WOGAA, Singpass) | 14 of 20 | 0 | 16 of 20 |
| PDF extraction marks or template placeholders on the real side | 5 | 0 | 3 |
| Document type: a "fictional budget report" or "incident report" on the synthetic side | 1 | 15 of 20 | 1 |
| Narrative style or invented document furniture on the synthetic side | 0 | 5 | 0 |
| WorldLoom IDs, repeated sentences, or 2026 dates | 0 | 0 | 0 |

The round 0 clues (WorldLoom IDs, lineage tables, formulaic text, 2026 dates) did not appear in
round 1. The judge error rate stayed at 0% for a different reason: the reference set. The real
files are public web pages and standards. A judge can recognise real product names, and it can
tell a standards page from a finance report by type alone.

## 5. Limits

- **Reference set.** The judge test cannot rise above 0% error until the real set holds internal
  finance and incident documents of the same types as the synthetic set. Until then, the metric
  vector is the better guide.
- **Facts against length.** Several sections have 2 or 3 facts and a 300-word brief. The writers
  added sentences that cite no fact to reach the length.
- **Missing facts.** Some section purposes need facts that WorldLoom does not put in the request.
- **Commercial vocabulary.** It comes from the retail engine. WorldLoom has no public-sector domain.
- **Sample size.** Each round has 6 files from 2 worlds. The numbers are a baseline, not a trend.

## 6. Next work

1. Add real internal finance and incident documents to the reference set, and add a judge rule
   that a real product name is not a clue.
2. Build the proposer: it reads the receipts and changes one part of the writer policy. A first
   candidate change: allow shorter sections when a section has few facts.
3. Build the holdout: a new seed and document types that the proposer never sees, judged on
   model option `flash`.
4. Build the promotion rule and run one full loop round. Then update this page from first draft
   to final.
5. Test `"base": "procurement"` for the commercial terms, or ask the WorldLoom owner for a
   public-sector domain.

## 7. Files

| File | Purpose |
|---|---|
| `src/bigloom/realism_metrics.py` | The metric vector and the grader digest |
| `src/bigloom/realism.py` | Realism findings that the gate checks for each file |
| `src/bigloom/formats/longform_filter.py` | The appendix and ID filter |
| `src/bigloom/narration.py` | The handshake writer steps |
| `docs/realism/receipts/round0.json`, `round1.json` | Round receipts |
| `conductor/tracks/realism_loop_20261022/` | The Conductor track for this work |
