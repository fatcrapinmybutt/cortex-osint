"""MEEK Lane Classifier — Compiled regex lane routing for litigation evidence.

Priority order: E (Misconduct) → D (PPO) → F (Appellate) → A (Custody) → B (Housing).
Default lane: 'C' (multi-lane / federal convergence).
"""
import re

__all__ = ["classify", "classify_multi", "MEEK_PATTERNS", "LANE_PRIORITY"]

LANE_PRIORITY = ["E", "D", "F", "A", "B"]

MEEK_PATTERNS: dict[str, re.Pattern] = {
    "E": re.compile(
        r"McNeill|judicial|bias|JTC|canon|misconduct|benchbook|ex\s*parte"
        r"|disqualif|recus|tenure|violation",
        re.IGNORECASE,
    ),
    "D": re.compile(
        r"PPO|protection\s*order|5907|stalking|harassment"
        r"|personal\s*protection|domestic\s*violence",
        re.IGNORECASE,
    ),
    "F": re.compile(
        r"COA|366810|appeal|appellant|appellee|appendix"
        r"|court\s*of\s*appeals|MSC|superintending",
        re.IGNORECASE,
    ),
    "A": re.compile(
        r"custody|parenting|001507|Watson|child|visitation|FOC"
        r"|best\s*interest|MCL\s*722|guardianship",
        re.IGNORECASE,
    ),
    "B": re.compile(
        r"Shady\s*Oaks|eviction|housing|trailer|002760|habitability"
        r"|landlord|tenant|lease|rent",
        re.IGNORECASE,
    ),
}


def classify(text: str) -> str:
    """Classify text into a single litigation lane (highest priority match).

    Returns the first matching lane in priority order, or 'C' as default.
    """
    if not text:
        return "C"
    for lane in LANE_PRIORITY:
        if MEEK_PATTERNS[lane].search(text):
            return lane
    return "C"


def classify_multi(text: str) -> list[str]:
    """Classify text into all matching litigation lanes.

    Returns a list of all matching lanes in priority order, or ['C'] if none.
    """
    if not text:
        return ["C"]
    matches = [lane for lane in LANE_PRIORITY if MEEK_PATTERNS[lane].search(text)]
    return matches if matches else ["C"]
