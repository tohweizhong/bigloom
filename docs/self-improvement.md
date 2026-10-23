# Realism self-improvement loop: instructions

These are the instructions for the agent that runs the BigLoom realism loop (the orchestrator).
Follow them in order. This file holds instructions only. Results go to
[`docs/realism/loop-log.md`](realism/loop-log.md). Lessons for the proposer go to
[`docs/realism/lessons.md`](realism/lessons.md).

## 1. Goal

Make the DOCX, PDF, and PPTX files that BigLoom builds read like real Singapore agency documents.
The loop has two levels:

- **Level 1, the writer policy.** Each round changes one rule in the writer policy and keeps the
  change only when it wins on train and on holdout.
- **Level 2, the loop itself.** When Level 1 stops making progress, you find the cause and propose a
  change to the metrics, the corpus, or the procedure. The user must approve each Level 2 change.

## 2. Start of each session

1. Read the "Current state" and "Open items" sections of `docs/realism/loop-log.md`.
2. Run `git log --oneline -5` on `realism-loop` and on `realism-v2`. Make sure that they agree with
   the current state.
3. Make sure that `main` is at `ba4b981`.
4. Do the open items in order. Start a new round only when no open item blocks it.

### Branches and paths

| Item | Value |
|---|---|
| Run rounds from | The `realism-loop` checkout, `/usr/local/google/home/weizhongt/coding/bigloom` |
| Make Level 2 code changes on | `realism-v2`, worktree `/usr/local/google/home/weizhongt/coding/bigloom-v2` |
| Raw corpus cache | `runs/loop/cache` (one `seed-<n>` folder for each seed) |
| Real files for the judges | The path in "Current state" of `loop-log.md`. If it is missing, ask the user. |
| Champion vectors | The newest receipt for the champion under the current grader: a promotion receipt or a `rescore-*.json` receipt |

## 3. Hard rules

Stop and correct the work at once if you break one of these rules.

1. **One change.** A candidate policy changes one rule of the champion and nothing else.
2. **Holdout isolation.** No proposer message, proposer input, or file that the proposer reads
   contains a holdout seed (`3101`, `3102`), a holdout number, a holdout passage, or a decision that
   uses holdout data.
3. **Fresh writers.** Each round uses new writer subagents. A writer sees only the text of the
   candidate policy and its own requests. Never give a writer an earlier `responses.json`, and never
   tell a writer to copy earlier output.
4. **No code change during a run.** Do not change code while the writers or a build of a round run.
5. **Protected places.** Never commit or merge to `main`. Do not edit the WorldLoom repository. Do not
   upload files. Do not use Vertex AI. Every model role is a Jetski subagent.
6. **Real samples.** Each receipt holds two sample passages from the current round's train set.
7. **No facade work.** No dummy content and no facade tests. A new test must fail on the old code.
   Show the failing run.
8. **Writing.** Write in Simplified Technical English. Report each time in SGT (GMT+8).

## 4. Information barriers

| Role | May read | Must never read |
|---|---|---|
| Proposer subagent | Champion policy, `docs/realism/loop/train-*.json`, `docs/realism/lessons.md`, `policies/PROPOSER.md` | Anything under `runs/`, `docs/realism/receipts/`, `docs/realism/loop-log.md`, this file |
| Writer subagent | The candidate policy text, its own `requests.json` | Any other file under `runs/`, `policies/`, or `docs/` |
| Judge subagent | One `pairs.md` file | Receipts, policies, the answer key, file names |
| Orchestrator (you) | Everything | Nothing is forbidden, but never copy holdout data into a proposer input |

`policies/PROPOSER.md` must list the same proposer inputs as this table. If the two lists differ,
correct `PROPOSER.md` before the next proposal.

## 5. Round procedure (Level 1)

Round `N` uses `NNN` for the three-digit number, `runs/loop/r<NNN>t` for train, and
`runs/loop/r<NNN>h` for holdout. Train seeds are `realism_loop.TRAIN`. Holdout seeds are
`realism_loop.HOLDOUT`.

1. **Room check.** For each key in `realism_loop.BANDS`, compute the champion's train distance to
   `real_reference()` with `realism_loop.distances`. A metric has room when its distance is larger
   than its band. If no metric has room, do not start a round. Go to Level 2 (section 7).
