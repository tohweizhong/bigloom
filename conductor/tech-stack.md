# Technology Stack: BigLoom

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.11+ | Core runtime and type annotations. |
| **Build Backend** | Hatchling (`pyproject.toml`) | Package build and editable installation. |
| **CLI Framework** | Typer (`>=0.12`) | Command-line interface (`bigloom build`, `queries`, `qualify`, `grade`). |
| **Data Models and Specs** | Pydantic v2 (`>=2.7`), PyYAML (`>=6.0`) | Frozen, strict data contracts, YAML proposal specs, and JSON/JSONL serialization. |
| **World and Retrieval Base** | WorldLoom (`synthetic-foundry`) | Enterprise corpus facts, `native_artifacts` byte inspection, and `Bm25` / `TfIdf` rank checks. |
| **Office and PDF Files** | `python-docx`, `python-pptx`, `openpyxl`, `xlsxwriter`, `reportlab`, `pypdf` | Build and inspect `.docx`, `.pptx`, `.xlsx`, and `.pdf` documents. |
| **Image Synthesis** | Pillow (`>=10.0`) | Render charts and add light grain so ZIP compression does not shrink large files. |
| **Testing and Linting** | `pytest` (`>=8.0`), `ruff` (`>=0.4`) | Unit tests, negative leakage tests, and code formatting. |

## Stack Updates
- **06 Oct 2026 SGT:** Added `pyyaml>=6.0` for `bigloom proposal` YAML spec loading (`specs/*.yaml`).
- **14 Oct 2026 SGT:** Added `xlsxwriter>=3.2` and `reportlab>=4.0` Platypus for multi-sheet Excel workbooks and A4 PDF generation in `bigloom build`.
