import logging
import re
from datetime import date, datetime

from app.services.cv_parser.base import (
    CVParser,
    ParsedCertification,
    ParsedCV,
    ParsedEducation,
    ParsedExperience,
    ParsedLanguage,
    ParsedProject,
)
from app.models.enums import SeniorityLevel
from app.services.cv_parser.skills_vocab import SKILLS_VOCAB_LOWER, SPECIALTY_CATEGORIES, SKILL_CATEGORIES, skill_pattern
from app.utils.text_normalize import normalize_whitespace

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s.-]?)?(\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}")
# GitHub/GitLab profile links, or a URL on a line explicitly labeled
# portfolio/website — deliberately not "any URL" (that would grab a LinkedIn
# ad link, a company's own website mentioned in an old job, etc.).
PORTFOLIO_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:github\.com|gitlab\.com)/[A-Za-z0-9_.-]+/?|"
    r"(?:portfolio|website|personal\s*site)\s*[:\-]\s*(?P<labeled>\S+)",
    re.IGNORECASE,
)

LEVEL_KEYWORDS: list[tuple[str, SeniorityLevel]] = [
    (r"\bintern(ship)?\b", SeniorityLevel.INTERN),
    (r"\bfresher\b|\bentry[\s-]?level\b", SeniorityLevel.FRESHER),
    (r"\bjunior\b|\bjr\.?\b", SeniorityLevel.JUNIOR),
    (r"\bmid(dle)?[\s-]?level\b|\bintermediate\b", SeniorityLevel.MID),
    (r"\bsenior\b|\bsr\.?\b", SeniorityLevel.SENIOR),
    (r"\btech(nical)?\s+lead\b|\bteam\s+lead\b|\bprincipal\b|\bstaff\b|\blead\b", SeniorityLevel.LEAD),
    (r"\bdirector\b|\bvp\b|\bvice\s+president\b|\bcto\b|\bchief\b", SeniorityLevel.DIRECTOR),
    (r"\bmanager\b|\bhead\s+of\b", SeniorityLevel.MANAGER),
]

# Checked against the candidate's own stated title before falling back to
# skill-count voting (see _guess_primary_specialty) — a title is a much more
# confident signal than "has both Python and Docker on their skill list",
# which ties equally plausibly between Backend and DevOps.
TITLE_SPECIALTY_KEYWORDS: list[tuple[str, str]] = [
    (r"\bdevops\b|\bsite\s+reliability\b|\bsre\b|\binfrastructure\b|\bplatform\s+engineer\b", "DevOps/Infrastructure"),
    (r"\bmachine\s+learning\b|\bML\b|\bAI\b|\bdata\s+scientist\b|\bdata\s+engineer\b|\bnlp\b|\bcomputer\s+vision\b", "AI/ML & Data"),
    (r"\bfront[\s-]?end\b|\bui\s+developer\b", "Frontend"),
    (r"\bmobile\b|\bios\b|\bandroid\b|\bflutter\b", "Mobile"),
    (r"\bback[\s-]?end\b", "Backend"),
    (r"\bqa\b|\bquality\s+assurance\b|\btest(er|ing)?\s+engineer\b", "QA/Testing"),
    (r"\bhr\b|\bhuman\s+resources\b|\brecruit(er|ing|ment)?\b|\btalent\s+acquisition\b", "HR"),
    (r"\bmarketing\b", "Marketing"),
    (r"\bsales\b|\bbusiness\s+development\b", "Sales"),
]
YEARS_EXP_RE = re.compile(r"(\d+(?:\.\d+)?)\+?\s*years?\s*(?:of)?\s*experience", re.IGNORECASE)

# Common bullet glyphs across Word/PowerPoint/PDF exports — stripped from the
# front of list-item lines (certifications, languages, project names) so a
# bullet character doesn't end up baked into the stored value.
BULLET_CHARS = " \t-•*▪▸‣●○◦·–—"

KNOWN_LOCATIONS = [
    "Ho Chi Minh City", "Hanoi", "Da Nang", "Hai Phong", "Can Tho", "Nha Trang", "Hue", "Vung Tau",
    "Remote", "Singapore", "Tokyo", "San Francisco", "New York", "London",
]

