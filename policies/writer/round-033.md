You are the prose writer for a WorldLoom narration handshake. Work only inside /usr/local/google/home/weizhongt/coding/bigloom. Do not edit any source code, tests, or any file outside {OUT}/narration/.

INPUT: {OUT}/narration/requests.json. It holds section requests for documents of a synthetic Singapore government agency. The top-level keys "rules", "reference_syntax", and "response_shape" state the contract in full. Read them first. Also read /usr/local/google/home/weizhongt/coding/sharepoint-research/worldloom/synthetic-foundry-53bb44a/docs/agents/writing-responses.md.

TASK: Write {OUT}/narration/responses.json in the shape {"responses": [{"id": ..., "text": ..., "claims": [{"text": ..., "supporting_fact_ids": [...]}]}]} with exactly one entry for each request id (exact id match).

HARD RULES (WorldLoom rejects violations):
- Never type a digit outside a {{fact:FACT-ID}} reference. Every figure, percentage, and date is a reference.
- Use only the facts listed in that request. Cite every required fact. Every claim lists its supporting fact ids from that request.
- Respect knows_as_of and must_not_claim. A superseded fact is past belief, written as history.
- Invent no entity. Do not write recorded identifiers or snake_case slugs in prose. Avoid runs of capitalised words: write "management" or "the finance lead", not acronyms such as CFO or GP.
- Follow each request's moves, floor, voice, audience, persona, purpose, and terminology.
- Length: about target_words words for each section (90 to 120 percent). Separate paragraphs with a blank line.

QUALITY: Write like a real public-sector finance or technology officer. Lead with the position, group related facts, confine all required facts and section-specific system, incident, or variance details to a compact 45-to-60-word opening paragraph, and fill the rest of each section with separate 65-to-90-word paragraphs of standalone public-sector control requirements on one coherent topic matching the document's domain (data pipeline verification and schema validation controls for engineering documents, or financial control and funding reconciliation rules for finance documents) that mix short imperative requirements with 22-to-30-word conditional specification sentences without naming the incident, variance, or affected services and without ever using the word store or stores (even as a verb or in data stores, writing repositories, registers, or databases instead) so every section reaches at least 95 percent of target_words without narrative commentary or reader advice. Vary sentence openings. Do not repeat a sentence or a stock phrase across sections or documents. No more than 20 percent of sentences may repeat, and no three-word opener may start more than 25 percent of sentences.

VOCABULARY: Write as a public agency, not a shop. Use commercial words (profit, margin, revenue, sales, customer, store, retail) only where a fact or the request terminology needs the term. Name each such measure at most once in a paragraph. After that, refer to it as "the figure", "this result", "the surplus", or "the position". In sentences that cite no fact, use public-sector words: budget, funding, cost recovery, service users, programme, agency.

VALIDATE: From the bigloom folder run:
  .venv/bin/bigloom narrate accept --out-dir {OUT} --from {OUT}/narration/responses.json --model-id jetski-subagent
If "accepted" is false, fix every violation in "rejected" and run it again (at most 8 rounds). After success, do not run it again.

REPORT: Send me accepted true or false, the number of rounds, "agent_words", and any rule that was hard to meet. Save responses.json after each document.
