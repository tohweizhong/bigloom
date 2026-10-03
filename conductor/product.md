# Product Definition: BigLoom

## Vision
BigLoom builds large test files (such as 18 MB, 50 MB, and 100 MB) and test questions from a WorldLoom corpus. You use these files and questions to test enterprise connectors. BigLoom stops target leakage so that a question about a large file cannot get its answer from a small file or a search snippet.

## Four Steps
BigLoom runs offline in four steps:
1. **Build files (`bigloom build`):** Create large test files (`.docx`, `.xlsx`, `.pptx`, `.pdf`) at the file sizes you choose. For each large file, also create one small trap file (under 1 MB) on the same topic.
2. **Generate queries (`bigloom queries`):** Create the test questions, the right answers (`golden_value`), and the small-file trap answers (`canary_value`) in `cases.json`. Each question asks about one fact in one large file without naming the file. Every right answer and trap answer uses a high-entropy value (such as `SGD 4,827,319`, `38.47%`, or `Zone B-409`) so a model cannot guess it by chance.
3. **Qualify (`bigloom qualify`):** Check the files and questions before you upload them. Make sure each right answer is high-entropy, appears in only one file, and sits deep inside that file. For image questions, make sure the answer does not appear in the document text.
4. **Grade (`bigloom grade`):** Check the answers from your test run. Mark a pass only when the answer is right, cites the right file, and shows a file download call.

## How the Small-File Trap Works
For every large target file (for example, a 50 MB `FY2026` final report), BigLoom creates a small distractor file under 1 MB (for example, an `FY2025` draft note on the same project). Both files share the same topic keywords, so search returns both files. The large file holds the right answer (`golden_value`), and the small file holds a different, unique trap number (`canary_value`). If a connector fails to download the 50 MB file and reads the 0.4 MB file instead, the agent returns the trap number, and `bigloom grade` flags `CROSS_FILE_LEAK_CANARY`.

## How We Test BigLoom During Development
We do not need a live search or agent system to test BigLoom:
1. **Test `qualify` with bad files:** We make test files with known mistakes, such as the same answer in two files or on page 1. We check that `bigloom qualify` catches every mistake.
2. **Test `grade` with saved runs:** We run `bigloom grade` on test responses and on saved evaluation logs. We check that it catches wrong files, trap answers, and snippet-only answers.

## Outputs
BigLoom writes JSON and JSONL files (`manifest.jsonl`, `cases.json`, `qualification_report.json`, and `grade_report.json`).
