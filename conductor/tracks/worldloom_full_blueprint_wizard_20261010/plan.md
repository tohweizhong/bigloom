# Implementation Plan: Full WorldLoom Pack and Blueprint Configuration (`bigloom init`)

## Phase 1: Full WorldLoom Pack, Blueprint Facets/Locales, and Interactive Wizard
- [x] Task 1: Write unit tests in `tests/test_wizard.py` verifying zero `worldloom.packs.lint` findings on generated packs, `locale` and `facets` application in `build_corpus` and `load_world_entities`, and the advanced interactive `bigloom init` flow.
- [x] Task 2: Add `locale` and `facets` support to `src/bigloom/proposal/spec.py`, `src/bigloom/proposal/facts.py`, `src/bigloom/build.py`, and `src/bigloom/cli.py`.
- [x] Task 3: Expand `src/bigloom/wizard.py` (`build_org_pack_dict`, `write_org_pack_json`, `write_proposal_spec_yaml`, and `run_interactive_wizard`) with all WorldLoom pack fields, `facets`, `locale`, and `worldloom.packs.lint` validation.
- [x] Task 4: Update `README.md` with tables for WorldLoom pack fields, facets, locales, and landscapes.
- [x] Task 5: Run `pytest --cov=src/bigloom`, `ruff check .`, `validate_mermaid.py README.md`, and `check_git_hygiene.py .`.
