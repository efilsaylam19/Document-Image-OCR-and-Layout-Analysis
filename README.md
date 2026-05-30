# Document Image OCR & Layout Analysis System

A desktop application for extracting text and analyzing the layout of document images. Built with OpenCV, Tesseract OCR, and Tkinter — featuring a dark-themed GUI, candidate pool management, ATS scoring, and multi-format export.

---

## ✨ Features

| Feature | Description |
|---|---|
| **OCR Engine** | Extract text from images and multi-page PDFs using Google Tesseract |
| **Layout Analysis** | Detect text blocks and table cells with OpenCV morphological operations |
| **Image Enhancement** | Brightness, contrast, denoise, deskew, and edge detection sliders |
| **Table Detection** | Identify and read individual table cells; export to CSV |
| **CV / Resume Parser** | Automatically extract name, email, phone, city, education, experience, skills, and languages |
| **Candidate Pool** | Store, filter, score, and rank candidates in a SQLite database |
| **ATS Checker** | Score a CV for Applicant Tracking System compatibility with improvement tips |
| **Export** | JSON, CSV, and styled Excel (.xlsx) export |
| **PDF Support** | Load and OCR multi-page PDFs (requires Poppler) |

---

## 📁 Project Structure

```
Document-Image-OCR-and-Layout-Analysis/
│
├── src/                     # Source code files
│   ├── app.py               # Main GUI application
│   ├── ocr_engine.py        # OCR pipeline
│   ├── cv_parser.py         # CV field extractor
│   ├── ats_checker.py       # ATS compatibility scorer
│   └── candidate_excel.py   # Excel export
│
├── assets/                  # Sample test images
│   ├── sample_document.png
│   └── sample_table.png
│
├── data/                    # SQLite DB and Excel files
├── samples/                 # Test files and output images
│
├── run.py                   # Entry point (run this to start)
├── .gitignore
└── README.md
```

---

## 🚀 Getting Started

### Step 1 — Install Tesseract OCR (required)

| OS | Instructions |
|---|---|
| **Windows** | Download from [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki). During setup, check **Turkish** under "Additional language data". |
| **Linux** | `sudo apt install tesseract-ocr tesseract-ocr-tur` |
| **macOS** | `brew install tesseract tesseract-lang` |

> **Windows users:** After installation, verify the path inside `app.py` and `ocr_engine.py`:
> ```python
> pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
> ```

### Step 2 — Install Python dependencies

```bash
pip install opencv-python pytesseract Pillow numpy matplotlib pdf2image openpyxl
```

### Step 3 — Run the application

```bash
python run.py
```

---

## 📄 PDF Support (optional)

PDF loading requires **Poppler** in addition to `pdf2image`:

1. Download from [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)
2. Extract and add the `bin/` folder to your system **PATH**
3. Restart your terminal / IDE

---

## 🖥️ Usage

### GUI Application (`app.py`)

The application has five tabs:

- **Analysis** — Load an image or PDF, apply enhancements, run OCR, view extracted text
- **Table Detection** — Detect and read table cells; export to CSV
- **Candidate Pool** — Manage extracted CV data; filter and rank candidates
- **Database** — Browse and search all saved documents
- **ATS Score** — Score a loaded CV for ATS compatibility

### Standalone OCR Script (`src/ocr_engine.py`)

```python
import sys
sys.path.append("src")
from ocr_engine import analyze_document

result = analyze_document("assets/sample_document.png", lang="tur+eng")
print(result["text"])
```

### CV Parser (`src/cv_parser.py`)

```python
import sys
sys.path.append("src")
from cv_parser import cv_parse

data = cv_parse(ocr_text)
print(data["full_name"])       # Extracted name
print(data["skills_str"])      # Comma-separated skills
print(data["experience_years"]) # Total years of experience
```

---

## 🔧 Supported Languages

| Code | Language |
|---|---|
| `eng` | English |
| `tur` | Turkish |
| `tur+eng` | Turkish + English (default) |

Add any Tesseract language pack and pass its code to `lang=`.

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `opencv-python` | Image processing and layout analysis |
| `pytesseract` | Tesseract OCR Python wrapper |
| `Pillow` | Image handling and Tkinter integration |
| `numpy` | Array operations |
| `matplotlib` | Result visualization in `ocr_engine.py` |
| `pdf2image` | PDF to image conversion *(optional)* |
| `openpyxl` | Excel export *(optional)* |

---

## 📝 License

MIT License — free to use, modify, and distribute.
