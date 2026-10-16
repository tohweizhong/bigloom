"""Phase 0, T5: measure the template prose and check that two builds give the same text.

Run from the BigLoom root:
    .venv/bin/python conductor/tracks/worldloom_native_bigloom_20261016/phase0/t5_prose_quality.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from worldloom import prose_quality
from worldloom.world import World

CORPUS = Path("runs/phase0/corpus")
SECOND = Path("runs/phase0/corpus_second")
BUILD = [
    ".venv/bin/worldloom", "build", "--seed", "8128", "--incident", "--periods", "3",
    "--distractors", "4", "--realism", "enterprise", "--narrate", "--locale", "singapore",
    "--overwrite", "--out",
]


def prose_digest(world: World) -> str:
    """Return one SHA-256 digest over every narrated section body, in a fixed order."""
    h = hashlib.sha256()
    for ir in sorted(world.artifact_irs, key=lambda i: i.id):
        for sec in ir.sections:
            h.update(f"{ir.id}|{sec.heading}|{sec.body or ''}\n".encode())
    return h.hexdigest()


def main() -> int:
    world = World.load(CORPUS)
    reading = prose_quality.measure(world)
    fails = prose_quality.failures(reading)
    subprocess.run([*BUILD, str(SECOND)], check=True, capture_output=True)
    second = World.load(SECOND)
    report = {
        "reading": reading.as_dict() if hasattr(reading, "as_dict") else str(reading),
        "thresholds": {k: list(v) for k, v in prose_quality.THRESHOLDS.items()},
        "failures": fails,
        "digest_first": prose_digest(world),
        "digest_second": prose_digest(second),
    }
    report["same_text"] = report["digest_first"] == report["digest_second"]
    print(json.dumps(report, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