SECTION_HEADERS = {
    "summary": [
        "summary", "professional summary", "objective", "profile", "about me",
        "tóm tắt", "giới thiệu bản thân", "giới thiệu", "mục tiêu nghề nghiệp",
        "自己pr", "自己紹介", "アピールポイント",
    ],
    "skills": [
        "skills", "technical skills", "core skills", "key skills",
        "kỹ năng", "kỹ năng chuyên môn",
        "スキル", "スキルシート", "技術スキル",
    ],
    "experience": [
        "work experience", "experience", "employment history", "professional experience",
        "kinh nghiệm làm việc", "kinh nghiệm", "quá trình công tác",
        "職歴", "経歴", "主なプロジェクト", "プロジェクト経験",
    ],
    "education": [
        "education", "academic background",
        "học vấn", "trình độ học vấn", "quá trình đào tạo",
        "学歴",
    ],
    "certifications": [
        "certifications", "certificates", "licenses",
        "chứng chỉ", "bằng cấp",
        "資格", "証明書",
    ],
    "languages": ["languages", "ngoại ngữ", "語学力", "語学"],
    "projects": [
        "projects", "personal projects", "key projects",
        "dự án", "các dự án",
        "プロジェクト",
    ],
}

# Explicit "Name:" / "Họ tên:" / "氏名" labels — checked before the generic
# first-plausible-line heuristic, since that fallback can pick up an
# unrelated short line when a document has no section headers we recognize
# (e.g. a table-heavy or non-English CV/skill-sheet).
NAME_LABEL_RE = re.compile(
    r"full\s*name|candidate\s*name|applicant\s*name|\bname\b|"
    r"h[oọ]\s*(?:va|v[àa])?\s*t[eê]n|"
    r"氏\s*名",
    re.IGNORECASE,
)
# A romanized name in parentheses near the top of the document — very common
# on Japanese-market resumes/skill-sheets alongside the native-script name,
# e.g. "氏名　ヴォー チー チュオン （Vo Chi Truong）".
ROMANIZED_NAME_RE = re.compile(r"[（(]\s*([A-Za-z][A-Za-z .'-]{1,40}[A-Za-z.])\s*[）)]")
NAME_SCAN_LINE_LIMIT = 15

MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9,
    "september": 9, "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}

DATE_TOKEN_RE = re.compile(
    r"(?P<month>[A-Za-z]{3,9})?\s*/?\s*(?P<year>\d{4})|(?P<present>present|current|now)", re.IGNORECASE
)
DATE_RANGE_RE = re.compile(
    r"(?P<start>[A-Za-z]{3,9}?\.?\s*\d{4}|\d{1,2}/\d{4}|\d{4})\s*[-–—to]+\s*"
    r"(?P<end>[A-Za-z]{3,9}?\.?\s*\d{4}|\d{1,2}/\d{4}|\d{4}|present|current|now)",
    re.IGNORECASE,
)


def _parse_single_date(token: str) -> date | None:
    token = token.strip().rstrip(".")
    if not token:
        return None
    m = re.match(r"(?P<month>[A-Za-z]{3,9})\s+(?P<year>\d{4})", token)
    if m:
        month = MONTHS.get(m.group("month").lower())
        if month:
            return date(int(m.group("year")), month, 1)
    m = re.match(r"(?P<month>\d{1,2})/(?P<year>\d{4})", token)
    if m:
        return date(int(m.group("year")), int(m.group("month")), 1)
    m = re.match(r"^(?P<year>\d{4})$", token)
    if m:
        return date(int(m.group("year")), 1, 1)
    return None


def _is_year_range(candidate: str) -> bool:
    """A bare "(2019-2022)"-shaped year range satisfies PHONE_RE (it's just
    two digit groups joined by a dash) but obviously isn't a phone number —
    this showed up for real on a CV whose only parenthetical digit pattern
    was an employment date range with no actual phone number present."""
    digits_and_dashes = re.sub(r"[()\s]", "", candidate)
    m = re.fullmatch(r"(\d{4})[-–—](\d{4})", digits_and_dashes)
    if not m:
        return False
    y1, y2 = int(m.group(1)), int(m.group(2))
    return 1900 <= y1 <= 2099 and 1900 <= y2 <= 2099


def _find_phone(text: str) -> str | None:
    for match in PHONE_RE.finditer(text):
        candidate = match.group(0)
        if len(re.sub(r"\D", "", candidate)) < 7:
            continue  # too few digits to plausibly be a phone number
        if _is_year_range(candidate):
            continue
        return candidate
    return None


def _strip_date_range(text: str) -> str:
    cleaned = DATE_RANGE_RE.sub("", text)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)  # leftover empty parens from "(Jan 2020 - Present)"
    return cleaned.strip(" -,|")


