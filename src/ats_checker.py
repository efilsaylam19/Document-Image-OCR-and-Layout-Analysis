"""
ATS Score Checker
Scores a CV text for Applicant Tracking System (ATS) compatibility.
"""

import re

# Strong action verbs ATS-optimized resumes use
ACTION_VERBS = [
    "developed", "designed", "implemented", "built", "created", "launched",
    "managed", "led", "optimized", "improved", "increased", "reduced",
    "delivered", "achieved", "coordinated", "analyzed", "automated",
    "integrated", "deployed", "maintained", "established", "initiated",
    "generated", "streamlined", "scaled", "migrated", "collaborated",
    "mentored", "trained", "researched", "published", "presented",
    "resolved", "negotiated", "drove", "secured", "supported",
]

# Standard ATS section headers
SECTION_HEADERS = {
    "Summary":    ["summary", "objective", "profile", "about", "introduction", "overview"],
    "Experience": ["experience", "employment", "work history", "internship", "career"],
    "Education":  ["education", "academic", "qualification", "university", "degree"],
    "Skills":     ["skills", "technologies", "technical", "competencies", "expertise", "tools"],
}

STOP_WORDS = {
    "and", "the", "for", "are", "with", "that", "this", "from", "have",
    "will", "been", "your", "their", "our", "its", "not", "but", "can",
    "all", "each", "you", "we", "in", "of", "to", "a", "is", "an", "or",
    "as", "at", "be", "by", "do", "if", "on", "so", "up", "us", "was",
    "who", "per", "any", "than", "also", "may", "must", "shall", "would",
}


# ─────────────────────────────────────────────────
# INDIVIDUAL CHECKS
# ─────────────────────────────────────────────────

def check_contact(parsed):
    """Contact completeness. Max 20 pts."""
    items = [
        ("Email",    bool(parsed.get("email")),    5),
        ("Phone",    bool(parsed.get("phone")),    5),
        ("LinkedIn", bool(parsed.get("linkedin")), 5),
        ("Location", bool(parsed.get("city")),     5),
    ]
    score = sum(pts for _, ok, pts in items if ok)
    details = []
    for label, ok, pts in items:
        tip = ""
        if not ok:
            tip = f"Add your {label.lower()} to the CV header"
        details.append({"label": label, "ok": ok, "pts": pts, "max": pts, "tip": tip})
    return score, details


def check_sections(text):
    """Standard section headers. Max 20 pts."""
    lower = text.lower()
    total = 0
    details = []
    for section, keywords in SECTION_HEADERS.items():
        found = any(kw in lower for kw in keywords)
        pts = 5 if found else 0
        total += pts
        tip = "" if found else ("Add a clear '" + section + "' section header")
        details.append({"label": section + " section", "ok": found, "pts": pts, "max": 5, "tip": tip})
    return total, details


def check_skills(parsed):
    """Skills count. Max 15 pts."""
    skills = parsed.get("skills", [])
    n = len(skills)
    if n >= 9:
        pts = 15
    elif n >= 4:
        pts = 10
    elif n >= 1:
        pts = 5
    else:
        pts = 0
    tip = ""
    if n == 0:
        tip = "Add a Skills section listing your technologies and tools"
    elif n < 4:
        tip = str(n) + " skill(s) detected — list more technologies (aim for 8+)"
    return pts, [{"label": "Skills listed (" + str(n) + " found)", "ok": pts >= 10, "pts": pts, "max": 15, "tip": tip}]


