# Technology Stack: BigLoom

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Language** | Python 3.11+ | Core runtime and type annotations. |
| **Build Backend** | Hatchling (`pyproject.toml`) | Package build and editable installation. |
| **CLI Framework** | Typer (`>=0.12`) | Command-line interface (`bigloom build`, `queries`, `qualify`, `grade`). |
| **Data Models** | Pydantic v2 (`>=2.7`) | Frozen, strict data contracts and JSON/JSONL serialization. |
| **World and Retrieval Base** | WorldLoom (`synthetic-foundry`) | Enterprise corpus facts, `native_artifacts` byte inspection, and `Bm25` / `TfIdf` rank checks. |
| **Office and PDF Files** | `python-docx`, `python-pptx`, `openpyxl`, `pypdf` | Build and inspect `.docx`, `.pptx`, `.xlsx`, and `.pdf` documents. |
| **Image Synthesis** | Pillow (`>=10.0`) | Render charts and add light grain so ZIP compression does not shrink large files. |
| **Testing and Linting** | `pytest` (`>=8.0`), `ruff` (`>=0.4`) | Unit tests, negative leakage tests, and code formatting. |
