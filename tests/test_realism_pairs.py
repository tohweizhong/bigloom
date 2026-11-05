"""Tests for the blind pair builder and name masking."""

from __future__ import annotations

from bigloom import realism_pairs as rp


def test_products_and_orgs_are_masked_consistently() -> None:
    text = "Log in with Singpass, then open Corppass. Singpass users of GovTech and the Government Technology Agency (Synthetic)."
    out = rp.mask_names(text)
    assert "Singpass" not in out and "Corppass" not in out and "GovTech" not in out
    import re

    tokens = re.findall(r"\[PRODUCT-\d\]", out)
    assert len(tokens) == 3 and len(set(tokens)) == 2  # the same name keeps one token
    assert "[ORG-1]" in out and "Synthetic" not in out


def test_extra_orgs_mask_world_names() -> None:
    out = rp.mask_names("The Product & Engineering cluster missed plan.", extra_orgs=["Product & Engineering"])
    assert out == "The [ORG-1] cluster missed plan."


def test_score_counts_correct_verdicts() -> None:
    key = {"P01": {"real": "A"}, "P02": {"real": "B"}}
    assert rp.score(key, [{"pair": "P01", "real": "A"}, {"pair": "P02", "real": "A"}]) == 1


def test_passages_drop_clues_and_short_lines() -> None:
    line = "This sentence has more than six words in it for the passage builder. "
    text = (line * 20) + "\nPage 3 of 9\nhttps://example.gov.sg/x\n"
    out = rp.passages(text)
    assert out and all("Page 3" not in p and "https" not in p for p in out)


def test_passages_keep_short_tail_of_wrapped_sentence() -> None:
    line = "This sentence has more than six words in it for the passage builder. "
    text = (line * 4) + "\nThe owner of the mapping table in the register is\nrecorded as unassigned.\n\n" + (line * 6)
    out = rp.passages(text)
    joined = " ".join(out)
    assert "the register is recorded as unassigned. This sentence" in joined
    assert "the register is This sentence" not in joined


def test_passages_still_drop_short_line_after_full_sentence() -> None:
    line = "This sentence has more than six words in it for the passage builder. "
    text = (line * 12) + "\nSection 4\n" + (line * 4)
    assert "Section 4" not in " ".join(rp.passages(text))


def test_passages_strip_url_page_ratios_on_wrapped_lines() -> None:
    line = "This sentence has more than six words in it for the passage builder. "
    text = (
        (line * 4)
        + "\nUsers can submit a request through the digital portal when\n"
        "https://www.tech.gov.sg/products/example/  6/8\n"
        "11/15/25, 10:28 PM                                           Document\n"
        "they need access to the service.\n\n"
        + (line * 6)
    )
    joined = " ".join(rp.passages(text))
    assert "6/8" not in joined
    assert "Document" not in joined
    assert "when they need access to the service." in joined


def test_passages_strip_oscal_parameter_tokens_and_parameter_table_rows() -> None:
    line = "This sentence has more than six words in it for the passage builder. "
    text = (
        (line * 4)
        + "\nAgencies must review their digital service at least every [ insert: param, pr-\n"
        "1_prm_1 ] day(s) and notify users at least [ insert: param, pr-4_prm_1 ] day(s) in advance.\n"
        "Ensure web-based services are compatible with the latest major versions of at least [\n"
        "insert: param, pr-6_prm_1 ] widely used web browsers, based on usage statistics.\n"
        "Remediate or risk accept findings within [ insert: param, uu-2_prm_1\n"
        "] day(s).\n"
        "pr- time period (days) The time period in days within which a digital service review must be\n"
        "1_prm_1 (int) conducted.\n"
        "uu- time period The time period in days to\n"
        "2_prm_1 (days) (int) remediate or risk accept\n"
        "findings.\n"
        "pr-4_prm_1 time period (days) (int) The time period in days to provide notice of schedule downtime.\n\n"
        + (line * 6)
    )
    joined = " ".join(rp.passages(text))
    assert "1_prm_1" not in joined
    assert "insert: param" not in joined
    assert "] days" not in joined
    assert "day(s)" not in joined
    assert "time period (days)" not in joined
    assert "(int)" not in joined


