# Document Image OCR and Layout Analysis — Başlangıç Rehberi

## Kullanılan Kütüphaneler
- **OpenCV** → Görüntü işleme, layout (düzen) analizi, çizgi tespiti
- **pytesseract** → Google Tesseract OCR motoru üzerinden metin çıkarma

---

## 1. Kurulum Adımları

### Adım 1 — Tesseract OCR motorunu kur (zorunlu)

| İşletim Sistemi | Komut / Link |
|---|---|
| **Windows** | [İndir: UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) |
| **Linux** | `sudo apt install tesseract-ocr tesseract-ocr-tur` |
| **macOS** | `brew install tesseract` |

> **Windows kullanıcıları:** Kurulumdan sonra `ocr_layout_analysis.py` içindeki şu satırın başındaki `#` işaretini kaldır ve kendi kurulum yolunu yaz:
> ```python
> pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
> ```

### Adım 2 — Python kütüphanelerini kur

```bash
pip install -r requirements.txt
```

---

## 2. Projeyi Çalıştır

```bash
python ocr_layout_analysis.py
```

Kendi belge görüntüsünü kullanmak için `ocr_layout_analysis.py` dosyasının en altındaki şu satırı güncelle:

```python
GORUNTU_YOLU = "ornek_belge.png"   # ← bunu değiştir
```

---

## 3. Kodun Yapısı

```
ocr_layout_analysis.py
│
├── goruntu_yukle()          → Görüntü dosyasını yükler
├── on_isleme()              → Gri tonlama + blur + threshold (OCR doğruluğunu artırır)
│
├── metin_cikar()            → pytesseract ile tam metin çıkarır
├── kelime_konumlari_al()    → Her kelimenin koordinatını ve güven skorunu verir
│
├── metin_bloklari_bul()     → OpenCV morfoloji ile büyük metin bloklarını tespit eder
├── cizgiler_bul()           → Tablolardaki yatay/dikey çizgileri bulur
│
├── sonuclari_goster()       → Orijinal, işlenmiş ve analiz sonucu → yan yana gösterir
└── belge_analiz_et()        → Yukarıdakileri sırayla çalıştıran ana pipeline
```

---

## 4. Türkçe Dil Desteği

Tesseract kurulumundan sonra Türkçe dil paketini de kur:

```bash
# Linux
sudo apt install tesseract-ocr-tur

# Dil dosyasını manuel indirmek için:
# https://github.com/tesseract-ocr/tessdata adresinden tur.traineddata indir
# → C:\Program Files\Tesseract-OCR\tessdata\ klasörüne koy (Windows)
```

---

## 5. Sıradaki Adımlar

- [ ] Tablo tespiti ekle (hücre hücre okuma)
- [ ] PDF desteği (`pdf2image` kütüphanesi ile)
- [ ] Çoklu sayfa işleme
- [ ] Sonuçları JSON / CSV olarak kaydetme
- [ ] Görüntü eğikliği düzeltme (deskewing)