def check_achievements(text):
    """Measurable achievements (numbers/%). Max 15 pts."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    metric_lines = [l for l in lines if re.search(r"\d+\s*%|\b\d{2,}\b", l)]
    n = len(metric_lines)
    if n >= 6:
        pts = 15
    elif n >= 3:
        pts = 10
    elif n >= 1:
        pts = 5
    else:
        pts = 0
    tip = ""
    if n == 0:
        tip = "Add measurable results (e.g. 'increased performance by 30%')"
    elif n < 3:
        tip = str(n) + " quantified achievement(s) — add more metrics and numbers"
    return pts, [{"label": "Measurable achievements (" + str(n) + " found)", "ok": pts >= 10, "pts": pts, "max": 15, "tip": tip}]


def check_action_verbs(text):
    """Strong action verbs. Max 10 pts."""
    lower = text.lower()
    found = [v for v in ACTION_VERBS if re.search(r"\b" + v + r"\b", lower)]
    n = len(found)
    if n >= 5:
        pts = 10
    elif n >= 2:
        pts = 6
    elif n >= 1:
        pts = 3
    else:
        pts = 0
    tip = ""
    if n < 5:
        tip = "Start bullet points with strong action verbs (built, designed, led, optimized...)"
    return pts, [{"label": "Action verbs (" + str(n) + " found)", "ok": pts >= 6, "pts": pts, "max": 10, "tip": tip}]


def check_dates(parsed):
    """Date consistency in experience. Max 10 pts."""
    experiences = parsed.get("experience_detail", [])
    with_dates = [e for e in experiences if e.get("duration")]
    if not experiences:
        pts = 5
        ok = False
        tip = "Add work experience with date ranges (e.g. 2022 - Present)"
    elif len(with_dates) == len(experiences):
        pts = 10
        ok = True
        tip = ""
    else:
        missing = len(experiences) - len(with_dates)
        pts = 5
        ok = False
        tip = str(missing) + " experience entry/entries missing date ranges"
    return pts, [{"label": "Date consistency", "ok": ok, "pts": pts, "max": 10, "tip": tip}]


def check_format(table_cells_count):
    """ATS-unfriendly formatting (tables/columns). Max 10 pts."""
    if table_cells_count == 0:
        pts, ok, tip = 10, True, ""
    elif table_cells_count < 5:
        pts, ok, tip = 6, True, "Minimal table use — tables can confuse some ATS systems"
    else:
        pts = 0
        ok = False
        tip = str(table_cells_count) + " table cells detected — avoid tables; ATS often cannot parse them"
    return pts, [{"label": "ATS-safe formatting", "ok": ok, "pts": pts, "max": 10, "tip": tip}]


def check_keywords(text, job_description):
    """Keyword match vs job description. Max 10 pts. Returns None if no JD provided."""
    if not job_description.strip():
        return None, []

    jd_words = set()
    for w in job_description.split():
        w_clean = w.lower().strip(".,;:()[]\"'")
        if len(w_clean) >= 3 and w_clean not in STOP_WORDS:
            jd_words.add(w_clean)

    if not jd_words:
        return None, []

    cv_lower = text.lower()
    matched = [w for w in jd_words if w in cv_lower]
    ratio = len(matched) / len(jd_words)

    if ratio >= 0.7:
        pts = 10
    elif ratio >= 0.5:
        pts = 8
    elif ratio >= 0.3:
        pts = 5
    elif ratio >= 0.1:
        pts = 2
    else:
        pts = 0

    pct = int(ratio * 100)
    tip = "" if ratio >= 0.5 else (str(pct) + "% keyword match — tailor your CV to the job description")
    detail = {
        "label": "Keyword match vs job description (" + str(pct) + "%)",
        "ok": ratio >= 0.5,
        "pts": pts,
        "max": 10,
        "tip": tip,
        "matched": len(matched),
        "total_jd": len(jd_words),
    }
    return pts, [detail]


# ─────────────────────────────────────────────────
# MAIN SCORER
# ─────────────────────────────────────────────────

def ats_score(parsed, text, table_cells_count=0, job_description=""):
    """
    Run all ATS checks. Returns a score report dict.

    Args:
        parsed           : dict returned by cv_parse()
        text             : raw OCR text string
        table_cells_count: number of table cells detected by layout analysis
        job_description  : optional job description text for keyword matching

    Returns dict with:
        total, max_score, percentage, rating, rating_color, breakdown, tips
    """
    breakdown = []
    total = 0
    max_score = 0

    checks = [
        ("contact",      check_contact(parsed),            20),
        ("sections",     check_sections(text),             20),
        ("skills",       check_skills(parsed),             15),
        ("achievements", check_achievements(text),         15),
        ("verbs",        check_action_verbs(text),         10),
        ("dates",        check_dates(parsed),              10),
        ("format",       check_format(table_cells_count),  10),
    ]

    for _, (s, d), max_pts in checks:
        total += s
        max_score += max_pts
        breakdown.extend(d)

    # Keyword match (optional +10)
    kw_score, kw_detail = check_keywords(text, job_description)
    if kw_score is not None:
        total += kw_score
        max_score += 10
        breakdown.extend(kw_detail)

    percentage = round((total / max_score) * 100) if max_score > 0 else 0

    if percentage >= 80:
        rating = "Excellent"
        rating_color = "#3aaa7a"
    elif percentage >= 60:
        rating = "Good"
        rating_color = "#f0a500"
    elif percentage >= 40:
        rating = "Fair"
        rating_color = "#e07020"
    else:
        rating = "Needs Work"
        rating_color = "#cc4444"

    tips = [item["tip"] for item in breakdown if item.get("tip")]

    return {
        "total":        total,
        "max_score":    max_score,
        "percentage":   percentage,
        "rating":       rating,
        "rating_color": rating_color,
        "breakdown":    breakdown,
        "tips":         tips,
    }
