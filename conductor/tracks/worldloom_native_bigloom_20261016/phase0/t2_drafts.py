"""Phase 0, T2: list which document types have a superseded draft in the corpus.

Run from the BigLoom root:
    .venv/bin/python conductor/tracks/worldloom_native_bigloom_20261016/phase0/t2_drafts.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from worldloom.world import World

CORPUS = Path("runs/phase0/corpus")


def main() -> int:
    world = World.load(CORPUS)
    by_id = {i.id: i for i in world.artifact_intents}
    rendered: dict[str, set[str]] = defaultdict(set)
    for entry in world.artifacts:
        if entry.path:
            rendered[entry.artifact_type].add(Path(entry.path).suffix.lstrip("."))
    types: dict[str, dict[str, object]] = {}
    for intent in world.artifact_intents:
        row = types.setdefault(intent.artifact_type, {"count": 0, "drafts": 0, "copies": 0})
        row["count"] = int(row["count"]) + 1
    for intent in world.artifact_intents:
        if intent.revises and intent.revises in by_id:
            types[by_id[intent.revises].artifact_type]["drafts"] = int(types[by_id[intent.revises].artifact_type]["drafts"]) + 1
        for src in intent.derived_from or ():
            if src in by_id:
                types[by_id[src].artifact_type]["copies"] = int(types[by_id[src].artifact_type]["copies"]) + 1
    for name, row in types.items():
        row["formats"] = sorted(rendered.get(name, set()))
    print(json.dumps(dict(sorted(types.items())), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
