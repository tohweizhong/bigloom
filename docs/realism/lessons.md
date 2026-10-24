# Realism loop lessons for the proposer

The proposer reads this file. It holds train results and lessons only. It holds no holdout seed, no
holdout number, and no holdout passage. The orchestrator updates it after each round, under the rules
in [`docs/self-improvement.md`](../self-improvement.md).

## What the metrics can and cannot show

- `commercial_per_k` counts the two-word phrases `gross profit`, `gross margin`, `operating margin`,
  `EBITDA`, and `sales volume`. The single word `margin` does not count.
- Loop v2 plants `gross surplus` and `surplus rate` in a public-sector pack. These phrases do not
  count as commercial.
- Loop v2 does not score the raw `unique_sentences` count. A count grows with file length. Receipts
  still report it.
- Most repeated sentences in the champion come from the PDF review record table and the cover
  abstract. The writer policy does not control them. A writer rule cannot lower
  `within_file_repeat` by a useful amount.

## Trade-offs seen in loop v1 (train numbers)

- **Shorter sentences add commercial phrases.** Rules for short sentences raised `unique_sentences`.
  Writers then named `gross profit` once in each new paragraph. Train `commercial_per_k` rose from 2.26
  to 4.78 (Round 5), 4.09 (Round 8), 3.48 (Round 14), and 6.47 (Round 15).
- **Fewer commercial phrases make long sentences.** Rules that cut commercial phrases made writers
  join facts into compound sentences of 25 to 30 words. Train `unique_sentences` fell from 48.8 to
  35.3 (Round 4), 31.2 (Round 11), and 38.5 (Round 13).
- **Fewer paragraphs hurt the PPTX in v1.** Each paragraph becomes one slide bullet. With fewer
  bullets, slide footers took a larger share of the openers. Grader v2 skips slide footers.
- **The word `margin` affects retrieval.** If the PDF and PPTX prose drop the word `margin`, the
  retrieval gate can fail for the DOCX chart query (Rounds 9, 10, 12). Keep the word `margin` in the
  prose where the facts support it.
- **Named sections fail.** Rules that name sections by title failed, because the section titles
  differ between documents (Round 11).

## Judge clues (masked judges, train passages)

The masked judges told real from synthetic in every pair after Rounds 2 and 11. Their clues:

- Synthetic side: a polished narrative tone, and capital letters in the middle of a sentence where a
  fact is joined into the text.
- Real side: PDF extraction marks, real external standards, and `.gov.sg` domains. The writer policy
  cannot change these real-side clues.

- **rs016 champion baseline (23 Oct 20:06 SGT, train passages, 3 fresh judges): 20, 20, and 20 of
  20 correct.** Commercial phrases did not appear as a clue. The judges named these clues:
  - The synthetic side comes from only two document families: a budget utilisation report (or
    Exco update) and an incident review about a stale code mapping.
  - The synthetic prose is polished and gives advice to a named role ("the cluster finance
    partner"). The incident review tells a neat story about a wrong theory, then closes on control
    failure and ownership.
  - One table repeats the same cell across all four columns.
  - The real side is varied operational text: design-standard controls, step guides, a security
    profile, threat tables, and product pages, with PDF extraction noise.

- **rescore-v2-017 (23 Oct 20:50 SGT, train passages, 3 fresh judges): 20, 20, and 20 of 20
  correct.** 15 of the 20 synthetic passages came from the PDF incident review, because the longest
  document gives the most passages. Only 3 came from the service impact assessment. The judges named:
  - One invented incident review (stale code mapping, SKU counts, manual override) and one finance
    Exco narrative, which repeat the same facts.
  - Reader-directed lines that tell the reader what to conclude ("Six months from now...",
    "Readers deciding whether to wait should...").
  - The real side: control tables with parameters, step guides, product pages, a security profile,
    and threat tables, with extraction noise.

- **rs017d champion (24 Oct 15:16 SGT, train passages, 6 fresh judges in two groups): 20 of 20 for
  every judge.** The judges named: one invented document pack with the same reference numbers,
  names, and figures in many pairs; field values copied word for word into the prose ("Manual agency
  code mapping override applied..."); smooth, argued essay prose ("It set the price", "a reader
  returning later"). The real side: guideline controls with parameter placeholders, step guides,
  product pages, a security profile, control tables, extraction noise.

## Writer behaviour

- One writer run for each seed is noisy. Under the same policy, two writers wrote 0 and 32 commercial
  phrases.
- Some writers wrote half the target length (Rounds 7 and 11). A length rule can help, but it also
  changed other metrics (Round 8).

## Rules tried in loop v1

| Round | Change | Result (train) |
|---|---|---|
| 2 | Name commercial measures at most once in a paragraph | Promoted. `commercial_per_k` 7.55 to 2.26 |
| 3 | Opener cap and thin-fact procedure rule | Rejected. Two rules in one round. |
| 4 | Each commercial word once in each section | Rejected. `unique_sentences` 48.8 to 35.3 |
| 5 | Sentences of 12 to 18 words | Rejected. `commercial_per_k` 2.26 to 4.78 |
| 6 | Opener cap of two in each document | Rejected. Process error. |
| 7 | Each commercial measure once in each section | Rejected. Writers wrote half length. |
| 8 | Word and sentence floor in each section | Rejected. `commercial_per_k` 2.26 to 4.09 |
| 9 | Commercial words once in each document | Rejected. Retrieval gate failed. |
| 10 | `gross margin` once in each section of one document | Rejected. Retrieval gate failed. |
| 11 | `gross margin` in three named sections | Rejected. `unique_sentences` 31.2 |
| 12 | Sentences of 12 to 16 words | Rejected. Retrieval gate failed. |
| 13 | `gross margin` in four named sections | Rejected. `unique_sentences` 48.8 to 38.5 |
| 14 | Two paragraphs of short sentences in each section | Rejected. `commercial_per_k` 3.48 |
| 15 | Short sentences of 13 to 17 words in three paragraphs | Rejected. `unique_sentences` 48.8 to 74.3, `commercial_per_k` 2.26 to 6.47 |

## Loop v2 rounds

No loop v2 round has run yet.
