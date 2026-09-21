"""Regression tests for RuleBasedCVParser against text shaped the way pypdf
actually extracts it from a real PDF — notably: no blank lines between
paragraphs (pypdf drops empty paragraphs that DOCX preserves), and long
lines hard-wrapped at the page width, sometimes mid-parenthetical. These
are real bugs found by converting a CV to an actual PDF (via LibreOffice)
and running it through the upload pipeline — see the fix in
app/services/cv_parser/rule_based.py (_merge_wrapped_parens, _group_entries).
"""

from app.models.enums import SeniorityLevel
from app.services.cv_parser.rule_based import (
    RuleBasedCVParser,
    _group_entries,
    _guess_primary_specialty,
    _merge_wrapped_parens,
)

# Captured verbatim from `SELECT raw_text FROM candidate_cvs` after uploading
# a real LibreOffice-generated PDF — no blank lines, and the education date
# range is wrapped mid-parenthesis exactly as pypdf produced it.
PYPDF_STYLE_RAW_TEXT = """Nguyen Van Test
nguyenvantest@example.com
+84 901 234 567
Ho Chi Minh City
SUMMARY
Backend engineer with 6 years of experience building scalable APIs and
RAG systems using Python and FastAPI.
SKILLS
Python, FastAPI, LangChain, RAG, LLM, PostgreSQL, Docker, AWS, Qdrant
WORK EXPERIENCE
Senior Backend Engineer at Tech Corp (Jan 2021 - Present)
Built a RAG-based question answering system serving 10k+ users using
FastAPI, LangChain and Qdrant.
Backend Engineer at StartupX (Jun 2018 - Dec 2020)
Developed microservices in Python and deployed on AWS with Docker.
EDUCATION
Bachelor of Science, Ho Chi Minh City University of Technology (2014 -
2018)
"""


def test_merge_wrapped_parens_rejoins_a_date_range_split_across_lines():
    lines = ["Some School (2014 -", "2018)", "Next line"]
    merged = _merge_wrapped_parens(lines)
    assert merged == ["Some School (2014 - 2018)", "Next line"]


def test_merge_wrapped_parens_leaves_balanced_lines_untouched():
    lines = ["Position at Company (Jan 2021 - Present)", "A description line."]
    assert _merge_wrapped_parens(lines) == lines


def test_group_entries_splits_on_date_header_when_no_blank_lines():
    # This is exactly what pypdf produces: no blank line between entries.
    lines = [
        "Senior Backend Engineer at Tech Corp (Jan 2021 - Present)",
        "Built a RAG-based question answering system.",
        "Backend Engineer at StartupX (Jun 2018 - Dec 2020)",
        "Developed microservices in Python.",
    ]
    blocks = _group_entries(lines)
    assert len(blocks) == 2
    assert blocks[0][0].startswith("Senior Backend Engineer")
    assert blocks[1][0].startswith("Backend Engineer at StartupX")
    # the first entry's description must not have swallowed the second entry
    assert "StartupX" not in " ".join(blocks[0][1:])


def test_group_entries_still_works_with_blank_line_separated_input():
    lines = [
        "Position A at Company A (2020 - 2021)",
        "Description A",
        "",
        "Position B at Company B (2021 - 2022)",
        "Description B",
    ]
    blocks = _group_entries(lines)
    assert len(blocks) == 2


def test_rule_based_parser_handles_real_pdf_shaped_text():
    parsed = RuleBasedCVParser().parse(PYPDF_STYLE_RAW_TEXT)

    assert len(parsed.work_experience) == 2
    first, second = parsed.work_experience
    assert first.company == "Tech Corp"
    assert first.position == "Senior Backend Engineer"
    assert first.is_current is True
    assert "StartupX" not in (first.description or "")

    assert second.company == "StartupX"
    assert second.position == "Backend Engineer"
    assert second.start_date.isoformat() == "2018-06-01"
    assert second.end_date.isoformat() == "2020-12-01"

    assert len(parsed.education) == 1
    edu = parsed.education[0]
    assert edu.school == "Ho Chi Minh City University of Technology"
    assert edu.degree == "Bachelor of Science"
    assert edu.start_date.isoformat() == "2014-01-01"
    assert edu.end_date.isoformat() == "2018-01-01"


