"""Court-specific format templates and reusable document blocks.

Provides COURT_FORMATS for lane→format mapping, party identity constants,
signature blocks, verification clauses, and proposed order shells.
"""

from datetime import date, datetime

# ── Party Identity (CANONICAL — auto-correct on sight) ──────────────────────

PLAINTIFF_NAME = "ANDREW JAMES PIGORS"
PLAINTIFF_ADDRESS = "1977 Whitehall Rd, Lot 17\nNorth Muskegon, MI 49445"
PLAINTIFF_PHONE = "(231) 903-5690"
PLAINTIFF_EMAIL = "andrewjpigors@gmail.com"

DEFENDANT_NAME = "EMILY A. WATSON"
DEFENDANT_ADDRESS = "2160 Garland Dr\nNorton Shores, MI 49441"

FOC_NAME = "Pamela Rusco"
FOC_ADDRESS = "990 Terrace St\nMuskegon, MI 49442"

JUDGE_NAME = "Hon. Jenny L. McNeill"
CHILD_INITIALS = "L.D.W."

SEPARATION_ANCHOR = date(2025, 7, 29)

# ── Court Format Definitions ────────────────────────────────────────────────

COURT_FORMATS = {
    "A": {
        "court": "14th Circuit Court",
        "county": "Muskegon",
        "format": "MCR_2113",
        "font": "12pt TNR",
        "spacing": "double",
        "case_number": "2024-001507-DC",
        "judge": JUDGE_NAME,
    },
    "B": {
        "court": "14th Circuit Court",
        "county": "Muskegon",
        "format": "MCR_2113",
        "font": "12pt TNR",
        "spacing": "double",
        "case_number": "2025-002760-CZ",
        "judge": "Hon. Kenneth Hoopes",
    },
    "C": {
        "court": "United States District Court\nWestern District of Michigan",
        "county": None,
        "format": "FRCP",
        "font": "14pt",
        "spacing": "double",
        "case_number": "NEW",
        "judge": "TBD",
    },
    "D": {
        "court": "14th Circuit Court",
        "county": "Muskegon",
        "format": "MCR_2113",
        "font": "12pt TNR",
        "spacing": "double",
        "case_number": "2023-5907-PP",
        "judge": JUDGE_NAME,
    },
    "E": {
        "court": "Judicial Tenure Commission",
        "county": None,
        "format": "JTC_LETTER",
        "font": "standard",
        "spacing": "single",
        "case_number": "NEW",
        "judge": None,
    },
    "F": {
        "court": "Michigan Court of Appeals",
        "county": None,
        "format": "MCR_7212",
        "font": "12pt TNR",
        "spacing": "double",
        "max_pages": 50,
        "case_number": "COA-366810",
        "judge": "Panel TBD",
    },
}


def get_court_format(lane: str) -> dict:
    """Return court format dict for a lane letter (A-F) or filing ID (F1-F10)."""
    lane_letter = _lane_to_letter(lane)
    fmt = COURT_FORMATS.get(lane_letter)
    if fmt is None:
        raise ValueError(f"Unknown lane '{lane}' — expected A-F or F1-F10")
    return dict(fmt)


# ── Lane Mapping ────────────────────────────────────────────────────────────

_FILING_LANE_MAP = {
    "F1": "A", "F2": "B", "F3": "A", "F4": "C",
    "F5": "F", "F6": "E", "F7": "A", "F8": "D",
    "F9": "F", "F10": "F",
}


def _lane_to_letter(lane: str) -> str:
    """Normalize lane to a single letter (A-F)."""
    lane = lane.strip().upper()
    if lane in COURT_FORMATS:
        return lane
    return _FILING_LANE_MAP.get(lane, lane)


# ── Separation Day Counter (dynamic — Rule 29) ─────────────────────────────

def separation_days(as_of: date | None = None) -> int:
    """Compute days since last contact with L.D.W. ALWAYS dynamic."""
    ref = as_of or date.today()
    return (ref - SEPARATION_ANCHOR).days


# ── Pro Se Signature Block ──────────────────────────────────────────────────

PRO_SE_SIGNATURE = f"""Respectfully submitted,


______________________________
{PLAINTIFF_NAME}
Plaintiff, appearing pro se
{PLAINTIFF_ADDRESS}
{PLAINTIFF_PHONE}
{PLAINTIFF_EMAIL}

Dated: {{date}}"""


def render_signature(filing_date: date | None = None) -> str:
    """Render the pro se signature block with the given date."""
    d = filing_date or date.today()
    return PRO_SE_SIGNATURE.format(date=d.strftime("%B %d, %Y"))