def test_passages_strip_sidebar_bleed_and_garbled_control_tables() -> None:
    line = "This sentence has more than six words in it for the passage builder. "
    text = (
        (line * 4)
        + "\nControls to establish credibility and build user trust Control in digital services.\n"
        "Reliability Understand and document Public Users' needs and context when creating a new digital service,\n"
        "Trust and Legitimacy redesigning existing services or introducing major features.\n"
        "WCAG : Register .gov.sg domain names through the service portal for all public websites.\n"
        "Perceivable Agencies must display the official masthead on every page of the portal.\n"
        "Table 2 – Identified threats on LLM applications by lifecycle.\n"
        "Dev1 Foundation / An attacker manipulates LLM Integrity Poison Training Data\n"
        "Table 3 – Recommended controls to mitigate corresponding threats.\n"
        "ED-C1 Harden Engineering Devices (Endpoints) Dev1 to Dev 3: IM8\n"
        "Perform engineering activities only through Fine-tuned\n"
        "Government Standard Image Build (GSIB2) or LLM poisoning\n"
        "3 Abstract Architecture ............................................................ 3\n"
        "Home Products and services For government agencies GovText\n"
        "Visit the portal to get started.                                          Chat with us\n"
        "Step 5: Click on 'Next' to proceed to the confirmation screen. 5\n\n"
        + (line * 6)
    )
    joined = " ".join(rp.passages(text))
    assert "WCAG :" not in joined
    assert "Control in digital" not in joined
    assert "Reliability Understand" not in joined
    assert "Trust and Legitimacy redesigning" not in joined
    assert "Perceivable Agencies" not in joined
    assert "Poison Training Data" not in joined
    assert "LLM poisoning" not in joined
    assert "...." not in joined
    assert "Home Products and services" not in joined
    assert "Chat with us" not in joined
    assert "screen. 5" not in joined


def test_passages_strip_real_corpus_extraction_artifacts() -> None:
    from pathlib import Path
    from bigloom.realism_metrics import text_of

    real_dir = Path("/usr/local/google/home/weizhongt/coding/bigloom/runs/realism/real")
    if not real_dir.is_dir():
        return
    for path in sorted(real_dir.iterdir()):
        if not path.is_file() or "SPP" in path.name or "DPO Registration" in path.name:
            continue
        joined = " ".join(rp.passages(text_of(path)))
        for bad in (
            "WCAG :",
            "Perceivable ",
            "Trust and Legitimacy redesigning",
            "Payments Use .gov.sg",
            "insert: param",
            "_prm_",
            "day(s)",
            "second(s)",
            "at least days in advance",
            "within days from detection",
            "....",
            "Threat ID",
            "Fine-tuned behaviour by altering",
            "OFFICIAL-OPEN",
            "Chat with us",
            "Home Products and services",
            "reach out to us at 17",
            "within .",
            "Step 2: Select “For Business Users”",
            "available to users .",
            "Have questions? Email us",
        ):
            assert bad not in joined, f"{path.name} leaked {bad!r}"
    u_passages = rp.passages(text_of(real_dir / "Understand Users.pdf"))
    assert len(u_passages) >= 2
    assert "Conduct usability testing at key milestones" in " ".join(u_passages)
    pr_joined = " ".join(rp.passages(text_of(real_dir / "Performance and Reliability.pdf")))
    assert "available to users 24/7." in pr_joined


def test_clean_line_strips_space_before_punctuation() -> None:
    raw = "The Government Technology Agency (Synthetic), acting as host, published the notice."
    assert rp._clean_line(raw) == "The Government Technology Agency, acting as host, published the notice."