def parse_date_range(text: str) -> tuple[date | None, date | None, bool]:
    match = DATE_RANGE_RE.search(text)
    if not match:
        return None, None, False
    start = _parse_single_date(match.group("start"))
    end_raw = match.group("end").strip().lower()
    if end_raw in ("present", "current", "now"):
        return start, None, True
    end = _parse_single_date(match.group("end"))
    return start, end, False


def _split_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for raw_line in lines:
        line = raw_line.strip()
        stripped_lower = line.lower().strip(":").strip()
        matched_key = None
        for key, aliases in SECTION_HEADERS.items():
            if stripped_lower in aliases and len(line) < 60:
                matched_key = key
                break
        if matched_key:
            current = matched_key
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def _guess_name(header_lines: list[str], full_text: str) -> str:
    all_lines = full_text.split("\n")
    top_lines = all_lines[:NAME_SCAN_LINE_LIMIT]

    # 1) Romanized name in parens near the top — strong signal, but only
    # near the top: unbounded, this risks matching an unrelated parenthetical
    # technology mention deep in a skills section (e.g. "(Machine Learning)").
    m = ROMANIZED_NAME_RE.search("\n".join(top_lines))
    if m:
        return normalize_whitespace(m.group(1))

    # 2) Explicit "Name:" / "Họ tên:" / "氏名" label, value on the same line.
    # Searched over the *whole* document, not just the top: DOCX extraction
    # (app/services/cv_parser/extractors.py) appends table-cell text after
    # all paragraph text, so a template that puts contact fields in a table
    # can push "Name: ..." well past the first ~15 lines even though it's
    # visually near the top of the page. An explicit label match is specific
    # enough to be low-risk even unbounded — unlike tier 3 below.
    for line in all_lines:
        label_match = NAME_LABEL_RE.search(line)
        if not label_match:
            continue
        value = line[label_match.end():].lstrip(" :：\t").strip()
        # Cut off a trailing unrelated field on the same line (e.g. a
        # Japanese skill-sheet's "filled in on <date>" that follows the name
        # with no delimiter other than whitespace).
        value = re.split(r"記入日|作成日|\bdate\b|\bngày\b", value, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        if value and len(value) <= 60:
            return value

    # 3) Fallback: the first short, name-shaped line near the very top of the
    # document. Bounded to the first ~15 lines so an unrecognized document
    # structure (no section headers we know, e.g. a different language or a
    # table-heavy skill-sheet) can't make this fall through to some unrelated
    # sentence from deep in the body — that used to be exactly what happened.
    for line in header_lines[:NAME_SCAN_LINE_LIMIT]:
        line = line.strip()
        if not line or "@" in line or PHONE_RE.fullmatch(line.replace(" ", "")):
            continue
        if len(line) > 60 or any(ch.isdigit() for ch in line):
            continue
        words = line.split()
        if 1 < len(words) <= 5:
            return line
    return "Unknown Candidate"


def _guess_location(header_text: str, full_text: str) -> str | None:
    # Prefer a match near the contact info (header) so a school/employer city
    # mentioned later in the CV doesn't get mistaken for where the candidate lives.
    for candidate_text in (header_text, full_text):
        for loc in KNOWN_LOCATIONS:
            if re.search(rf"\b{re.escape(loc)}\b", candidate_text, re.IGNORECASE):
                return loc
    m = re.search(r"(?:location|address)\s*[:\-]\s*(.+)", full_text, re.IGNORECASE)
    if m:
        return normalize_whitespace(m.group(1))[:255]
    return None


def _extract_portfolio_url(full_text: str) -> str | None:
    m = PORTFOLIO_URL_RE.search(full_text)
    if not m:
        return None
    url = m.group("labeled") or m.group(0)
    url = url.strip().rstrip(".,;)")
    if not url:
        return None
    if not url.lower().startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def _guess_current_level(current_title: str | None, full_text: str) -> SeniorityLevel | None:
    # Prefer the candidate's own stated title (e.g. "Senior Backend Engineer")
    # over a level word appearing incidentally elsewhere in the document
    # (a past employer's job ad, a mentioned colleague's title, etc.).
    for haystack in (current_title or "", full_text):
        if not haystack:
            continue
        for pattern, level in LEVEL_KEYWORDS:
            if re.search(pattern, haystack, re.IGNORECASE):
                return level
    return None


def _guess_primary_specialty(current_title: str | None, skills: list[str]) -> str | None:
    """Best-effort category guess — e.g. mostly Python/FastAPI/PostgreSQL
    skills -> "Backend". Recruiter-editable; this is a starting point, not a
    claim of certainty.

    1) The candidate's own title is checked first — a stated "DevOps
       Engineer" title is a far more confident signal than skill counting,
       which would otherwise tie between Backend and DevOps for someone who
       simply lists Python *and* Docker/Kubernetes/AWS (a common, not
       remotely unusual combination for a backend engineer).
    2) Falls back to counting categorized skills; ties are broken by
       SPECIALTY_CATEGORIES' declared order (core dev disciplines listed
       before supporting/infra ones) rather than giving up with None.
    """
    if current_title:
        for pattern, category in TITLE_SPECIALTY_KEYWORDS:
            if re.search(pattern, current_title, re.IGNORECASE):
                return category

    skill_set = {s.lower() for s in skills}
    counts = {
        category: sum(1 for skill in SKILL_CATEGORIES[category] if skill.lower() in skill_set)
        for category in SPECIALTY_CATEGORIES
    }
    best_count = max(counts.values())
    if best_count == 0:
        return None
    return next(category for category in SPECIALTY_CATEGORIES if counts[category] == best_count)


def _extract_skills(skills_lines: list[str], full_text: str) -> list[str]:
    found: set[str] = set()
    raw = " ".join(skills_lines) if skills_lines else ""
    tokens = re.split(r"[,•|/\n]", raw)
    for token in tokens:
        token = token.strip(" .-")
        if not token:
            continue
        canonical = SKILLS_VOCAB_LOWER.get(token.lower())
        if canonical:
            found.add(canonical)
    # Also scan the whole document so skills mentioned in experience/projects count.
    lowered = full_text.lower()
    for skill_lower, canonical in SKILLS_VOCAB_LOWER.items():
        if re.search(skill_pattern(skill_lower), lowered):
            found.add(canonical)
    return sorted(found)


def _merge_wrapped_parens(lines: list[str]) -> list[str]:
    """PDF text extraction (pypdf) hard-wraps long lines at the page's visual
    width and — unlike our own DOCX-based text — frequently drops blank
    paragraph lines entirely. The most damaging artifact is a trailing date
    range getting wrapped mid-parenthetical, e.g. "...Technology (2014 -" /
    "2018)" as two separate lines. Rejoin lines while parens are unbalanced
    so a wrapped "(start - end)" always ends up back on one logical line."""
    merged: list[str] = []
    buffer = ""
    balance = 0
    for line in lines:
        if not line.strip() and balance == 0:
            merged.append(line)
            continue
        buffer = f"{buffer} {line}".strip() if buffer else line
        balance += line.count("(") - line.count(")")
        if balance <= 0:
            merged.append(buffer)
            buffer = ""
            balance = 0
    if buffer:
        merged.append(buffer)
    return merged


def _group_by_blank_lines(lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _group_entries(lines: list[str]) -> list[list[str]]:
    """Splits section lines into one block per experience/education entry.

    Uses two independent signals, since either can be missing depending on
    the source format: a blank line (DOCX/plain-text exports reliably keep
    these) and a line containing a date range (present in virtually every
    real entry header, and often the *only* reliable signal in text
    extracted from a PDF — pypdf frequently collapses the blank paragraph
    lines that would otherwise separate entries, which used to merge every
    job/education entry in a PDF into a single block)."""
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            continue
        if current and DATE_RANGE_RE.search(line):
            blocks.append(current)
            current = []
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _parse_experience(lines: list[str]) -> list[ParsedExperience]:
    entries: list[ParsedExperience] = []
    for block in _group_entries(lines):
        block_text = " ".join(block)
        start, end, is_current = parse_date_range(block_text)
        header_line = block[0]
        header_clean = _strip_date_range(header_line)
        company, position = "Unknown Company", "Unknown Position"
        for sep in [" at ", " - ", " | ", ", "]:
            if sep in header_clean:
                parts = [p.strip() for p in header_clean.split(sep, 1)]
                if len(parts) == 2:
                    position, company = parts
                    break
        else:
            position = header_clean or position
        description = " ".join(block[1:]) if len(block) > 1 else None
        entries.append(
            ParsedExperience(
                company=company or "Unknown Company",
                position=position or "Unknown Position",
                start_date=start,
                end_date=end,
                is_current=is_current,
                description=normalize_whitespace(description) if description else None,
            )
        )
    return entries


DEGREE_KEYWORDS = ["bachelor", "master", "phd", "b.s", "m.s", "b.a", "m.a", "mba", "associate", "diploma", "engineer"]


def _parse_education(lines: list[str]) -> list[ParsedEducation]:
    entries: list[ParsedEducation] = []
    for block in _group_entries(lines):
        block_text = " ".join(block)
        start, end, _ = parse_date_range(block_text)
        header_line = _strip_date_range(block[0])
        degree, major, school = None, None, header_line
        lowered = header_line.lower()
        for kw in DEGREE_KEYWORDS:
            if kw in lowered:
                parts = [p.strip() for p in header_line.split(",", 1)]
                degree = parts[0]
                if len(parts) > 1:
                    school = parts[1]
                break
        if len(block) > 1 and not major:
            major = normalize_whitespace(block[1])
        entries.append(
            ParsedEducation(school=school or "Unknown School", degree=degree, major=major, start_date=start, end_date=end)
        )
    return entries


def _parse_certifications(lines: list[str]) -> list[ParsedCertification]:
    entries = []
    for line in lines:
        line = line.strip(BULLET_CHARS)
        if not line:
            continue
        m = re.match(r"(?P<name>.+?)\s*[-–|]\s*(?P<issuer>.+)", line)
        if m:
            entries.append(ParsedCertification(name=m.group("name").strip(), issuer=m.group("issuer").strip()))
        else:
            entries.append(ParsedCertification(name=line))
    return entries


def _parse_languages(lines: list[str]) -> list[ParsedLanguage]:
    entries = []
    joined = " ".join(lines)
    for token in re.split(r"[,\n]", joined):
        token = token.strip(BULLET_CHARS)
        if not token:
            continue
        m = re.match(r"(?P<name>[A-Za-z ]+)\((?P<level>[^)]+)\)", token)
        if m:
            entries.append(ParsedLanguage(name=m.group("name").strip(), proficiency=m.group("level").strip()))
        else:
            entries.append(ParsedLanguage(name=token))
    return entries


def _parse_projects(lines: list[str]) -> list[ParsedProject]:
    entries = []
    for block in _group_by_blank_lines(lines):
        name = block[0].strip(BULLET_CHARS)
        description = " ".join(block[1:]) if len(block) > 1 else None
        tech_found = [
            canonical for skill_lower, canonical in SKILLS_VOCAB_LOWER.items()
            if re.search(skill_pattern(skill_lower), " ".join(block), re.IGNORECASE)
        ]
        entries.append(
            ParsedProject(
                name=name,
                description=normalize_whitespace(description) if description else None,
                technologies=", ".join(sorted(set(tech_found))) or None,
            )
        )
    return entries


def _compute_years_of_experience(text: str, experiences: list[ParsedExperience]) -> float | None:
    m = YEARS_EXP_RE.search(text)
    if m:
        return float(m.group(1))
    total_months = 0
    for exp in experiences:
        if not exp.start_date:
            continue
        end = exp.end_date or date.today()
        total_months += max(0, (end.year - exp.start_date.year) * 12 + (end.month - exp.start_date.month))
    return round(total_months / 12, 1) if total_months else None


class RuleBasedCVParser(CVParser):
    """Regex/heuristic CV parser. No external dependency — always available."""

    def parse(self, raw_text: str) -> ParsedCV:
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [normalize_whitespace(l) if l.strip() else "" for l in text.split("\n")]
        lines = _merge_wrapped_parens(lines)
        sections = _split_sections(lines)

        email_match = EMAIL_RE.search(text)
        phone_match = _find_phone(text)

        experiences = _parse_experience(sections.get("experience", []))
        current_title = experiences[0].position if experiences else None
        skills = _extract_skills(sections.get("skills", []), text)

        parsed = ParsedCV(
            full_name=_guess_name(sections.get("header", []), text),
            email=email_match.group(0) if email_match else None,
            phone=normalize_whitespace(phone_match) if phone_match else None,
            location=_guess_location(" ".join(sections.get("header", [])), text),
            current_title=current_title,
            summary=normalize_whitespace(" ".join(sections.get("summary", []))) or None,
            portfolio_url=_extract_portfolio_url(text),
            current_level=_guess_current_level(current_title, text),
            primary_specialty=_guess_primary_specialty(current_title, skills),
            skills=skills,
            work_experience=experiences,
            education=_parse_education(sections.get("education", [])),
            certifications=_parse_certifications(sections.get("certifications", [])),
            languages=_parse_languages(sections.get("languages", [])),
            projects=_parse_projects(sections.get("projects", [])),
        )
        parsed.years_of_experience = _compute_years_of_experience(text, experiences)
        return parsed
