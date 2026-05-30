"""
CV Parser — extracts candidate information from OCR text.
"""

import re

# ─────────────────────────────────────────────────
# KEYWORD LISTS
# ─────────────────────────────────────────────────

EDUCATION_KEYWORDS = [
    "universite", "university", "universitesi",
    "lisans", "bachelor", "b.sc", "b.s.",
    "yuksek lisans", "master", "m.sc", "m.s.", "mba",
    "doktora", "phd", "ph.d",
    "onlisans", "associate",
    "lise", "high school",
    "faculty", "fakulte",
    "bolum", "department",
    "gpa", "cgpa", "not ortalama",
]

EXPERIENCE_KEYWORDS = [
    "experience", "deneyim", "is deneyimi",
    "calisti", "worked at", "work experience",
    "staj", "intern", "internship",
    "pozisyon", "position", "role", "gorev",
    "sirket", "company", "kurum",
    "full-time", "part-time", "freelance",
]

SKILLS_KEYWORDS = [
    "skills", "beceri", "yetenek", "teknoloji", "technology",
    "programlama", "programming", "language",
    "framework", "library", "tool",
    "sertifika", "certificate", "certification",
]

PROGRAMMING_LANGUAGES = [
    "python", "java", "javascript", "typescript", "c++", "c#", "c",
    "go", "rust", "swift", "kotlin", "dart", "ruby", "php",
    "r", "matlab", "scala", "perl", "bash", "shell",
]

FRAMEWORKS_AND_TOOLS = [
    "react", "angular", "vue", "nextjs", "nuxt",
    "django", "flask", "fastapi", "spring", "laravel",
    "flutter", "react native", "tensorflow", "pytorch",
    "nodejs", "node.js", "express", "nestjs",
    "docker", "kubernetes", "git", "github", "gitlab",
    "sql", "mysql", "postgresql", "mongodb", "redis",
    "aws", "azure", "gcp", "firebase", "linux",
    "opencv", "scikit-learn", "pandas", "numpy",
]

LANGUAGE_KEYWORDS = {
    "turkish":    ["turkce", "turkish"],
    "english":    ["ingilizce", "english"],
    "german":     ["almanca", "german", "deutsch"],
    "french":     ["fransizca", "french"],
    "spanish":    ["ispanyolca", "spanish"],
    "italian":    ["italyanca", "italian"],
    "arabic":     ["arapca", "arabic"],
    "russian":    ["rusca", "russian"],
    "japanese":   ["japonca", "japanese"],
    "chinese":    ["cince", "chinese", "mandarin"],
}

PROFICIENCY_LEVELS = [
    "native", "fluent", "advanced", "upper-intermediate",
    "intermediate", "beginner", "basic",
    "ana dil", "anadili", "ileri", "orta",
    "a1", "a2", "b1", "b2", "c1", "c2",
]

CITIES = [
    "istanbul", "ankara", "izmir", "bursa", "antalya", "adana",
    "gaziantep", "konya", "kayseri", "mersin", "eskisehir",
    "diyarbakir", "samsun", "denizli", "urfa", "malatya",
    "london", "new york", "boston", "chicago", "seattle", "berlin", "paris", "amsterdam",
    "remote", "uzaktan", "hybrid", "hibrit",
]

# ─────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────

def _clean(text):
    return re.sub(r"\s+", " ", text).strip()

def _split_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]

def _lowercase(text):
    return text.lower().replace("\u0130", "i").replace("I", "\u0131")

# ─────────────────────────────────────────────────
# FIELD EXTRACTORS
# ─────────────────────────────────────────────────