def test_passages_flush_on_blank_lines_and_drop_headers_and_captions() -> None:
    sec1 = " ".join(
        [
            "Agencies must validate every schema before deploying a shared data service to production.",
            "Each integration team records the validation outcome in the release log before cutover.",
        ]
        * 5
    )
    sec2 = " ".join(
        [
            "Service owners must review access permissions every quarter and revoke dormant accounts promptly.",
            "System administrators archive the signed review sheet in the compliance repository.",
        ]
        * 5
    )
    text = (
        "1 Executive summary: schema governance and release controls\n\n"
        f"{sec1}\n\n"
        "2 Access review and quarterly audit controls\n\n"
        f"{sec2}\n\n"
        "4 Revised gross surplus forecast\n\n"
        "Table 4.1: Revised gross surplus forecast (SGD thousands)\n\n"
        "Source: March 2026 Board Pack; Finance Model (SGD thousands).\n\n"
        "Figure: Revised gross surplus forecast (SGD thousands) Bars: FY2025 Actual=1200.0, FY2026 Plan=1350.0\n"
    )
    out = rp.passages(text)
    assert len(out) >= 2
    joined = " ".join(out)
    for bad in (
        "1 Executive summary",
        "2 Access review",
        "4 Revised gross surplus forecast",
        "Table 4.1:",
        "Source: March 2026",
        "Figure: Revised gross surplus",
    ):
        assert bad not in joined, f"leaked {bad!r}"


def test_pool_excludes_spp_manual_and_dpo_guide(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from docx import Document

    body = "Agencies must validate every schema before deploying a shared data service to production. " * 15
    p_ok = tmp_path / "Understand Users.docx"
    p_spp = tmp_path / "spp model development procedure manual 2021 v5.0.docx"
    p_dpo = tmp_path / "DPO Registration Instruction Guide.docx"
    for p in (p_ok, p_spp, p_dpo):
        doc = Document()
        doc.add_paragraph(body)
        doc.save(str(p))
    pooled = rp._pool([p_ok, p_spp, p_dpo])
    names = {item[0] for item in pooled}
    assert names == {"Understand Users.docx"}


def test_level_2d_real_pool_has_no_extraction_splices_or_unmasked_tools() -> None:
    from pathlib import Path

    real_dir = Path("/usr/local/google/home/weizhongt/coding/bigloom/runs/realism/real")
    if not real_dir.is_dir():
        return
    pooled = rp._pool(sorted(p for p in real_dir.iterdir() if p.is_file()))
    assert len(pooled) >= 25
    masked_all = "\n".join(rp.mask_names(p[2]) for p in pooled)
    for bad in (
        "WU-9:",
        "service.Ensure",
        "Use.gov.sg",
        "Register.gov.sg",
        "and.edu.sg",
        "web-based.gov.sg",
        "Model-as-a- Service",
        "Use the Not required for",
        "architecture1",
        "+65 6211",
        "Choo Fai Cheong",
        "Hansard Analysis",
        "IM8 Q&A",
        "BrowserStack",
        "LambdaTest",
        "Google PageSpeed Insights",
        "Flesch Reading Ease",
        "Flesch-Kincaid",
        "Enabling efficient analyses of textual data",
        "Build government digital services quickly and securely",
        "key details about the Allowing",
        "colour(e.g.",
        "effective meet",
        "develops and maintain ",
        "when they are updates",
        "2.2. Locations where",
        "5.1. Types of Incidents",
        "current year in YYYY",
        "GovTech Act 2016",
        "RFC 2350",
        "IM8",
        "c) using web analytics",
    ):
        assert bad not in masked_all, f"leaked {bad!r}"


def test_build_pairs_prefers_2mb_final_files(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from docx import Document

    real_dir = tmp_path / "real"
    synth_dir = tmp_path / "synth"
    out_dir = tmp_path / "out"
    real_dir.mkdir()
    synth_dir.mkdir()

    real_doc = Document()
    real_doc.add_paragraph("Agencies must validate every schema before deploying a shared data service to production. " * 15)
    real_doc.save(str(real_dir / "real.docx"))

    doc_2mb = Document()
    doc_2mb.add_paragraph("Two megabyte target prose states the technical standard for agency deployment pipelines. " * 15)
    doc_2mb.save(str(synth_dir / "bl-001-docx-2mb_final.docx"))

    doc_5mb = Document()
    doc_5mb.add_paragraph("Five megabyte target prose states the duplicate world episode numbers across passages. " * 15)
    doc_5mb.save(str(synth_dir / "bl-001-docx-5mb_final.docx"))

    res = rp.build_pairs(real_dir, synth_dir, out_dir, 5, 18064)
    srcs = {v["synth_src"] for v in res["key"].values()}
    assert srcs == {"bl-001-docx-2mb_final.docx"}








