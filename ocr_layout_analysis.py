"""
Document Image OCR and Layout Analysis
Kullanılan araçlar: OpenCV, pytesseract
"""

import cv2
import pytesseract
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import os

# Tesseract yolu (Windows için gerekli)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ─────────────────────────────────────────────────
# 1. GÖRÜNTÜ YÜKLEME VE ÖN İŞLEME
# ─────────────────────────────────────────────────

def goruntu_yukle(dosya_yolu: str) -> np.ndarray:
    """Görüntüyü yükler ve BGR formatında döndürür."""
    img = cv2.imread(dosya_yolu)
    if img is None:
        raise FileNotFoundError(f"Görüntü bulunamadı: {dosya_yolu}")
    return img


def on_isleme(img: np.ndarray) -> np.ndarray:
    """
    OCR doğruluğunu artırmak için temel ön işleme adımları:
    - Gri tonlamaya çevirme
    - Gürültü azaltma
    - Eşikleme (thresholding)
    """
    # Gri tonlamaya çevir
    gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Gaussian blur ile gürültüyü azalt
    bulanik = cv2.GaussianBlur(gri, (3, 3), 0)

    # Otsu's thresholding: arka planı beyaz, metni siyah yap
    _, esikli = cv2.threshold(bulanik, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return esikli


# ─────────────────────────────────────────────────
# 2. METİN ÇIKARMA (OCR)
# ─────────────────────────────────────────────────

def metin_cikar(img_islenmis: np.ndarray, dil: str = "tur+eng") -> str:
    """
    İşlenmiş görüntüden metin çıkarır.

    dil parametresi:
      "tur"     → Sadece Türkçe
      "eng"     → Sadece İngilizce
      "tur+eng" → Türkçe ve İngilizce birlikte
    """
    pil_img = Image.fromarray(img_islenmis)
    # psm 6: Tek bir metin bloğu olarak işle → daha düzenli çıktı
    config = "--psm 6 --oem 3"
    metin = pytesseract.image_to_string(pil_img, lang=dil, config=config)
    return metin.strip()


def kelime_konumlari_al(img_islenmis: np.ndarray, dil: str = "tur+eng") -> list:
    """
    Her kelimenin görüntü üzerindeki konumunu (bounding box) döndürür.
    """
    pil_img = Image.fromarray(img_islenmis)
    veri = pytesseract.image_to_data(pil_img, lang=dil, output_type=pytesseract.Output.DICT)

    kelimeler = []
    for i, kelime in enumerate(veri["text"]):
        if kelime.strip() and int(veri["conf"][i]) > 40:  # Güven skoru > 40
            kelimeler.append({
                "metin": kelime,
                "x": veri["left"][i],
                "y": veri["top"][i],
                "genislik": veri["width"][i],
                "yukseklik": veri["height"][i],
                "guven": veri["conf"][i],
            })
    return kelimeler


# ─────────────────────────────────────────────────
# 3. LAYOUT (DÜZEN) ANALİZİ
# ─────────────────────────────────────────────────

def metin_bloklari_bul(img: np.ndarray) -> list:
    """
    OpenCV morfoloji işlemleri ile metin bloklarını tespit eder.
    (Paragraflar, başlıklar, sütunlar gibi büyük bölgeler)
    """
    gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, esikli = cv2.threshold(gri, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Yatay ve dikey genişletme ile metin satırlarını birleştir
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
    genisletilmis = cv2.dilate(esikli, kernel, iterations=3)

    # Bağlantılı bölgeleri bul
    konturlar, _ = cv2.findContours(genisletilmis, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    bloklar = []
    for k in konturlar:
        x, y, w, h = cv2.boundingRect(k)
        # Çok küçük gürültüleri filtrele
        if w > 50 and h > 10:
            bloklar.append({"x": x, "y": y, "genislik": w, "yukseklik": h})

    # Yukarıdan aşağıya sırala
    bloklar.sort(key=lambda b: b["y"])
    return bloklar


def cizgiler_bul(img: np.ndarray) -> dict:
    """
    Hough Line Transform ile yatay ve dikey çizgileri tespit eder.
    (Tablolar, formlar ve bölücü çizgiler için kullanışlı)
    """
    gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    kenarlar = cv2.Canny(gri, 50, 150, apertureSize=3)
    cizgiler = cv2.HoughLinesP(kenarlar, 1, np.pi / 180, threshold=100,
                                minLineLength=100, maxLineGap=10)

    yatay, dikey = [], []
    if cizgiler is not None:
        for c in cizgiler:
            x1, y1, x2, y2 = c[0]
            aci = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if aci < 10:        # Yatay çizgi
                yatay.append((x1, y1, x2, y2))
            elif aci > 80:      # Dikey çizgi
                dikey.append((x1, y1, x2, y2))

    return {"yatay": yatay, "dikey": dikey}


# ─────────────────────────────────────────────────
# 4. GÖRSEL ÇIKTI
# ─────────────────────────────────────────────────

def sonuclari_goster(img_orijinal: np.ndarray,
                     img_islenmis: np.ndarray,
                     bloklar: list,
                     kelimeler: list) -> np.ndarray:
    """
    Orijinal görüntü üzerine tespit edilen blokları ve kelimeleri çizer.
    """
    cikti = img_orijinal.copy()

    # Metin bloklarını mavi çerçeveyle göster
    for blok in bloklar:
        x, y, w, h = blok["x"], blok["y"], blok["genislik"], blok["yukseklik"]
        cv2.rectangle(cikti, (x, y), (x + w, y + h), (255, 100, 0), 2)

    # Kelimeleri yeşil çerçeveyle göster
    for k in kelimeler:
        x, y, w, h = k["x"], k["y"], k["genislik"], k["yukseklik"]
        cv2.rectangle(cikti, (x, y), (x + w, y + h), (0, 200, 0), 1)

    # Matplotlib ile yan yana göster
    fig, axes = plt.subplots(1, 3, figsize=(18, 7))
    axes[0].imshow(cv2.cvtColor(img_orijinal, cv2.COLOR_BGR2RGB))
    axes[0].set_title("Orijinal Görüntü")
    axes[0].axis("off")

    axes[1].imshow(img_islenmis, cmap="gray")
    axes[1].set_title("Ön İşleme (OCR için)")
    axes[1].axis("off")

    axes[2].imshow(cv2.cvtColor(cikti, cv2.COLOR_BGR2RGB))
    axes[2].set_title("Layout + Kelime Tespiti")
    axes[2].axis("off")

    plt.tight_layout()
    plt.savefig("analiz_sonucu.png", dpi=150, bbox_inches="tight")
    plt.show()

    return cikti


# ─────────────────────────────────────────────────
# 5. ANA PIPELINE
# ─────────────────────────────────────────────────

def belge_analiz_et(dosya_yolu: str, dil: str = "tur+eng") -> dict:
    """
    Tek bir fonksiyon çağrısıyla tam analiz yapar.
    Döndürür: metin, kelimeler, bloklar, çizgiler
    """
    print(f"[1/5] Görüntü yükleniyor: {dosya_yolu}")
    img = goruntu_yukle(dosya_yolu)

    print("[2/5] Ön işleme uygulanıyor...")
    img_islenmis = on_isleme(img)

    print("[3/5] Metin çıkarılıyor (OCR)...")
    metin = metin_cikar(img_islenmis, dil=dil)
    kelimeler = kelime_konumlari_al(img_islenmis, dil=dil)

    print("[4/5] Layout analizi yapılıyor...")
    bloklar = metin_bloklari_bul(img)
    cizgiler = cizgiler_bul(img)

    print("[5/5] Sonuçlar gösteriliyor...")
    sonuclari_goster(img, img_islenmis, bloklar, kelimeler)

    sonuc = {
        "metin": metin,
        "kelime_sayisi": len(kelimeler),
        "blok_sayisi": len(bloklar),
        "yatay_cizgi_sayisi": len(cizgiler["yatay"]),
        "dikey_cizgi_sayisi": len(cizgiler["dikey"]),
        "kelimeler": kelimeler,
        "bloklar": bloklar,
    }

    print("\n" + "=" * 50)
    print("ANALİZ TAMAMLANDI")
    print("=" * 50)
    print(f"Bulunan kelime sayısı : {sonuc['kelime_sayisi']}")
    print(f"Metin bloğu sayısı    : {sonuc['blok_sayisi']}")
    print(f"Yatay çizgi sayısı   : {sonuc['yatay_cizgi_sayisi']}")
    print(f"Dikey çizgi sayısı   : {sonuc['dikey_cizgi_sayisi']}")
    print("\n--- ÇIKARILAN METİN ---")
    print(sonuc["metin"] if sonuc["metin"] else "(metin bulunamadı)")

    return sonuc


# ─────────────────────────────────────────────────
# KULLANIM ÖRNEĞİ
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    # Kendi görüntü dosyanın yolunu buraya yaz:
    GORUNTU_YOLU = "ornek_belge.png"

    # Dil seçimi: "tur" / "eng" / "tur+eng"
    DIL = "tur+eng"

    if not os.path.exists(GORUNTU_YOLU):
        print(f"HATA: '{GORUNTU_YOLU}' bulunamadı.")
        print("Lütfen GORUNTU_YOLU değişkenini kendi dosya yolunla güncelle.")
    else:
        sonuc = belge_analiz_et(GORUNTU_YOLU, dil=DIL)