def extract_email(text):
    matches = re.findall(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", text)
    return matches[0].lower() if matches else ""

def extract_phone(text):
    patterns = re.findall(
        r"(?:\+90|0)?[\s\-.\u200b]?\(?[0-9]{3}\)?[\s\-.]?[0-9]{3}[\s\-.]?[0-9]{2}[\s\-.]?[0-9]{2}",
        text
    )
    if patterns:
        return re.sub(r"[\s\-.]", "", patterns[0])
    return ""

def extract_name(text, email=""):
    lines = _split_lines(text)
    for line in lines[:6]:
        if "@" in line or re.search(r"\d{5,}", line):
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(re.match(r"[A-Za-z\u00c7\u00e7\u011e\u011f\u0130\u0131\u00d6\u00f6\u015e\u015f\u00dc\u00fc\-]+$", w) for w in words):
            return _clean(line)
    if email:
        local = email.split("@")[0]
        guess = local.replace(".", " ").replace("_", " ").title()
        if len(guess.split()) >= 2:
            return guess
    return ""

def extract_city(text):
    lower_text = _lowercase(text)
    for city in CITIES:
        if city in lower_text:
            return city.title()
    return ""

def extract_linkedin(text):
    matches = re.findall(r"linkedin\.com/in/[\w\-]+", text, re.IGNORECASE)
    return matches[0] if matches else ""

def extract_github(text):
    matches = re.findall(r"github\.com/[\w\-]+", text, re.IGNORECASE)
    return matches[0] if matches else ""

# ─────────────────────────────────────────────────
# EDUCATION EXTRACTOR
# ─────────────────────────────────────────────────

def extract_education(text):
    lines = _split_lines(text)
    education_list = []
    i = 0
    while i < len(lines):
        line = lines[i]
        lower = _lowercase(line)
        if any(kw in lower for kw in EDUCATION_KEYWORDS):
            block = [line]
            for j in range(1, 4):
                if i + j < len(lines):
                    block.append(lines[i + j])
            block_text = " | ".join(block)
            years = re.findall(r"\b(19|20)\d{2}\b", block_text)
            year_range = " - ".join(sorted(set(years))) if years else ""
            gpa_match = re.search(r"\b([0-9]{1,2}[.,][0-9]{1,2})\s*/?\s*(?:4\.0|4|100)?\b", block_text)
            gpa = gpa_match.group(1).replace(",", ".") if gpa_match else ""
            degree = ""
            for d in ["doktora", "phd", "ph.d", "yuksek lisans", "master", "m.sc",
                       "lisans", "bachelor", "b.sc", "lise"]:
                if d in _lowercase(block_text):
                    degree = d.title()
                    break
            education_list.append({
                "school": _clean(line),
                "detail": block_text,
                "year":   year_range,
                "gpa":    gpa,
                "degree": degree,
            })
            i += 3
        else:
            i += 1
    return education_list[:3]

def education_summary(education_list):
    if not education_list:
        return ""
    return " / ".join(
        e["school"] + (" (" + e["year"] + ")" if e["year"] else "")
        for e in education_list
    )

# ─────────────────────────────────────────────────
# EXPERIENCE EXTRACTOR
# ─────────────────────────────────────────────────

def extract_experience(text):
    lines = _split_lines(text)
    experience_list = []
    i = 0
    while i < len(lines):
        line = lines[i]
        lower = _lowercase(line)
        if any(kw in lower for kw in EXPERIENCE_KEYWORDS):
            block = [line]
            for j in range(1, 5):
                if i + j < len(lines):
                    block.append(lines[i + j])
            block_text = " | ".join(block)
            year_match = re.search(
                r"(20\d{2})\s*[-\u2013]\s*(20\d{2}|present|devam|halen)",
                block_text, re.IGNORECASE
            )
            duration_str = year_match.group(0) if year_match else ""
            duration_years = 0
            if year_match:
                start = int(year_match.group(1))
                end_str = year_match.group(2)
                if end_str.isdigit():
                    duration_years = int(end_str) - start
                else:
                    duration_years = 2025 - start
            experience_list.append({
                "company":        _clean(line),
                "detail":         block_text,
                "duration":       duration_str,
                "duration_years": duration_years,
            })
            i += 4
        else:
            i += 1
    return experience_list[:5]

def total_experience_years(experience_list):
    return round(sum(e.get("duration_years", 0) for e in experience_list), 1)

def experience_summary(experience_list):
    if not experience_list:
        return ""
    return " / ".join(
        e["company"] + (" (" + e["duration"] + ")" if e["duration"] else "")
        for e in experience_list
    )

# ─────────────────────────────────────────────────
# SKILLS EXTRACTOR
# ─────────────────────────────────────────────────

def extract_skills(text):
    lower_text = _lowercase(text)
    found = []
    for lang in PROGRAMMING_LANGUAGES:
        if re.search(r"\b" + re.escape(lang) + r"\b", lower_text):
            found.append(lang.upper() if len(lang) <= 3 else lang.title())
    for tool in FRAMEWORKS_AND_TOOLS:
        if re.search(r"\b" + re.escape(tool) + r"\b", lower_text):
            found.append(tool.title())
    return list(dict.fromkeys(found))

# ─────────────────────────────────────────────────
# LANGUAGE EXTRACTOR
# ─────────────────────────────────────────────────

def extract_languages(text):
    lower_text = _lowercase(text)
    found = []
    for lang_name, synonyms in LANGUAGE_KEYWORDS.items():
        for synonym in synonyms:
            if synonym.lower() in lower_text:
                pos = lower_text.find(synonym.lower())
                region = lower_text[max(0, pos - 30):pos + 60]
                level = ""
                for lvl in PROFICIENCY_LEVELS:
                    if lvl in region:
                        level = lvl.title()
                        break
                found.append({"language": lang_name.title(), "level": level})
                break
    return found

def languages_summary(languages):
    return ", ".join(
        lang["language"] + (" (" + lang["level"] + ")" if lang["level"] else "")
        for lang in languages
    )

# ─────────────────────────────────────────────────
# GPA EXTRACTOR
# ─────────────────────────────────────────────────

def extract_gpa(text):
    """
    Extract GPA value from text.
    Supported formats:
    - Labelled:   'GPA: 3.50 / 4.00'  or  'CGPA: 85/100'
    - Unlabelled: '2.98/4'  or  '3.05/4.0'  (common CV format)
    Avoids false matches with date formats (10.2023, 01.2024).
    """
    # 1) Labelled  "GPA: 3.50 / 4.00"
    m = re.search(
        r"(?:GPA|CGPA)[:\s]+([0-9]+[.,][0-9]+)\s*/\s*([0-9]+[.,][0-9]+)",
        text, re.IGNORECASE
    )
    if m:
        return m.group(1).replace(",", ".") + "/" + m.group(2).replace(",", ".")

    # 2) Labelled  "GPA: 3.50"
    m = re.search(r"(?:GPA|CGPA)[:\s]+([0-9]+[.,][0-9]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).replace(",", ".")

    # 3) Labelled  "not ortalama / grade point"
    m = re.search(
        r"(?:not ortalama|grade point)[:\s]+([0-9]+[.,][0-9]+)",
        text, re.IGNORECASE
    )
    if m:
        return m.group(1).replace(",", ".")

    # 4) Unlabelled X.XX/4 format (single digit + 2 decimals — avoids date patterns)
    bare4 = re.findall(r"(?<!\d)([0-9]\.[0-9]{2})\s*/\s*4(?:\.0)?\b", text)
    if bare4:
        return " | ".join(v + "/4" for v in bare4)

    # 5) Unlabelled out of 100  "85/100"
    m = re.search(r"\b([0-9]{2,3})\s*/\s*100\b", text)
    if m:
        return m.group(1) + "/100"

    return ""

# ─────────────────────────────────────────────────
# MAIN PARSER
# ─────────────────────────────────────────────────

def cv_parse(text):
    """
    Parse OCR text, extract all fields and return a structured dictionary.
    """
    email    = extract_email(text)
    phone    = extract_phone(text)
    name     = extract_name(text, email)
    city     = extract_city(text)
    linkedin = extract_linkedin(text)
    github   = extract_github(text)
    gpa      = extract_gpa(text)

    education_list  = extract_education(text)
    experience_list = extract_experience(text)
    skills_list     = extract_skills(text)
    languages_list  = extract_languages(text)

    notes = "GPA: " + gpa if gpa else ""

    return {
        "full_name":          name,
        "email":              email,
        "phone":              phone,
        "city":               city,
        "linkedin":           linkedin,
        "github":             github,
        "education_summary":  education_summary(education_list),
        "education_detail":   education_list,
        "experience_summary": experience_summary(experience_list),
        "experience_years":   total_experience_years(experience_list),
        "experience_detail":  experience_list,
        "skills":             skills_list,
        "skills_str":         ", ".join(skills_list),
        "languages":          languages_list,
        "languages_str":      languages_summary(languages_list),
        "gpa":                gpa,
        "notes":              notes,
        "raw_text":           text,
    }