2. **Propose.** Start a fresh proposer subagent. Give it `policies/PROPOSER.md`, the champion path,
   the output path `policies/writer/round-<NNN>.md`, and the list of metrics with room. Give it no
   number that you did not take from a train receipt. Check its output:
   - `diff <champion> policies/writer/round-<NNN>.md` shows one rule changed and nothing else.
   - `target_metric` is a key in `BANDS` and has room.
   - `why` cites a train number only.
   If a check fails, reject the proposal and start a new fresh proposer.
3. **Prepare.** Run `prepare_round(Path("runs/loop/r<NNN>t"), Path("runs/loop/cache"), TRAIN)` and
   `prepare_round(Path("runs/loop/r<NNN>h"), Path("runs/loop/cache"), HOLDOUT)`. The function
   deletes each `seed-<n>` folder and copies it again from the cache, without `responses.json`.
4. **Write.** Start one fresh writer subagent for each seed. Use this prompt and nothing more:

   > You write prose for synthetic documents. Follow this policy exactly: `<full policy text>`.
   > Read the requests in `<root>/seed-<n>/narration/requests.json`. Write one response for each
   > request to `<root>/seed-<n>/narration/responses.json`, in the format that the requests file
   > states. Do not read any other file.

5. **Fact gate.** For each seed, run
   `bigloom narrate accept --out-dir <root>/seed-<n> --from <root>/seed-<n>/narration/responses.json`.
   If a seed fails, start one new fresh writer for that seed and run the gate again. If it fails a
   second time, reject the round for the fact gate. Record the number of attempts for each seed as
   `writer_accept_rounds`.
6. **Length guard.** Count the words in each seed's `responses.json` prose as `agent_words`. Compare
   each seed with the champion's `agent_words` for the same seed. If a seed has less than 80% of the
   champion count, start one new fresh writer for that seed, then repeat step 5 for it. Apply the
   same rule to train and to holdout seeds. If the seed is still short, record a writer failure and
   reject the round.
7. **Build gate.** Run `build_round(Path("runs/loop/r<NNN>t"), TRAIN)` and
   `build_round(Path("runs/loop/r<NNN>h"), HOLDOUT)`. A gate violation rejects the round.
8. **Decide.** Call:

   ```python
   decide(champ_train, cand_train, champ_holdout, cand_holdout, real_reference())
   ```

   Use the vector from each `build_round` result and the champion vectors from section 2. Use the
   output as the decision. Never write a decision by hand.
9. **Judges (only if step 8 promotes).** Build pairs for the champion set and for the candidate set
   with `build_pairs(real_dir, synth_dir, out_dir, 20, seed)`. Use `<root>/set/large` of the train
   build as `synth_dir`, and the same `seed` for both sets. Keep the answer key in memory. Do not
   write it to disk until all judges reply. Start three fresh judge subagents for each set:

   > Read `<out_dir>/pairs.md`. Each pair has one real passage and one synthetic passage. For each
   > pair, reply with `{"pair": "P01", "real": "A"}` or `"B"`. Reply with a JSON list only.

   Count correct verdicts with `score(key, verdicts)` for each judge. Call `decide` again with
   `best_judge_correct` and `cand_judge_correct` (lists of three counts). Use this second decision.
10. **Record and promote.** Write the receipts (section 6). Commit them on `realism-loop` and push.
    If the decision promotes, the candidate becomes the champion. Update "Current state" in
    `loop-log.md`.

## 6. Receipts and records

After each round, write these files:

| File | Content | Proposer may read |
|---|---|---|
| `docs/realism/receipts/round<N>.json` | Full receipt (fields below) | No |
| `docs/realism/loop/train-<NNN>.json` | The full receipt with every holdout field, every holdout seed key, and `decision` removed | Yes |
| `docs/realism/loop-log.md` | One row in Appendix A, update to "Current state" | No |
| `docs/realism/lessons.md` | One row in "Loop v2 rounds" with train numbers only, plus any new lesson | Yes |

Fields of the full receipt:

| Receipt field | Source |
|---|---|
| `round`, `date_sgt` | The round number. `TZ=Asia/Singapore date '+%Y-%m-%d %H:%M'` |
| `champion_policy`, `champion_policy_sha256` | The champion path and `sha256sum` of it |
| `candidate_policy`, `candidate_policy_sha256` | The candidate path and `sha256sum` of it |
| `proposer_change` | The proposer's JSON reply |
| `writer_accept_rounds`, `agent_words` | Steps 5 and 6, one key for each seed |
| `grader_sha256` | `grader_sha256` from the `build_round` result |
| `gate_passed`, `gate_violations` | `gate_passed` and `violations` from both `build_round` results |
| `champion_train_vector`, `champion_holdout_vector` | The champion vectors from section 2 |
| `vector`, `holdout_vector` | `vector` from the train and the holdout `build_round` results |
| `per_file` | `files` from the train `build_round` result |
| `writer_notes` | Short notes from the writers, if any |
| `samples`, `samples_method` | `samples(Path("runs/loop/r<NNN>t/set/large"))`, and that call as text |
| `known_floors` | Floors from the newest rescore receipt, for example the cover abstract repeats |
| `decision` | The output of step 8, or of step 9 when the judges ran |

Check each new receipt before you commit it. These checks apply to receipts made under the current
grader. Do not apply them to old receipts.

- `grader_sha256` is the digest in "Current state". If the digest changed without an approved Level 2
  change, stop.
- `samples` holds exactly two passages. Each `file` exists in `runs/loop/r<NNN>t/set/large`.
- `candidate_policy_sha256` matches `sha256sum` of the policy file.
- `decision` is the unchanged output of `decide`.
- `grep -E "holdout|3101|3102|decision" docs/realism/loop/train-<NNN>.json` returns nothing.

A helper that returns an empty list or a zero count for a whole set is an error. Examine the input
path before you record the result.

## 7. Improve the loop (Level 2)

### When to start Level 2

Start Level 2 when one of these conditions is true:

- **No room.** The room check (section 5, step 1) finds no metric with room.
- **Plateau.** Three rounds in a row were rejected for the same reason.
- **Disagreement.** Train and holdout move in opposite directions on the same metric for two rounds.
- **Judges.** The masked judges still tell real from synthetic every time after a promotion.

### How to do Level 2

1. **Find the cause.** Look at the files, not only the vector. For each metric with a problem, list
   the sentences or phrases that cause it, and find which part of BigLoom or WorldLoom made them.
   Compare the requests that the writers got. A difference between seeds can come from the requests
   or from writer variance.
2. **Classify the cause.** The cause is one of: writer policy, writer requests, BigLoom corpus or
   renderer, grader, real reference, or procedure (seeds, number of writers).
3. **Propose one change to the user.** State the cause, the evidence, the change, the expected
   effect, the quota cost, and the test that will show it. Wait for approval.
4. **Make the change on `realism-v2`.** Add a test that fails on the old code. Show the failing run
   and the passing run. Do not change code while a round runs.
5. **Merge.** Merge `realism-v2` into `realism-loop` and push. Never merge into `main`.
6. **Measure the champion again.** Rebuild the champion prose on the merged code with no new writer
   runs. Write `docs/realism/receipts/rescore-v<k>-<NNN>.json` with the room check and the known
   floors. A rescore is not a round. Old and new receipts use different graders. Do not compare their
   numbers directly.
7. **Record.** Add the change and the rescore to `loop-log.md`. If the grader changed, write the new
   digest in "Current state". Add the lesson to `lessons.md` with train numbers only. Update
   `policies/PROPOSER.md` if the proposer needs to know the change.

### Order of the design changes

Propose these changes in this order, unless the evidence shows a better order:

1. **Repeat runs.** Run two writers on each seed and score the mean. The noise between two writers is
   larger than every band. This change doubles the writer quota for each round. State this cost
   when you ask the user.
2. **More train seeds.** Add new train seeds that are not holdout seeds. This measures the variance
   across more seeds, but it does not reduce the variance of one writer.
3. **A new signal for distance from real.** Add a metric that the judges' clues point to, for
   example prose density without padding, or the judge error rate as a scored metric.
4. **An archive of near misses.** Keep candidates that won on holdout but lost on train. Let the
   proposer start from one of them.

## 8. Stop and ask the user

Stop the loop and ask the user when one of these happens:

- A quota error (429) that does not clear at once. Report the reset time in SGT. Do not retry.
- A permission or credential error. Give the exact command that fixes it.
- The grader digest changes without an approved Level 2 change.
- A Level 2 condition is true (section 7).
- The review set is ready. Give the folder path and the file names.

## 9. Report

After each round or Level 2 change, report in five lines or fewer: the step, the result, the
decision, any rule break, and any blocker. Use SGT for every time.
