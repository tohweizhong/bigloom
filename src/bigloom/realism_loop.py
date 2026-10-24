"""The realism improvement loop: sets, the promotion rule, and round receipts.

One round tests one candidate writer policy against the current best policy:

1. `prepare_round` copies a cached raw corpus (no prose) for each seed of the train set and
   the holdout set, and writes the WorldLoom requests of the candidate documents.
2. Writer subagents answer the requests under the candidate policy. `bigloom narrate accept`
   validates them (a hard gate).
3. `build_round` builds the targets with the handshake writer and runs `bigloom qualify` (a
   hard gate), then measures the metric vector with `realism_metrics`.
4. `decide` applies the promotion rule to the train and holdout vectors.

The proposer sees train receipts only. It never sees holdout passages or holdout numbers.
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

#: Size group (MB) to world seed. The train set matches round 1.
TRAIN: dict[float, int] = {2.0: 2026, 5.0: 2027}
#: New seeds that the proposer never sees.
HOLDOUT: dict[float, int] = {2.0: 3101, 5.0: 3102}
FORMATS: tuple[str, ...] = ("docx", "pdf", "pptx")
PACK = "packs/govtech.json"

#: Metric dimension to its band. A change smaller than the band is noise.
#: The score of a dimension is its distance from the real reference value (lower is better).
BANDS: dict[str, float] = {
    "wl_id_per_k": 0.5,
    "commercial_per_k": 0.5,
    "retail_per_k": 0.3,
    "within_file_repeat": 0.01,
    "top_opener_share": 0.01,
    "cross_document_reuse": 0.01,
}
#: Loop v2 does not score the raw `unique_sentences` count. A count grows with file length, and
#: the real median (39) comes from short files, so the count rewarded shorter files. Sentence
#: variety is scored as a rate by `within_file_repeat`. Receipts still report the count.
#: The judge guard: the candidate's judge error rate may not fall by more than this (6 of 60 verdicts).
JUDGE_BAND = 0.10
#: Loop v2 real reference: the median of the 11 real files (grader v2). The v1 mean was pulled
#: up by one 29,351-word DOCX, which put `unique_sentences` at 146.7 against a median of 39.
REFERENCE_V2 = Path(__file__).resolve().parents[2] / "docs" / "realism" / "reference-v2.json"


def real_reference(path: Path = REFERENCE_V2) -> dict[str, float]:
    """Return the loop v2 real reference vector (the median of the real files)."""
    return {k: float(v) for k, v in json.loads(path.read_text(encoding="utf-8"))["median"].items()}


@dataclass(frozen=True)
class Decision:
    """The result of the promotion rule."""

    promote: bool
    improved: tuple[str, ...]
    worsened: tuple[str, ...]
    holdout_gain: float
    reasons: tuple[str, ...] = field(default=())


def distances(vector: Mapping[str, float], real: Mapping[str, float]) -> dict[str, float]:
    """Return the distance from the real reference value for each loop dimension."""
    return {k: round(abs(float(vector[k]) - float(real[k])), 4) for k in BANDS}


#: Grader v3: the judge error rate is a scored dimension. Its real target is 0.5 (the judges cannot
#: tell real from synthetic). Its band is `JUDGE_BAND` (6 of 60 verdicts).
JUDGE_TARGET = 0.5


def judge_error(correct: Sequence[int] | None, pairs_per_judge: int = 20) -> float | None:
    """Return the judge error rate `1 - correct / (pairs x judges)`, or None without counts."""
    if not correct:
        return None
    return round(1 - sum(correct) / (pairs_per_judge * len(correct)), 4)


def decide(
    best_train: Mapping[str, float],
    cand_train: Mapping[str, float],
    best_holdout: Mapping[str, float],
    cand_holdout: Mapping[str, float],
    real: Mapping[str, float],
    best_judge_correct: list[int] | None = None,
    cand_judge_correct: list[int] | None = None,
    best_holdout_judge_correct: list[int] | None = None,
    cand_holdout_judge_correct: list[int] | None = None,
    gate_passed: bool = True,
) -> Decision:
    """Apply the promotion rule.

    Promote only when, on the train set, at least one dimension moves closer to the real value
    by more than its band and no dimension moves away by more than its band, and on the holdout
    set the summed normalised distance also falls.

    Grader v3: `judge_error` is one of the dimensions. Its distance is `|judge_error - 0.5|` and
    its band is `JUDGE_BAND`. It enters the train check when both train sides have judge counts,
    and the holdout gain when both holdout sides have them. A side without counts skips it.
    """
    bt, ct = distances(best_train, real), distances(cand_train, real)
    bh, ch = distances(best_holdout, real), distances(cand_holdout, real)
    bands = dict(BANDS)
    bj, cj = judge_error(best_judge_correct), judge_error(cand_judge_correct)
    if bj is not None and cj is not None:
        bands["judge_error"] = JUDGE_BAND
        bt["judge_error"], ct["judge_error"] = abs(bj - JUDGE_TARGET), abs(cj - JUDGE_TARGET)
    improved = tuple(k for k in bt if k in bands and round(bt[k] - ct[k], 6) > bands[k])
    worsened = tuple(k for k in bt if k in bands and round(ct[k] - bt[k], 6) > bands[k])
    hbj, hcj = judge_error(best_holdout_judge_correct), judge_error(cand_holdout_judge_correct)
    gain_terms = [(bh[k] - ch[k]) / BANDS[k] for k in BANDS]
    if hbj is not None and hcj is not None:
        gain_terms.append((abs(hbj - JUDGE_TARGET) - abs(hcj - JUDGE_TARGET)) / JUDGE_BAND)
    gain = round(sum(gain_terms), 3)
    reasons: list[str] = []
    if not gate_passed:
        reasons.append("build or fact gate failed")
    if not improved:
        reasons.append("no train dimension improved by more than its band")
    if worsened:
        reasons.append(f"train dimensions worsened beyond their band: {', '.join(worsened)}")
    if gain <= 0:
        reasons.append(f"holdout did not gain (normalised gain {gain})")
    return Decision(promote=not reasons, improved=improved, worsened=worsened, holdout_gain=gain, reasons=tuple(reasons))


def raw_corpus(cache: Path, seed: int) -> Path:
    """Return a cached corpus with no prose for `seed`, building it once."""
    from .narration import prepare

    target = cache / f"seed-{seed}"
    if not (target / "corpus" / "world.json").is_file():
        prepare(target, seed=seed, formats=FORMATS, world_pack=PACK)
    return target


def prepare_round(root: Path, cache: Path, seeds: Mapping[float, int]) -> dict[int, Path]:
    """Copy the cached raw corpus and its requests for each seed into `root/seed-<n>`."""
    out: dict[int, Path] = {}
    for seed in seeds.values():
        source = raw_corpus(cache, seed)
        dest = root / f"seed-{seed}"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)
        responses = dest / "narration" / "responses.json"
        if responses.exists():
            responses.unlink()
        out[seed] = dest
    return out


def build_round(root: Path, seeds: Mapping[float, int]) -> dict[str, Any]:
    """Build each size group from its narrated corpus, run the gate, and measure the vector.

    Return the gate result and the metric vector. The combined files are in `root/set`.
    """
    from .build import build_corpus
    from .models import EvalCase
    from .qualify import load_corpus_snapshots, qualify_corpus
    from .realism_metrics import metrics, summary

    combined = root / "set"
    if combined.exists():
        shutil.rmtree(combined)
    (combined / "large").mkdir(parents=True)
    manifest: list[str] = []
    violations: list[str] = []
    for size, seed in seeds.items():
        out = root / f"build-{seed}"
        if out.exists():
            shutil.rmtree(out)
        build_corpus(out, sizes_mb=(size,), seed=seed, formats=FORMATS,
                     corpus_dir=root / f"seed-{seed}" / "corpus", writer="handshake")
        cases = [EvalCase.model_validate(c) for c in json.loads((out / "cases.json").read_text(encoding="utf-8"))]
        report = qualify_corpus(load_corpus_snapshots(out), cases, check_retrieval=True)
        violations += [f"{v.case_id}: {v.code.value}" for v in report.violations]
        for f in (out / "large").iterdir():
            shutil.copy2(f, combined / "large" / f.name)
        manifest.append((out / "manifest.jsonl").read_text(encoding="utf-8").strip())
    (combined / "manifest.jsonl").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    result = metrics(combined)
    return {"gate_passed": not violations, "violations": violations, "vector": summary(result),
            "grader_sha256": result["grader_sha256"], "files": result["files"]}


def write_receipt(path: Path, payload: Mapping[str, Any]) -> None:
    """Write one round receipt as JSON."""
    data = {k: (asdict(v) if hasattr(v, "__dataclass_fields__") else v) for k, v in payload.items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