# Trimmed header from a real Japanese-market "スキルシート" (skill-sheet) PDF
# a user uploaded and reported as "not parsed correctly". Before the fix,
# _guess_name had no section headers it recognized in this document (all
# Japanese) and no bounded search window, so it fell through to a random
# short-looking sentence deep in the body — turning the candidate's name
# into a garbled skill-level legend. Full raw text runs to ~200 lines of a
# dense skill matrix table; this header slice is enough to regression-test
# the name-extraction fix without embedding the whole document.
JAPANESE_SKILLSHEET_HEADER = """スキルシート
氏　名 ヴォー チー チュオン （Vo Chi Truong） 記入日2026年 08月 26日
【スキルレベル基準】
  S ：業務上の指導・教育が可能なレベル。標準化・レビュー・育成が可能  D ：基礎的な利用・実装経験あり。PoC・小規模対応レベル
  A ：設計〜実装〜リリースまで自走できる。実務上の主担当が可能  E ：基礎知識あり・学習中。実務経験は限定的または未経験
  B ：業務レベルで自走できる。一般的な課題なら独力で対応可能  F ：未経験 / ほとんど経験なし
  C ：業務経験あり。難しい課題は支援を受けながら対応可能  － ：スキル評価対象外（資格・学歴・属性情報など）
■ プログラミング言語 ■ マークアップ・スタイル ■ データ形式 / ドキュメント
スキル・技術 経験年数レベル スキル・技術 経験年数 レベル スキル・技術 経験年数レベル
JavaScript / TypeScript 1 D HTML5 1 D JSON 2 B
Python 3 B アクセシビリティ対応 － CSV / TSV 2 B
"""


def test_guess_name_extracts_romanized_name_from_japanese_skillsheet():
    parsed = RuleBasedCVParser().parse(JAPANESE_SKILLSHEET_HEADER)
    assert parsed.full_name == "Vo Chi Truong"


def test_guess_name_does_not_regress_plain_first_line_name():
    # No label, no parens — just "Name\nemail\n..." like our own DOCX fixtures.
    parsed = RuleBasedCVParser().parse("Nguyen Van Test\nnguyenvantest@example.com\nSKILLS\nPython")
    assert parsed.full_name == "Nguyen Van Test"


def test_guess_name_uses_explicit_label_when_no_parens_present():
    parsed = RuleBasedCVParser().parse("Full Name: Tran Thi B\nEmail: tranthib@example.com")
    assert parsed.full_name == "Tran Thi B"


def test_guess_name_finds_label_beyond_top_lines_but_not_bare_heuristic():
    # DOCX extraction appends table-cell text after all paragraph text (see
    # extractors.py), so a template with contact fields in a table can push
    # "Name: ..." well past the first ~15 lines even though it's visually
    # near the top of the page. A labeled match must still be found; but the
    # unlabeled bare-heuristic fallback (tier 3) must stay bounded near the
    # top, or it would just grab whatever noise line appears first.
    filler = "\n".join(f"Some unrelated bullet point number {i} about the role." for i in range(20))
    raw_text = f"Company Letterhead\nJob Title\n{filler}\nName: Vo Chi Truong\nSKILLS\nPython"
    parsed = RuleBasedCVParser().parse(raw_text)
    assert parsed.full_name == "Vo Chi Truong"


def test_certification_bullets_are_stripped_for_various_glyphs():
    raw_text = "Bob Smith\nbob@example.com\nCERTIFICATIONS\n▪ AWS Certified Developer\n* PMP Certified\n○ Scrum Master\n"
    parsed = RuleBasedCVParser().parse(raw_text)
    names = [c.name for c in parsed.certifications]
    assert names == ["AWS Certified Developer", "PMP Certified", "Scrum Master"]


