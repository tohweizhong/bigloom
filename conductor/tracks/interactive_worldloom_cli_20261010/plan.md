# Implementation Plan: Interactive WorldLoom Interface (`bigloom init`) and Custom Pack Documentation

## Phase 1: Custom Org-Pack Support and Interactive Wizard (`bigloom init`)
- [x] Task 1: Write unit tests in `tests/test_wizard.py` covering custom `.json` org-pack loading in `build_corpus` and `load_world_entities`, plus interactive `bigloom init` flows for both `proposal` and `corpus` modes.
- [x] Task 2: Update `src/bigloom/build.py` and `src/bigloom/proposal/facts.py` to apply `.pack(str(candidate))` when `world_pack` is a `.json` file on disk.
- [x] Task 3: Implement `src/bigloom/wizard.py` and wire `bigloom init` into `src/bigloom/cli.py`.
- [x] Task 4: Update `README.md` with the WorldLoom CLI overview, the four company input modes, and `bigloom init` usage examples.
- [x] Task 5: Run `pytest --cov=src/bigloom`, `ruff check .`, and `validate_mermaid.py README.md`.