# ── Verification Clause (Affidavits) ────────────────────────────────────────

VERIFICATION_CLAUSE = f"""VERIFICATION

I, Andrew James Pigors, declare under the penalties of perjury under the laws
of the State of Michigan that the foregoing statements are true and correct to
the best of my knowledge, information, and belief.


______________________________
{PLAINTIFF_NAME}
Dated: {{date}}"""


def render_verification(filing_date: date | None = None) -> str:
    """Render the verification clause with date."""
    d = filing_date or date.today()
    return VERIFICATION_CLAUSE.format(date=d.strftime("%B %d, %Y"))


# ── Proposed Order Shell ────────────────────────────────────────────────────

PROPOSED_ORDER_TEMPLATE = """STATE OF MICHIGAN
IN THE {court}
{county_line}

{plaintiff},          Case No. {case_number}
    Plaintiff,                {judge}
v.

{defendant},
    Defendant.
___________________________/

ORDER

    At a session of said Court held in the {court_city},
County of {county}, State of Michigan, on _______________, 2026.

PRESENT: {judge}

    This matter having come before the Court on Plaintiff's {motion_title},
and the Court being otherwise fully advised in the premises;

    IT IS HEREBY ORDERED that:

    1. {relief_line}

    IT IS SO ORDERED.


______________________________
{judge}
{court}"""


def render_proposed_order(filing_info: dict, motion_title: str,
                          relief_line: str) -> str:
    """Render a proposed order from filing info."""
    fmt = get_court_format(filing_info.get("lane", "A"))
    county = fmt.get("county", "Muskegon") or "Muskegon"
    county_line = f"COUNTY OF {county.upper()}" if county else ""
    return PROPOSED_ORDER_TEMPLATE.format(
        court=fmt["court"],
        county_line=county_line,
        plaintiff=PLAINTIFF_NAME,
        case_number=filing_info.get("case_number", fmt.get("case_number", "")),
        judge=fmt.get("judge", JUDGE_NAME),
        defendant=DEFENDANT_NAME,
        court_city=county,
        county=county,
        motion_title=motion_title,
        relief_line=relief_line,
    )


# ── Certificate of Service Template ─────────────────────────────────────────

COS_TEMPLATE = """CERTIFICATE OF SERVICE

    I, Andrew James Pigors, certify that on {service_date}, I served a true
copy of {document_title} upon the following by {method}:

{recipients}

______________________________
{plaintiff}
Plaintiff, appearing pro se
Dated: {service_date}"""


def render_cos(document_title: str, service_date: date | None = None,
               method: str = "first-class U.S. mail, postage prepaid",
               include_foc: bool = True) -> str:
    """Render MC 12 Certificate of Service."""
    d = service_date or date.today()
    date_str = d.strftime("%B %d, %Y")

    recipients = [
        f"    {DEFENDANT_NAME}\n    {DEFENDANT_ADDRESS}"
    ]
    if include_foc:
        recipients.append(
            f"    {FOC_NAME}, Friend of the Court\n    {FOC_ADDRESS}"
        )

    return COS_TEMPLATE.format(
        service_date=date_str,
        document_title=document_title,
        method=method,
        recipients="\n\n".join(recipients),
        plaintiff=PLAINTIFF_NAME,
    )


# ── Fee Waiver Note ─────────────────────────────────────────────────────────

FEE_WAIVER_NOTE = (
    "Plaintiff has previously filed MC 20 (Fee Waiver Request) "
    "and requests that the filing fee be waived."
)


# ── Caption Helpers ─────────────────────────────────────────────────────────

def build_caption_text(filing_info: dict) -> str:
    """Build the full court caption block for a filing."""
    fmt = get_court_format(filing_info.get("lane", "A"))
    case_number = filing_info.get("case_number") or fmt.get("case_number", "")
    judge = fmt.get("judge", JUDGE_NAME)
    county = fmt.get("county")

    lines = ["STATE OF MICHIGAN"]
    lines.append(f"IN THE {fmt['court'].upper()}")
    if county:
        lines.append(f"COUNTY OF {county.upper()}")
    lines.append("")
    lines.append(f"{PLAINTIFF_NAME},          Case No. {case_number}")
    judge_line = f"    Plaintiff,                {judge}" if judge else "    Plaintiff,"
    lines.append(judge_line)
    lines.append("v.")
    lines.append("")
    lines.append(f"{DEFENDANT_NAME},")
    lines.append("    Defendant.")
    lines.append("___________________________/")
    return "\n".join(lines)