def test_phone_does_not_false_positive_on_a_bare_year_range():
    # A CV with no real phone number, but a "(2019-2022)" date range in an
    # experience entry — PHONE_RE alone would match the date range as if it
    # were a phone number (both are just digit-groups joined by a dash).
    raw_text = "Alice Wong\nalice@example.com\nWORK EXPERIENCE\nData Engineer at DataCo (2019-2022)\nDid data things.\n"
    parsed = RuleBasedCVParser().parse(raw_text)
    assert parsed.phone is None


def test_phone_is_still_found_when_a_real_one_is_present_alongside_a_year_range():
    raw_text = (
        "Alice Wong\nalice@example.com\n0912345678\n"
        "WORK EXPERIENCE\nData Engineer at DataCo (2019-2022)\nDid data things.\n"
    )
    parsed = RuleBasedCVParser().parse(raw_text)
    assert parsed.phone is not None
    assert "0912345678" in parsed.phone.replace(" ", "").replace("-", "")


def test_vietnamese_section_headers_are_recognized():
    raw_text = (
        "Nguyen Van C\n"
        "nguyenvanc@example.com\n"
        "KỸ NĂNG\n"
        "Python, FastAPI, Docker\n"
        "KINH NGHIỆM LÀM VIỆC\n"
        "Backend Engineer at ACME Corp (Jan 2020 - Present)\n"
        "Xay dung he thong backend.\n"
    )
    parsed = RuleBasedCVParser().parse(raw_text)
    assert "Python" in parsed.skills
    assert len(parsed.work_experience) == 1
    assert parsed.work_experience[0].company == "ACME Corp"


def test_extracts_github_portfolio_url():
    raw_text = "John Doe\njohn@example.com\nGitHub: github.com/johndoe\nSKILLS\nPython\n"
    parsed = RuleBasedCVParser().parse(raw_text)
    assert parsed.portfolio_url == "https://github.com/johndoe"


def test_extracts_labeled_portfolio_url():
    raw_text = "John Doe\njohn@example.com\nPortfolio: johndoe.dev\nSKILLS\nPython\n"
    parsed = RuleBasedCVParser().parse(raw_text)
    assert parsed.portfolio_url == "https://johndoe.dev"


def test_no_portfolio_url_when_absent():
    parsed = RuleBasedCVParser().parse("John Doe\njohn@example.com\nSKILLS\nPython\n")
    assert parsed.portfolio_url is None


def test_infers_current_level_from_title():
    raw_text = (
        "John Doe\njohn@example.com\nWORK EXPERIENCE\n"
        "Senior Backend Engineer at Acme (Jan 2021 - Present)\nBuilt things.\n"
    )
    parsed = RuleBasedCVParser().parse(raw_text)
    assert parsed.current_level == SeniorityLevel.SENIOR


def test_infers_junior_level_from_title():
    raw_text = (
        "John Doe\njohn@example.com\nWORK EXPERIENCE\n"
        "Junior Developer at Acme (Jan 2021 - Present)\nBuilt things.\n"
    )
    parsed = RuleBasedCVParser().parse(raw_text)
    assert parsed.current_level == SeniorityLevel.JUNIOR


def test_primary_specialty_uses_title_over_tied_skills():
    # Python/FastAPI/PostgreSQL (Backend) vs Docker/AWS/Kubernetes (DevOps)
    # is an exact 3-3 tie by skill count alone — a common, unremarkable
    # combination for a backend engineer who also knows the cloud basics.
    # The title should resolve this confidently rather than guessing.
    specialty = _guess_primary_specialty(
        "DevOps Engineer", ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Kubernetes"]
    )
    assert specialty == "DevOps/Infrastructure"

    specialty = _guess_primary_specialty(
        "Senior Backend Engineer", ["Python", "FastAPI", "PostgreSQL", "Docker", "AWS", "Kubernetes"]
    )
    assert specialty == "Backend"


def test_primary_specialty_falls_back_to_skill_voting_without_title_match():
    specialty = _guess_primary_specialty(None, ["Python", "FastAPI", "PostgreSQL", "Django"])
    assert specialty == "Backend"


def test_primary_specialty_none_without_any_categorized_skills():
    assert _guess_primary_specialty(None, []) is None
    assert _guess_primary_specialty("Some Random Title", ["Some Unlisted Tool"]) is None
