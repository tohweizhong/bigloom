# Deferred Design: Generalising the Large-File Builder

**Status:** Deferred. Do this after the first version of `bigloom proposal` works.
**Recorded:** 6 Oct 2026 SGT.
**Owner:** weizhongt.

## 1. Problem
The one-off script `sharepoint-research/worldloom/make_gsw_proposal.py` made a 200 MB
Greater Southern Waterfront (GSW) proposal and a 500 MB Tuas Port proposal. To make
them, the user had to give these inputs word for word:

- The organisation: GovTech (agency name, marking, names).
- The topic: GSW, then Tuas Port (title, context, site names).

The script holds many other choices in its code. A new organisation, topic, or document
type needs a code change. The approved spec for this track fixes only part of this.

## 2. What is fixed in code today

| Input | Where it is now | In the approved spec? |
|---|---|---|
| Organisation (agency, marking, names) | Imported from `make_large_files.py` | Yes, through `--org-pack` |
| Topic (title, context, site names, fact wording) | Python constants, plus a stopgap `TOPICS` dict and `--topic` flag | Partly. It moves to a YAML file that a person writes by hand. |
| Document type (funding proposal chapters and tables) | The chapter list for each topic | No |
| Plates (zoning plan, seawall, sensor plan, render, phasing, cost) | Six drawers for urban planning and ports | No |
| Currency, voice, spelling (SGD, British English) | Text in the Gemini prompt | No. The WorldLoom pack has `currency` and `voices`, but the spec does not use them. |
| Text and image mix | Fixed. Plates make the bytes, about 1 plate for each section. | No |

## 3. Target design: five layers

1. **Organisation pack (who).** Reuse WorldLoom packs, for example `govtech-pack.json`.
   BigLoom already reads packs in `bigloom build --world-pack`. Add the pack currency,
   voice, and marking to the prompt.
2. **Topic brief (what).** The user gives one line, for example "Tuas Port digital twin
   funding proposal". Gemini writes a draft topic YAML: title, context, site names,
   plate words, and fact wording. A person reviews it once. After that, the YAML is
   fixed and the build is repeatable.
3. **Document type (shape).** Templates that the user can reuse: funding proposal, annual
   report, tender specification, audit report, and board paper. Each template holds its
   chapter skeleton, standard tables, and the place of the middle facts.
4. **Plate library (visuals).** General plate types: bar chart, line chart, phasing chart,
   table image, site map, render, diagram, and organisation chart. The topic file gives
   the words. Domain drawers, for example the seawall cross-section, become optional.
5. **Size profile (how big).** Target bytes, file type, and the text and image mix. Keep
   the mix as words for each MiB, so a larger file gets more text and more plates.

Target command, for example:

    bigloom proposal --org-pack govtech-pack.json --brief "Tuas Port digital twin" \
        --doc-type proposal --target-bytes 500MiB

## 4. Measured reference points

| File | Size | Words | Plates | Prose time | Build time | Peak memory |
|---|---|---|---|---|---|---|
| GSW proposal | 201.8 MiB | 126,290 | 96 | 7 min 40 s (8 workers) | 74 s (2 builds) | 2.7 GB |
| Tuas Port proposal | 500 MiB target | about 310,000 target | 240 | In progress | In progress | In progress |

## 5. Known facts for the design
- SharePoint changes an uploaded `.docx`. It adds `docProps/custom.xml`, `customXml/`
  parts, and `[trash]/` entries, and it changes the relationship files. The text and the
  images stay identical. Record the SHA-256 of the original file, not of a SharePoint copy.
- Prose compresses a lot inside a `.docx`. Plates with grain make the bytes. A file where
  text makes most of the bytes is not realistic and is out of scope.

## 6. Open questions
1. Must the topic brief step run in the same command, or as a separate `bigloom topic` command?
2. Which document types come first after the funding proposal?
3. Must `.pptx` and `.pdf` use the same topic file and plate library?
