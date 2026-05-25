"""
CV Parser -- OCR metninden aday bilgilerini cikarir.
"""

import re

# ─────────────────────────────────────────────────
# ANAHTAR KELIME LISTELERI
# ─────────────────────────────────────────────────

EGITIM_ANAHTARLARI = [
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

DENEYIM_ANAHTARLARI = [
    "experience", "deneyim", "is deneyimi",
    "calisti", "worked at", "work experience",
    "staj", "intern", "internship",
    "pozisyon", "position", "role", "gorev",
    "sirket", "company", "kurum",
    "full-time", "part-time", "freelance",
]

BECERI_ANAHTARLARI = [
    "skills", "beceri", "yetenek", "teknoloji", "technology",
    "programlama", "programming", "language",
    "framework", "library", "tool",
    "sertifika", "certificate", "certification",
]

PROGRAMLAMA_DILLERI = [
    "python", "java", "javascript", "typescript", "c++", "c#", "c",
    "go", "rust", "swift", "kotlin", "dart", "ruby", "php",
    "r", "matlab", "scala", "perl", "bash", "shell",
]

FRAMEWORKLER = [
    "react", "angular", "vue", "nextjs", "nuxt",
    "django", "flask", "fastapi", "spring", "laravel",
    "flutter", "react native", "tensorflow", "pytorch",
    "nodejs", "node.js", "express", "nestjs",
    "docker", "kubernetes", "git", "github", "gitlab",
    "sql", "mysql", "postgresql", "mongodb", "redis",
    "aws", "azure", "gcp", "firebase", "linux",
    "opencv", "scikit-learn", "pandas", "numpy",
]

DIL_ANAHTAR = {
    "turkce": ["turkce", "turkish"],
    "ingilizce": ["ingilizce", "english"],
    "almanca": ["almanca", "german", "deutsch"],
    "fransizca": ["fransizca", "french"],
    "ispanyolca": ["ispanyolca", "spanish"],
    "italyanca": ["italyanca", "italian"],
    "arapca": ["arapca", "arabic"],
    "rusca": ["rusca", "russian"],
    "japonca": ["japonca", "japanese"],
    "cince": ["cince", "chinese", "mandarin"],
}

SEVIYE_ANAHTAR = [
    "native", "fluent", "advanced", "upper-intermediate",
    "intermediate", "beginner", "basic",
    "ana dil", "anadili", "ileri", "orta",
    "a1", "a2", "b1", "b2", "c1", "c2",
]

SEHIRLER = [
    "istanbul", "ankara", "izmir", "bursa", "antalya", "adana",
    "gaziantep", "konya", "kayseri", "mersin", "eskisehir",
    "diyarbakir", "samsun", "denizli", "urfa", "malatya",
    "london", "new york", "berlin", "paris", "amsterdam",
    "remote", "uzaktan", "hybrid", "hibrit",
]

# ─────────────────────────────────────────────────
# YARDIMCI FONKSIYONLAR
# ─────────────────────────────────────────────────

def _temizle(metin):
    return re.sub(r"\s+", " ", metin).strip()

def _satirlara_bol(metin):
    return [s.strip() for s in metin.splitlines() if s.strip()]

def _kucuk(metin):
    return metin.lower().replace("\u0130", "i").replace("I", "\u0131")

# ─────────────────────────────────────────────────
# ALAN CIKARICI FONKSIYONLAR
# ─────────────────────────────────────────────────

def email_cikar(metin):
    sonuc = re.findall(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", metin)
    return sonuc[0].lower() if sonuc else ""

def telefon_cikar(metin):
    kalip = re.findall(
        r"(?:\+90|0)?[\s\-.\u200b]?\(?[0-9]{3}\)?[\s\-.]?[0-9]{3}[\s\-.]?[0-9]{2}[\s\-.]?[0-9]{2}",
        metin
    )
    if kalip:
        return re.sub(r"[\s\-.]", "", kalip[0])
    return ""

def ad_cikar(metin, email=""):
    satirlar = _satirlara_bol(metin)
    for satir in satirlar[:6]:
        if "@" in satir or re.search(r"\d{5,}", satir):
            continue
        kelimeler = satir.split()
        if 2 <= len(kelimeler) <= 4 and all(re.match(r"[A-Za-z\u00c7\u00e7\u011e\u011f\u0130\u0131\u00d6\u00f6\u015e\u015f\u00dc\u00fc\-]+$", k) for k in kelimeler):
            return _temizle(satir)
    if email:
        lokal = email.split("@")[0]
        tahmin = lokal.replace(".", " ").replace("_", " ").title()
        if len(tahmin.split()) >= 2:
            return tahmin
    return ""

def sehir_cikar(metin):
    kucuk_metin = _kucuk(metin)
    for sehir in SEHIRLER:
        if sehir in kucuk_metin:
            return sehir.title()
    return ""

def linkedin_cikar(metin):
    sonuc = re.findall(r"linkedin\.com/in/[\w\-]+", metin, re.IGNORECASE)
    return sonuc[0] if sonuc else ""

def github_cikar(metin):
    sonuc = re.findall(r"github\.com/[\w\-]+", metin, re.IGNORECASE)
    return sonuc[0] if sonuc else ""

# ─────────────────────────────────────────────────
# EGITIM CIKARICI
# ─────────────────────────────────────────────────

def egitim_cikar(metin):
    satirlar = _satirlara_bol(metin)
    egitimler = []
    i = 0
    while i < len(satirlar):
        satir = satirlar[i]
        kucuk = _kucuk(satir)
        if any(a in kucuk for a in EGITIM_ANAHTARLARI):
            blok = [satir]
            for j in range(1, 4):
                if i + j < len(satirlar):
                    blok.append(satirlar[i + j])
            blok_metin = " | ".join(blok)
            yillar = re.findall(r"\b(19|20)\d{2}\b", blok_metin)
            yil = " - ".join(sorted(set(yillar))) if yillar else ""
            gpa_m = re.search(r"\b([0-9]{1,2}[.,][0-9]{1,2})\s*/?\s*(?:4\.0|4|100)?\b", blok_metin)
            gpa = gpa_m.group(1).replace(",", ".") if gpa_m else ""
            derece = ""
            for d in ["doktora", "phd", "ph.d", "yuksek lisans", "master", "m.sc",
                       "lisans", "bachelor", "b.sc", "lise"]:
                if d in _kucuk(blok_metin):
                    derece = d.title()
                    break
            egitimler.append({
                "okul": _temizle(satir),
                "detay": blok_metin,
                "yil": yil,
                "gpa": gpa,
                "derece": derece,
            })
            i += 3
        else:
            i += 1
    return egitimler[:3]

def egitim_ozet(egitimler):
    if not egitimler:
        return ""
    return " / ".join(
        e["okul"] + (" (" + e["yil"] + ")" if e["yil"] else "")
        for e in egitimler
    )

# ─────────────────────────────────────────────────
# DENEYIM CIKARICI
# ─────────────────────────────────────────────────

def deneyim_cikar(metin):
    satirlar = _satirlara_bol(metin)
    deneyimler = []
    i = 0
    while i < len(satirlar):
        satir = satirlar[i]
        kucuk = _kucuk(satir)
        if any(a in kucuk for a in DENEYIM_ANAHTARLARI):
            blok = [satir]
            for j in range(1, 5):
                if i + j < len(satirlar):
                    blok.append(satirlar[i + j])
            blok_metin = " | ".join(blok)
            yil_m = re.search(
                r"(20\d{2})\s*[-\u2013]\s*(20\d{2}|present|devam|halen)",
                blok_metin, re.IGNORECASE
            )
            sure = yil_m.group(0) if yil_m else ""
            sure_yil = 0
            if yil_m:
                baslangic = int(yil_m.group(1))
                bitis_str = yil_m.group(2)
                if bitis_str.isdigit():
                    sure_yil = int(bitis_str) - baslangic
                else:
                    sure_yil = 2025 - baslangic
            deneyimler.append({
                "sirket": _temizle(satir),
                "detay": blok_metin,
                "sure": sure,
                "sure_yil": sure_yil,
            })
            i += 4
        else:
            i += 1
    return deneyimler[:5]

def deneyim_toplam_yil(deneyimler):
    return round(sum(d.get("sure_yil", 0) for d in deneyimler), 1)

def deneyim_ozet(deneyimler):
    if not deneyimler:
        return ""
    return " / ".join(
        d["sirket"] + (" (" + d["sure"] + ")" if d["sure"] else "")
        for d in deneyimler
    )

# ─────────────────────────────────────────────────
# BECERI CIKARICI
# ─────────────────────────────────────────────────

def beceri_cikar(metin):
    kucuk_metin = _kucuk(metin)
    bulunanlar = []
    for dil in PROGRAMLAMA_DILLERI:
        if re.search(r"\b" + re.escape(dil) + r"\b", kucuk_metin):
            bulunanlar.append(dil.upper() if len(dil) <= 3 else dil.title())
    for fw in FRAMEWORKLER:
        if re.search(r"\b" + re.escape(fw) + r"\b", kucuk_metin):
            bulunanlar.append(fw.title())
    return list(dict.fromkeys(bulunanlar))

# ─────────────────────────────────────────────────
# DIL CIKARICI
# ─────────────────────────────────────────────────

def dil_cikar(metin):
    kucuk_metin = _kucuk(metin)
    bulunanlar = []
    for dil_adi, esanlamlar in DIL_ANAHTAR.items():
        for es in esanlamlar:
            if es.lower() in kucuk_metin:
                konum = kucuk_metin.find(es.lower())
                bolge = kucuk_metin[max(0, konum - 30):konum + 60]
                seviye = ""
                for s in SEVIYE_ANAHTAR:
                    if s in bolge:
                        seviye = s.title()
                        break
                bulunanlar.append({"dil": dil_adi.title(), "seviye": seviye})
                break
    return bulunanlar

def dil_ozet(diller):
    return ", ".join(
        d["dil"] + (" (" + d["seviye"] + ")" if d["seviye"] else "")
        for d in diller
    )

# ─────────────────────────────────────────────────
# GPA CIKARICI
# ─────────────────────────────────────────────────

def gpa_cikar(metin):
    """
    GPA degerini metin icerisinden cikarir.
    - Etiketli: 'GPA: 3.50 / 4.00'  veya  'CGPA: 85/100'
    - Etiketsiz: '2.98/4' veya '3.05/4.0'  (CV'lerde yaygin format)
    Tarih formatlarindan (10.2023, 01.2024) karismasini onler.
    """
    # 1) Etiketli  "GPA: 3.50 / 4.00"
    m = re.search(
        r"(?:GPA|CGPA)[:\s]+([0-9]+[.,][0-9]+)\s*/\s*([0-9]+[.,][0-9]+)",
        metin, re.IGNORECASE
    )
    if m:
        return m.group(1).replace(",", ".") + "/" + m.group(2).replace(",", ".")

    # 2) Etiketli  "GPA: 3.50"
    m = re.search(r"(?:GPA|CGPA)[:\s]+([0-9]+[.,][0-9]+)", metin, re.IGNORECASE)
    if m:
        return m.group(1).replace(",", ".")

    # 3) Etiketli  "not ortalama / grade point"
    m = re.search(
        r"(?:not ortalama|grade point)[:\s]+([0-9]+[.,][0-9]+)",
        metin, re.IGNORECASE
    )
    if m:
        return m.group(1).replace(",", ".")

    # 4) Etiketsiz X.XX/4 formati
    #    Tek rakam + 2 ondalik + /4  =>  tarihlerde bu pattern olmaz (10.2023 vb)
    bare4 = re.findall(r"(?<!\d)([0-9]\.[0-9]{2})\s*/\s*4(?:\.0)?\b", metin)
    if bare4:
        return " | ".join(v + "/4" for v in bare4)

    # 5) Etiketsiz 100-lik  "85/100"
    m = re.search(r"\b([0-9]{2,3})\s*/\s*100\b", metin)
    if m:
        return m.group(1) + "/100"

    return ""

# ─────────────────────────────────────────────────
# ANA PARSER FONKSIYONU
# ─────────────────────────────────────────────────

def cv_parse(metin):
    """
    OCR metnini alir, tum alanlari cikarir ve
    yapilandirilmis bir sozluk dondurur.
    """
    email    = email_cikar(metin)
    telefon  = telefon_cikar(metin)
    ad       = ad_cikar(metin, email)
    sehir    = sehir_cikar(metin)
    linkedin = linkedin_cikar(metin)
    github   = github_cikar(metin)
    gpa      = gpa_cikar(metin)

    egitimler  = egitim_cikar(metin)
    deneyimler = deneyim_cikar(metin)
    beceriler  = beceri_cikar(metin)
    diller     = dil_cikar(metin)

    notlar = "GPA: " + gpa if gpa else ""

    return {
        "ad_soyad":      ad,
        "email":         email,
        "telefon":       telefon,
        "sehir":         sehir,
        "linkedin":      linkedin,
        "github":        github,
        "egitim_ozet":   egitim_ozet(egitimler),
        "egitim_detay":  egitimler,
        "deneyim_ozet":  deneyim_ozet(deneyimler),
        "deneyim_yil":   deneyim_toplam_yil(deneyimler),
        "deneyim_detay": deneyimler,
        "beceriler":     beceriler,
        "beceri_str":    ", ".join(beceriler),
        "diller":        diller,
        "dil_str":       dil_ozet(diller),
        "gpa":           gpa,
        "notlar":        notlar,
        "ham_metin":     metin,
    }

# Backward-compatible Turkish aliases
email_cIkar = email_cikar
telefon_cIkar = telefon_cikar
ad_cIkar = ad_cikar
sehir_cIkar = sehir_cikar
linkedin_cIkar = linkedin_cikar
github_cIkar = github_cikar
egitim_cIkar = egitim_cikar
deneyim_cIkar = deneyim_cikar
beceri_cIkar = beceri_cikar
dil_cIkar = dil_cikar
gpa_cIkar = gpa_cikar
