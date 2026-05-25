"""
Document Image OCR and Layout Analysis System  v2.1
"""

import cv2
import pytesseract
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import os
import json
import csv
from datetime import datetime

try:
    from cv_parser import cv_parse
    CV_PARSER_VAR = True
except ImportError:
    CV_PARSER_VAR = False

try:
    from aday_excel import aday_ekle_excel, excel_yenile, OPENPYXL_VAR, EXCEL_DOSYA
    EXCEL_VAR = OPENPYXL_VAR
except ImportError:
    EXCEL_VAR = False
    EXCEL_DOSYA = "candidate_pool.xlsx"

try:
    from pdf2image import convert_from_path
    PDF_SUPPORTED = True
except ImportError:
    PDF_SUPPORTED = False

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────
BG    = "#1e2130"
PANEL = "#252a3d"
CARD  = "#2a2f45"
INPUT = "#1a1e2e"
EDGE  = "#363d5a"
BLUE  = "#4a7fcc"
GREEN = "#3aaa7a"
TEXT  = "#d4daf0"
MUTED = "#6b7599"
WHITE = "#ffffff"

# ─────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────

def init_db(path="documents.db"):
    conn = sqlite3.connect(path)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT, date TEXT, text TEXT,
            word_count INTEGER, block_count INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name    TEXT,
            email        TEXT,
            phone        TEXT,
            city         TEXT,
            linkedin     TEXT,
            github       TEXT,
            education    TEXT,
            exp_years    REAL,
            exp_summary  TEXT,
            skills       TEXT,
            languages    TEXT,
            source_file  TEXT,
            notes        TEXT,
            date         TEXT
        )
    """)
    conn.commit()
    return conn

# ── Candidate CRUD ─────────────────────────────────

def add_candidate(conn, c: dict) -> int:
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO candidates
        (full_name, email, phone, city, linkedin, github,
         education, exp_years, exp_summary, skills, languages,
         source_file, notes, date)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        c.get("ad_soyad",""),   c.get("email",""),
        c.get("telefon",""),    c.get("sehir",""),
        c.get("linkedin",""),   c.get("github",""),
        c.get("egitim_ozet",""), c.get("deneyim_yil", 0),
        c.get("deneyim_ozet",""), c.get("beceri_str",""),
        c.get("dil_str",""),    c.get("kaynak_dosya",""),
        c.get("notlar",""),
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    conn.commit()
    return cur.lastrowid

def update_candidate_field(conn, cid: int, field: str, value):
    conn.cursor().execute(f"UPDATE candidates SET {field}=? WHERE id=?", (value, cid))
    conn.commit()

def delete_candidate(conn, cid: int):
    conn.cursor().execute("DELETE FROM candidates WHERE id=?", (cid,))
    conn.commit()

def get_all_candidates(conn) -> list:
    cur = conn.cursor()
    cur.execute("SELECT * FROM candidates ORDER BY id DESC")
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def filter_candidates(conn, filters: dict) -> list:
    conditions, params = [], []
    field_map = {
        "name":     "full_name",
        "city":     "city",
        "skill":    "skills",
        "language": "languages",
        "education":"education",
        "exp_min":  None,
    }
    for key, val in filters.items():
        if not str(val).strip():
            continue
        if key == "exp_min":
            try:
                conditions.append("exp_years >= ?")
                params.append(float(val))
            except ValueError:
                pass
        elif key in field_map and field_map[key]:
            conditions.append(f"{field_map[key]} LIKE ?")
            params.append(f"%{val}%")
    sql = "SELECT * FROM candidates"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY id DESC"
    cur = conn.cursor()
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

# ── Document CRUD ──────────────────────────────────

def save_document(conn, filename, text, word_count, block_count):
    conn.cursor().execute(
        "INSERT INTO documents (filename, date, text, word_count, block_count) VALUES (?,?,?,?,?)",
        (filename, datetime.now().strftime("%Y-%m-%d %H:%M"), text, word_count, block_count)
    )
    conn.commit()

def search_documents(conn, query):
    cur = conn.cursor()
    cur.execute("SELECT id, filename, date, word_count FROM documents WHERE text LIKE ?",
                (f"%{query}%",))
    return cur.fetchall()

def get_all_documents(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, filename, date, word_count FROM documents ORDER BY id DESC")
    return cur.fetchall()

def delete_document(conn, doc_id):
    conn.cursor().execute("DELETE FROM documents WHERE id=?", (doc_id,))
    conn.commit()

# ─────────────────────────────────────────────────
# IMAGE PROCESSING
# ─────────────────────────────────────────────────

def load_image(path):
    return cv2.imread(path)

def pil_to_cv2(pil_img):
    return cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)

def preprocess(img):
    gray   = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur   = cv2.GaussianBlur(gray, (3, 3), 0)
    _, thr = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thr

def adjust_brightness_contrast(img, brightness=0, contrast=1.0):
    return cv2.convertScaleAbs(img, alpha=contrast, beta=brightness)

def denoise(img):
    return cv2.medianBlur(img, 3)

def deskew(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(thr > 0))
    if len(coords) == 0:
        return img
    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    h, w  = gray.shape[:2]
    M     = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)

def edge_detection(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    return cv2.Canny(gray, 50, 150)

def find_text_blocks(img):
    gray   = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
    dilated = cv2.dilate(thr, kernel, iterations=3)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return [(x, y, w, h) for c in contours
            for x, y, w, h in [cv2.boundingRect(c)] if w > 50 and h > 10]

def run_ocr(img, lang="tur+eng"):
    processed = preprocess(img)
    pil_img   = Image.fromarray(processed)
    config    = "--psm 6 --oem 3"
    text      = pytesseract.image_to_string(pil_img, lang=lang, config=config)
    data      = pytesseract.image_to_data(pil_img, lang=lang, config=config,
                                          output_type=pytesseract.Output.DICT)
    words = [
        {"text": w, "x": data["left"][i], "y": data["top"][i],
         "width": data["width"][i], "height": data["height"][i],
         "conf": int(data["conf"][i])}
        for i, w in enumerate(data["text"])
        if w.strip() and int(data["conf"][i]) > 40
    ]
    return text.strip(), words

# ─────────────────────────────────────────────────
# TABLE DETECTION
# ─────────────────────────────────────────────────

def find_table_cells(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h_lines = cv2.morphologyEx(thr, cv2.MORPH_OPEN,
                               cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1)), iterations=2)
    v_lines = cv2.morphologyEx(thr, cv2.MORPH_OPEN,
                               cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40)), iterations=2)
    grid    = cv2.add(h_lines, v_lines)
    contours, _ = cv2.findContours(grid, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    total_area = img.shape[0] * img.shape[1]
    cells = [
        {"x": x, "y": y, "w": w, "h": h}
        for c in contours
        for x, y, w, h in [cv2.boundingRect(c)]
        if 500 < w * h < total_area * 0.8 and w > 20 and h > 10
    ]
    cells.sort(key=lambda c: (c["y"] // 20, c["x"]))
    return cells

def read_cells(img, cells, lang="tur+eng"):
    results = []
    for cell in cells:
        x, y, w, h = cell["x"], cell["y"], cell["w"], cell["h"]
        d   = 3
        crop = img[max(0, y+d):min(img.shape[0], y+h-d),
                   max(0, x+d):min(img.shape[1], x+w-d)]
        text = ""
        if crop.size > 0:
            pil = Image.fromarray(preprocess(crop))
            text = pytesseract.image_to_string(pil, lang=lang,
                                               config="--psm 7 --oem 3").strip()
        results.append({"x": x, "y": y, "w": w, "h": h, "text": text})
    return results

# ─────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────

def save_json(path, source, text, words, blocks):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "summary": {"word_count": len(words),
                        "block_count": len(blocks),
                        "char_count": len(text)},
            "text": text,
            "words": words,
            "blocks": [{"x": b[0], "y": b[1], "w": b[2], "h": b[3]} for b in blocks],
        }, f, ensure_ascii=False, indent=2)

def save_csv(path, words):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["text", "x", "y", "width", "height", "conf"])
        w.writeheader()
        w.writerows(words)

def save_table_csv(path, results):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["x", "y", "w", "h", "text"])
        w.writeheader()
        w.writerows(results)

# ─────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────

def numpy_to_tk(img, max_w=480, max_h=380):
    pil = Image.fromarray(img if len(img.shape) == 2
                          else cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pil.thumbnail((max_w, max_h), Image.LANCZOS)
    return ImageTk.PhotoImage(pil)

def flat_btn(parent, label, command, color=BLUE, fg=WHITE, **kw):
    return tk.Button(parent, text=label, command=command,
                     bg=color, fg=fg, activebackground=color,
                     activeforeground=fg, relief="flat",
                     font=("Segoe UI", 9), padx=12, pady=5,
                     cursor="hand2", **kw)

def lbl(parent, text="", **kw):
    return tk.Label(parent, text=text, bg=parent["bg"],
                    fg=TEXT, font=("Segoe UI", 10), **kw)

def section_header(parent, text):
    f = tk.Frame(parent, bg=CARD)
    tk.Label(f, text=text, bg=CARD, fg=MUTED,
             font=("Segoe UI", 9)).pack(side="left")
    tk.Frame(f, bg=EDGE, height=1).pack(side="left", fill="x",
                                         expand=True, padx=(8, 0), pady=6)
    return f

# ─────────────────────────────────────────────────
# APPLICATION
# ─────────────────────────────────────────────────

class App:

    def __init__(self, root):
        self.root = root
        self.root.title("Document OCR & Layout Analysis System")
        self.root.geometry("1280x780")
        self.root.minsize(960, 620)
        self.root.configure(bg=BG)

        self.active_img    = None
        self.processed_img = None
        self.active_path   = ""
        self.last_text     = ""
        self.last_words    = []
        self.last_blocks   = []
        self.pdf_pages     = []
        self.pdf_page_idx  = 0
        self.table_results = []
        self._selected_cid = None

        self.db = init_db()
        self._apply_style()
        self._build_ui()

    # ── STYLE ─────────────────────────────────────

    def _apply_style(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT,
                    fieldbackground=INPUT, font=("Segoe UI", 10))
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=TEXT)
        s.configure("TNotebook", background=PANEL, borderwidth=0, tabmargins=[0, 0, 0, 0])
        s.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                    padding=[16, 7], font=("Segoe UI", 10), borderwidth=0)
        s.map("TNotebook.Tab",
              background=[("selected", CARD), ("active", BG)],
              foreground=[("selected", TEXT),  ("active", TEXT)])
        s.configure("Treeview", background=CARD, foreground=TEXT,
                    fieldbackground=CARD, rowheight=28, borderwidth=0,
                    font=("Segoe UI", 10))
        s.configure("Treeview.Heading", background=PANEL, foreground=MUTED,
                    font=("Segoe UI", 9, "bold"), relief="flat", borderwidth=0)
        s.map("Treeview",
              background=[("selected", BLUE)],
              foreground=[("selected", WHITE)])
        s.configure("TScrollbar", background=PANEL, troughcolor=BG,
                    borderwidth=0, arrowsize=12, gripcount=0)

    # ── UI ────────────────────────────────────────

    def _build_ui(self):
        # Header bar
        header = tk.Frame(self.root, bg=PANEL, height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="Document OCR & Layout Analysis System",
                 bg=PANEL, fg=TEXT, font=("Segoe UI", 13, "bold")).pack(
                 side="left", padx=16, pady=12)
        tk.Label(header, text="OpenCV  ·  Tesseract  ·  SQLite",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(side="right", padx=16)

        # Notebook
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True)
        self.notebook = nb

        self._tab_analysis(nb)
        self._tab_table(nb)
        self._tab_candidates(nb)
        self._tab_database(nb)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        tk.Label(self.root, textvariable=self.status_var,
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9),
                 anchor="w", padx=12, pady=4).pack(fill="x", side="bottom")

    # ── TAB: ANALYSIS ─────────────────────────────

    def _tab_analysis(self, nb):
        tab = tk.Frame(nb, bg=BG)
        nb.add(tab, text="  Analysis  ")

        # Left panel
        left = tk.Frame(tab, bg=BG)
        left.pack(side="left", fill="both", padx=(10, 5), pady=10)
        left.configure(width=500)
        left.pack_propagate(False)

        # Preview box
        preview_frame = tk.Frame(left, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        preview_frame.pack(fill="both", expand=True, pady=(0, 8))
        lbl(preview_frame, "Preview").pack(anchor="w", padx=10, pady=(8, 0))

        self.img_label = tk.Label(preview_frame, bg=INPUT,
                                   text="Click here or use the buttons below\nto load an image or PDF.",
                                   fg=MUTED, font=("Segoe UI", 10), cursor="hand2")
        self.img_label.pack(fill="both", expand=True, padx=8, pady=(4, 4))
        self.img_label.bind("<Button-1>", lambda e: self.load_image_btn())

        # PDF navigator (hidden initially)
        self.pdf_nav = tk.Frame(preview_frame, bg=CARD)
        flat_btn(self.pdf_nav, "< Prev", self.pdf_prev_page, color=PANEL).pack(side="left", padx=4, pady=4)
        self.pdf_page_var = tk.StringVar(value="Page 1 / 1")
        tk.Label(self.pdf_nav, textvariable=self.pdf_page_var,
                 bg=CARD, fg=TEXT, font=("Segoe UI", 9),
                 width=14, anchor="center").pack(side="left")
        flat_btn(self.pdf_nav, "Next >", self.pdf_next_page, color=PANEL).pack(side="left", padx=4, pady=4)

        # Main buttons
        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", pady=(0, 8))
        flat_btn(btn_row, "Load Image", self.load_image_btn).pack(side="left", padx=(0, 6))
        flat_btn(btn_row, "Load PDF",   self.load_pdf_btn).pack(side="left", padx=(0, 6))
        flat_btn(btn_row, "Run OCR",    self.run_ocr_btn, color=GREEN).pack(side="left", padx=(0, 6))
        flat_btn(btn_row, "Save",       self.save_document_btn, color=PANEL).pack(side="left")

        # Image enhancement
        enh = tk.Frame(left, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        enh.pack(fill="x")
        section_header(enh, "Image Enhancement").pack(fill="x", padx=10, pady=(6, 2))

        sliders = tk.Frame(enh, bg=CARD)
        sliders.pack(fill="x", padx=10, pady=(0, 4))

        tk.Label(sliders, text="Brightness", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9), width=10, anchor="w").grid(row=0, column=0, sticky="w")
        self.brightness = tk.IntVar(value=0)
        tk.Scale(sliders, from_=-100, to=100, orient="horizontal",
                 variable=self.brightness, bg=CARD, fg=TEXT,
                 highlightbackground=CARD, troughcolor=INPUT,
                 activebackground=BLUE, showvalue=True, length=230,
                 command=self._live_update).grid(row=0, column=1, sticky="ew", padx=4)

        tk.Label(sliders, text="Contrast", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9), width=10, anchor="w").grid(row=1, column=0, sticky="w")
        self.contrast = tk.DoubleVar(value=1.0)
        tk.Scale(sliders, from_=0.5, to=3.0, resolution=0.1, orient="horizontal",
                 variable=self.contrast, bg=CARD, fg=TEXT,
                 highlightbackground=CARD, troughcolor=INPUT,
                 activebackground=BLUE, showvalue=True, length=230,
                 command=self._live_update).grid(row=1, column=1, sticky="ew", padx=4)

        ops = tk.Frame(enh, bg=CARD)
        ops.pack(fill="x", padx=10, pady=(2, 10))
        for label, cmd in [
            ("Denoise",        self.denoise_btn),
            ("Deskew",         self.deskew_btn),
            ("Edge Detection", self.edge_btn),
            ("Reset",          self.reset_btn),
        ]:
            flat_btn(ops, label, cmd, color=PANEL).pack(side="left", padx=(0, 6))

        # Right panel
        right = tk.Frame(tab, bg=BG)
        right.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)

        # Stats row
        stats = tk.Frame(right, bg=BG)
        stats.pack(fill="x", pady=(0, 8))
        self.v_words = tk.StringVar(value="—")
        self.v_blocks = tk.StringVar(value="—")
        self.v_chars  = tk.StringVar(value="—")
        for title, var in [("Words", self.v_words),
                            ("Blocks", self.v_blocks),
                            ("Characters", self.v_chars)]:
            box = tk.Frame(stats, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
            box.pack(side="left", fill="x", expand=True, padx=(0, 6))
            tk.Label(box, text=title, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(pady=(8, 0))
            tk.Label(box, textvariable=var, bg=CARD, fg=TEXT,
                     font=("Segoe UI", 20, "bold")).pack(pady=(2, 8))

        # Extracted text
        text_frame = tk.Frame(right, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        text_frame.pack(fill="both", expand=True, pady=(0, 8))

        text_header = tk.Frame(text_frame, bg=CARD)
        text_header.pack(fill="x", padx=10, pady=(8, 0))
        lbl(text_header, "Extracted Text").pack(side="left")
        self.status_lbl = tk.Label(text_header, text="", bg=CARD, fg=MUTED, font=("Segoe UI", 9))
        self.status_lbl.pack(side="right")

        text_inner = tk.Frame(text_frame, bg=CARD)
        text_inner.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self.text_box = tk.Text(text_inner, bg=INPUT, fg=TEXT, font=("Consolas", 10),
                                 wrap="word", insertbackground=TEXT, relief="flat",
                                 padx=10, pady=8, selectbackground=BLUE)
        sb = tk.Scrollbar(text_inner, command=self.text_box.yview,
                          bg=PANEL, troughcolor=BG, relief="flat")
        self.text_box.config(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text_box.pack(fill="both", expand=True)

        # Action buttons — always visible
        action_row = tk.Frame(right, bg=BG)
        action_row.pack(fill="x")
        flat_btn(action_row, "Copy",         self.copy_text,     color=GREEN).pack(side="left", padx=(0, 6))
        flat_btn(action_row, "Export JSON",  self.export_json,   color=PANEL).pack(side="left", padx=(0, 6))
        flat_btn(action_row, "Export CSV",   self.export_csv,    color=PANEL).pack(side="left", padx=(0, 6))
        flat_btn(action_row, "Save as CV",   self.save_as_cv,    color="#5a3e8a").pack(side="left")

    # ── TAB: TABLE DETECTION ──────────────────────

    def _tab_table(self, nb):
        tab = tk.Frame(nb, bg=BG)
        nb.add(tab, text="  Table Detection  ")

        top = tk.Frame(tab, bg=BG)
        top.pack(fill="x", padx=10, pady=10)
        flat_btn(top, "Scan Table", self.scan_table, color=GREEN).pack(side="left", padx=(0, 6))
        flat_btn(top, "Export CSV", self.export_table_csv, color=PANEL).pack(side="left")
        self.cell_count_var = tk.StringVar(value="")
        tk.Label(top, textvariable=self.cell_count_var,
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(side="right")

        content = tk.Frame(tab, bg=BG)
        content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left_f = tk.Frame(content, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        left_f.pack(side="left", fill="both", expand=True, padx=(0, 6))
        lbl(left_f, "Cell Visualization").pack(anchor="w", padx=10, pady=(8, 4))
        self.table_img_label = tk.Label(left_f, bg=INPUT, fg=MUTED,
                                         font=("Segoe UI", 10),
                                         text="Load an image in the Analysis tab,\nthen click 'Scan Table'.")
        self.table_img_label.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        right_f = tk.Frame(content, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        right_f.pack(side="right", fill="both", expand=True)
        lbl(right_f, "Cell Contents").pack(anchor="w", padx=10, pady=(8, 4))

        tree_ic = tk.Frame(right_f, bg=CARD)
        tree_ic.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        cols = ("no", "position", "text")
        self.cell_tree = ttk.Treeview(tree_ic, columns=cols, show="headings")
        self.cell_tree.heading("no",       text="#")
        self.cell_tree.heading("position", text="Position")
        self.cell_tree.heading("text",     text="Content")
        self.cell_tree.column("no",       width=35,  anchor="center")
        self.cell_tree.column("position", width=110, anchor="center")
        self.cell_tree.column("text",     width=260)
        sb2 = tk.Scrollbar(tree_ic, command=self.cell_tree.yview,
                            bg=PANEL, troughcolor=BG, relief="flat")
        self.cell_tree.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        self.cell_tree.pack(fill="both", expand=True)

    # ── TAB: CANDIDATE POOL ───────────────────────

    def _tab_candidates(self, nb):
        tab = tk.Frame(nb, bg=BG)
        nb.add(tab, text="  Candidate Pool  ")

        # ── Filter + scoring panel ──
        top_panel = tk.Frame(tab, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        top_panel.pack(fill="x", padx=8, pady=(8, 4))

        # Filters (left)
        filter_f = tk.Frame(top_panel, bg=PANEL)
        filter_f.pack(side="left", fill="x", expand=True, padx=10, pady=8)

        tk.Label(filter_f, text="FILTERS", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).grid(row=0, column=0, columnspan=6,
                                                     sticky="w", pady=(0, 4))

        self._filter_vars = {}
        filters = [
            ("Name",             "name"),
            ("City",             "city"),
            ("Skill",            "skill"),
            ("Language",         "language"),
            ("Education",        "education"),
            ("Min. Exp. (years)","exp_min"),
        ]
        for i, (label, key) in enumerate(filters):
            row = i // 3
            col = (i % 3) * 2
            tk.Label(filter_f, text=label, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 9)).grid(row=row*2+1, column=col,
                                                sticky="w", padx=(0, 4))
            var = tk.StringVar()
            var.trace_add("write", lambda *a: self._apply_filters())
            self._filter_vars[key] = var
            tk.Entry(filter_f, textvariable=var, bg=INPUT, fg=TEXT,
                     insertbackground=TEXT, relief="flat",
                     font=("Segoe UI", 10), width=16).grid(
                     row=row*2+2, column=col, sticky="ew", padx=(0, 14), ipady=3)

        # Scoring (right)
        score_f = tk.Frame(top_panel, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        score_f.pack(side="right", padx=10, pady=8)

        tk.Label(score_f, text="MATCH SCORE CRITERIA", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=8, pady=(4, 2))

        tk.Label(score_f, text="Required skills (comma-separated):", bg=PANEL,
                 fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=8)
        self._score_skills = tk.StringVar()
        tk.Entry(score_f, textvariable=self._score_skills, bg=INPUT, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 10), width=28).pack(padx=8, pady=(2, 4), ipady=3, fill="x")

        tk.Label(score_f, text="Min. experience (years):", bg=PANEL,
                 fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=8)
        self._score_exp = tk.StringVar(value="0")
        tk.Entry(score_f, textvariable=self._score_exp, bg=INPUT, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 10), width=10).pack(padx=8, pady=(2, 4), ipady=3, anchor="w")

        tk.Label(score_f, text="Required language:", bg=PANEL,
                 fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=8)
        self._score_lang = tk.StringVar()
        tk.Entry(score_f, textvariable=self._score_lang, bg=INPUT, fg=TEXT,
                 insertbackground=TEXT, relief="flat",
                 font=("Segoe UI", 10), width=18).pack(padx=8, pady=(2, 6), ipady=3, anchor="w")

        flat_btn(score_f, "Score & Rank", self._compute_scores,
                 color=BLUE).pack(padx=8, pady=(0, 8), fill="x")

        # ── Candidate list ──
        list_f = tk.Frame(tab, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        list_f.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        list_top = tk.Frame(list_f, bg=CARD)
        list_top.pack(fill="x", padx=10, pady=(8, 4))
        self.cand_count_var = tk.StringVar(value="")
        lbl(list_top, "Candidate List").pack(side="left")
        tk.Label(list_top, textvariable=self.cand_count_var,
                 bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side="left", padx=8)

        btn_f = tk.Frame(list_top, bg=CARD)
        btn_f.pack(side="right")
        flat_btn(btn_f, "Show All",      self._list_candidates,   color=PANEL).pack(side="left", padx=(0, 4))
        flat_btn(btn_f, "Export Excel",  self._export_excel,      color=PANEL).pack(side="left", padx=(0, 4))
        flat_btn(btn_f, "Delete",        self._delete_candidate,  color="#8b1a1a").pack(side="left")

        # Treeview
        cols2 = ("id", "full_name", "city", "education",
                 "exp_years", "skills", "languages", "score")
        self.cand_tree = ttk.Treeview(list_f, columns=cols2,
                                       show="headings", selectmode="browse")
        headers = {
            "id":        ("#",            45,  True),
            "full_name": ("Name",        160,  False),
            "city":      ("City",         90,  True),
            "education": ("Education",   180,  False),
            "exp_years": ("Exp. (yrs)",   90,  True),
            "skills":    ("Skills",      200,  False),
            "languages": ("Languages",   110,  False),
            "score":     ("Match %",      70,  True),
        }
        for col, (title, width, center) in headers.items():
            self.cand_tree.heading(col, text=title,
                                    command=lambda c=col: self._sort_by(c))
            self.cand_tree.column(col, width=width,
                                   anchor="center" if center else "w")

        sb3 = tk.Scrollbar(list_f, command=self.cand_tree.yview,
                            bg=PANEL, troughcolor=BG, relief="flat")
        self.cand_tree.configure(yscrollcommand=sb3.set)
        sb3.pack(side="right", fill="y")
        self.cand_tree.pack(fill="both", expand=True, padx=(8, 0), pady=(0, 8))
        self.cand_tree.bind("<<TreeviewSelect>>", self._show_candidate_detail)
        self.cand_tree.tag_configure("good", background="#1e3a2a", foreground=TEXT)
        self.cand_tree.tag_configure("mid",  background="#2a2f45", foreground=TEXT)
        self.cand_tree.tag_configure("low",  background="#2a1e1e", foreground=TEXT)

        # ── Detail panel ──
        detail_f = tk.Frame(tab, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        detail_f.pack(fill="x", padx=8, pady=(0, 8))
        lbl(detail_f, "Selected Candidate Details").pack(anchor="w", padx=10, pady=(8, 2))

        detail_inner = tk.Frame(detail_f, bg=CARD)
        detail_inner.pack(fill="x", padx=10, pady=(0, 8))

        left_d = tk.Frame(detail_inner, bg=CARD)
        left_d.pack(side="left", fill="x", expand=True)

        self._detail_vars = {}
        detail_fields = [
            ("Email",    "email"),
            ("Phone",    "phone"),
            ("LinkedIn", "linkedin"),
            ("GitHub",   "github"),
        ]
        for i, (label, key) in enumerate(detail_fields):
            r, c = i // 2, (i % 2) * 2
            tk.Label(left_d, text=label+":", bg=CARD, fg=MUTED,
                     font=("Segoe UI", 9)).grid(row=r, column=c,
                                                sticky="w", padx=(0, 4), pady=2)
            var = tk.StringVar()
            self._detail_vars[key] = var
            tk.Label(left_d, textvariable=var, bg=CARD, fg=TEXT,
                     font=("Segoe UI", 10), anchor="w").grid(
                     row=r, column=c+1, sticky="w", padx=(0, 20), pady=2)

        right_d = tk.Frame(detail_inner, bg=CARD)
        right_d.pack(side="right", fill="x", expand=True)
        tk.Label(right_d, text="Notes:", bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")
        self._notes_box = tk.Text(right_d, bg=INPUT, fg=TEXT, font=("Segoe UI", 10),
                                   height=3, relief="flat", padx=6, pady=4,
                                   insertbackground=TEXT, wrap="word")
        self._notes_box.pack(fill="x", pady=(2, 4))
        flat_btn(right_d, "Save Note", self._save_note, color=PANEL).pack(anchor="e")

        self._list_candidates()

    # ── TAB: DATABASE ─────────────────────────────

    def _tab_database(self, nb):
        tab = tk.Frame(nb, bg=BG)
        nb.add(tab, text="  Database  ")

        # Search row
        search_f = tk.Frame(tab, bg=BG)
        search_f.pack(fill="x", padx=10, pady=10)
        tk.Label(search_f, text="Search:", bg=BG, fg=MUTED,
                 font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))
        self.search_entry = tk.Entry(search_f, bg=INPUT, fg=TEXT,
                                      insertbackground=TEXT, relief="flat",
                                      font=("Segoe UI", 10), width=34)
        self.search_entry.pack(side="left", ipady=4, padx=(0, 6))
        self.search_entry.bind("<Return>", lambda e: self.search_docs())
        flat_btn(search_f, "Search",   self.search_docs).pack(side="left", padx=(0, 6))
        flat_btn(search_f, "Show All", self.show_all_docs, color=PANEL).pack(side="left")
        flat_btn(search_f, "Delete",   self.delete_doc,   color="#8b1a1a").pack(side="right")

        # Documents table
        doc_f = tk.Frame(tab, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        doc_f.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        lbl(doc_f, "Saved Documents").pack(anchor="w", padx=10, pady=(8, 4))

        doc_inner = tk.Frame(doc_f, bg=CARD)
        doc_inner.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        doc_cols = ("id", "filename", "date", "word_count")
        self.doc_tree = ttk.Treeview(doc_inner, columns=doc_cols, show="headings")
        self.doc_tree.heading("id",         text="#")
        self.doc_tree.heading("filename",   text="Filename")
        self.doc_tree.heading("date",       text="Date")
        self.doc_tree.heading("word_count", text="Words")
        self.doc_tree.column("id",         width=40,  anchor="center")
        self.doc_tree.column("filename",   width=400)
        self.doc_tree.column("date",       width=155, anchor="center")
        self.doc_tree.column("word_count", width=80,  anchor="center")

        sb4 = tk.Scrollbar(doc_inner, command=self.doc_tree.yview,
                            bg=PANEL, troughcolor=BG, relief="flat")
        self.doc_tree.configure(yscrollcommand=sb4.set)
        sb4.pack(side="right", fill="y")
        self.doc_tree.pack(fill="both", expand=True)
        self.doc_tree.bind("<<TreeviewSelect>>", self._show_doc_text)

        # Selected document text
        sel_f = tk.Frame(tab, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
        sel_f.pack(fill="x", padx=10, pady=(0, 10))
        lbl(sel_f, "Selected Document Text").pack(anchor="w", padx=10, pady=(8, 4))
        self.selected_text = tk.Text(sel_f, bg=INPUT, fg=TEXT, font=("Consolas", 10),
                                      height=5, wrap="word", relief="flat",
                                      padx=10, pady=8, selectbackground=BLUE)
        self.selected_text.pack(fill="x", padx=8, pady=(0, 8))

        self.show_all_docs()

    # ── IMAGE LOADING ─────────────────────────────

    def load_image_btn(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("All Files", "*.*")]
        )
        if not path:
            return
        self.active_path   = path
        self.active_img    = load_image(path)
        self.processed_img = self.active_img.copy()
        self.pdf_pages     = []
        self.pdf_nav.pack_forget()
        self.brightness.set(0)
        self.contrast.set(1.0)
        self._show_image(self.processed_img)
        self._clear()
        self.status_var.set(f"Loaded: {os.path.basename(path)}")

    def load_pdf_btn(self):
        if not PDF_SUPPORTED:
            messagebox.showerror("Missing Library",
                "PDF support requires:\n\n  pip install pdf2image\n\n"
                "Poppler is also required:\n"
                "https://github.com/oschwartz10612/poppler-windows/releases")
            return
        path = filedialog.askopenfilename(
            title="Select PDF",
            filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
        )
        if not path:
            return
        self.status_var.set("Converting PDF...")
        self.root.update()
        try:
            pages = convert_from_path(path, dpi=200)
        except Exception as e:
            messagebox.showerror("PDF Error", f"Could not open PDF:\n{e}")
            self.status_var.set("Error: could not open PDF")
            return
        self.pdf_pages    = [pil_to_cv2(p) for p in pages]
        self.pdf_page_idx = 0
        self.active_path  = path
        self._show_pdf_page()
        self.pdf_nav.pack(pady=(0, 4))
        self.status_var.set(f"PDF loaded: {os.path.basename(path)}  ({len(self.pdf_pages)} pages)")

    def _show_pdf_page(self):
        idx = self.pdf_page_idx
        self.active_img    = self.pdf_pages[idx]
        self.processed_img = self.active_img.copy()
        self.brightness.set(0)
        self.contrast.set(1.0)
        self._show_image(self.processed_img)
        self._clear()
        self.pdf_page_var.set(f"Page {idx+1} / {len(self.pdf_pages)}")

    def pdf_prev_page(self):
        if self.pdf_page_idx > 0:
            self.pdf_page_idx -= 1
            self._show_pdf_page()

    def pdf_next_page(self):
        if self.pdf_page_idx < len(self.pdf_pages) - 1:
            self.pdf_page_idx += 1
            self._show_pdf_page()

    def _show_image(self, img):
        tk_img = numpy_to_tk(img)
        self.img_label.config(image=tk_img, text="")
        self.img_label.image = tk_img

    def _live_update(self, _=None):
        if self.active_img is None:
            return
        self.processed_img = adjust_brightness_contrast(
            self.active_img, self.brightness.get(), self.contrast.get())
        self._show_image(self.processed_img)

    def denoise_btn(self):
        if self.processed_img is None:
            messagebox.showwarning("Warning", "Load an image first!"); return
        self.processed_img = denoise(self.processed_img)
        self._show_image(self.processed_img)

    def deskew_btn(self):
        if self.processed_img is None:
            messagebox.showwarning("Warning", "Load an image first!"); return
        self.processed_img = deskew(self.processed_img)
        self._show_image(self.processed_img)

    def edge_btn(self):
        if self.processed_img is None:
            messagebox.showwarning("Warning", "Load an image first!"); return
        self._show_image(edge_detection(self.processed_img))

    def reset_btn(self):
        if self.active_img is None:
            return
        self.processed_img = self.active_img.copy()
        self.brightness.set(0)
        self.contrast.set(1.0)
        self._show_image(self.processed_img)

    def _clear(self):
        self.last_text = ""; self.last_words = []; self.last_blocks = []
        self.text_box.delete("1.0", "end")
        self.status_lbl.config(text="")
        self.v_words.set("—"); self.v_blocks.set("—"); self.v_chars.set("—")

    # ── OCR ───────────────────────────────────────

    def run_ocr_btn(self):
        if self.processed_img is None:
            messagebox.showwarning("Warning", "Load an image first!"); return
        self.status_lbl.config(text="Processing...")
        self.status_var.set("Running OCR...")
        self.root.update()

        text, words  = run_ocr(self.processed_img)
        blocks       = find_text_blocks(self.processed_img)
        self.last_text, self.last_words, self.last_blocks = text, words, blocks

        out = self.processed_img.copy()
        for w in words:
            cv2.rectangle(out, (w["x"], w["y"]),
                          (w["x"]+w["width"], w["y"]+w["height"]), (0, 180, 80), 1)
        for (x, y, w2, h) in blocks:
            cv2.rectangle(out, (x, y), (x+w2, y+h), (74, 127, 204), 2)
        self._show_image(out)

        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", text if text else "(No text found)")
        self.v_words.set(str(len(words)))
        self.v_blocks.set(str(len(blocks)))
        self.v_chars.set(str(len(text)))
        self.status_lbl.config(text="Done")
        self.status_var.set(f"OCR complete  —  {os.path.basename(self.active_path)}")

    # ── COPY ──────────────────────────────────────

    def copy_text(self):
        text = self.text_box.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Warning", "Run OCR first!"); return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        self.status_lbl.config(text="Copied to clipboard")
        self.root.after(2000, lambda: self.status_lbl.config(text="Done"))

    # ── EXPORT ────────────────────────────────────

    def export_json(self):
        if not self.last_text and not self.last_words:
            messagebox.showwarning("Warning", "Run OCR first!"); return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")],
            initialfile=os.path.splitext(os.path.basename(self.active_path))[0] + "_ocr.json")
        if not path: return
        save_json(path, self.active_path, self.last_text, self.last_words, self.last_blocks)
        messagebox.showinfo("Success", f"JSON saved:\n{path}")
        self.status_var.set(f"JSON saved: {os.path.basename(path)}")

    def export_csv(self):
        if not self.last_words:
            messagebox.showwarning("Warning", "Run OCR first!"); return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=os.path.splitext(os.path.basename(self.active_path))[0] + "_words.csv")
        if not path: return
        save_csv(path, self.last_words)
        messagebox.showinfo("Success", f"CSV saved:\n{path}")
        self.status_var.set(f"CSV saved: {os.path.basename(path)}")

    # ── TABLE DETECTION ───────────────────────────

    def scan_table(self):
        if self.processed_img is None:
            messagebox.showwarning("Warning", "Load an image in the Analysis tab first!"); return
        self.status_var.set("Scanning table..."); self.root.update()
        cells = find_table_cells(self.processed_img)
        if not cells:
            messagebox.showinfo("Result",
                "No table detected in this image.\n\nTip: Images with clear grid lines work best.")
            self.status_var.set("No table found"); return

        self.status_var.set(f"Reading {len(cells)} cells..."); self.root.update()
        self.table_results = read_cells(self.processed_img, cells)

        out = self.processed_img.copy()
        for i, c in enumerate(self.table_results):
            cv2.rectangle(out, (c["x"], c["y"]),
                          (c["x"]+c["w"], c["y"]+c["h"]), (74, 127, 204), 2)
            cv2.putText(out, str(i+1), (c["x"]+3, c["y"]+15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.44, (74, 127, 204), 1)
        tk_img = numpy_to_tk(out, max_w=550, max_h=460)
        self.table_img_label.config(image=tk_img, text="")
        self.table_img_label.image = tk_img

        for row in self.cell_tree.get_children():
            self.cell_tree.delete(row)
        for i, c in enumerate(self.table_results):
            self.cell_tree.insert("", "end", values=(
                i+1, f"({c['x']}, {c['y']})",
                c["text"].replace("\n", " ").strip()))

        filled = sum(1 for c in self.table_results if c["text"].strip())
        self.cell_count_var.set(f"{len(self.table_results)} cells  —  {filled} filled")
        self.status_var.set(f"{len(self.table_results)} cells detected")

    def export_table_csv(self):
        if not self.table_results:
            messagebox.showwarning("Warning", "Click 'Scan Table' first!"); return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile="table_results.csv")
        if not path: return
        save_table_csv(path, self.table_results)
        messagebox.showinfo("Success", f"Table CSV saved:\n{path}")

    # ── CV / CANDIDATE ────────────────────────────

    def save_as_cv(self):
        if not self.last_text:
            messagebox.showwarning("Warning", "Run OCR first!"); return
        if not CV_PARSER_VAR:
            messagebox.showerror("Error", "cv_parser.py not found!"); return
        candidate = cv_parse(self.last_text)
        candidate["kaynak_dosya"] = os.path.basename(self.active_path)
        self._open_cv_editor(candidate)

    def _open_cv_editor(self, candidate: dict):
        win = tk.Toplevel(self.root)
        win.title("Review & Edit CV Data")
        win.geometry("580x640")
        win.configure(bg=BG)
        win.resizable(False, True)
        win.grab_set()

        tk.Label(win, text="Review and edit the extracted CV information before saving:",
                 bg=BG, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=14, pady=(10, 4))

        canvas = tk.Canvas(win, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=14, pady=4)

        inner = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        fields = [
            ("Full Name",        "ad_soyad"),
            ("Email",            "email"),
            ("Phone",            "telefon"),
            ("City",             "sehir"),
            ("LinkedIn",         "linkedin"),
            ("GitHub",           "github"),
            ("Education",        "egitim_ozet"),
            ("Experience (yrs)", "deneyim_yil"),
            ("Experience Summary","deneyim_ozet"),
            ("Skills",           "beceri_str"),
            ("Languages",        "dil_str"),
            ("Notes (GPA etc.)", "notlar"),
        ]
        entries = {}
        for label, key in fields:
            row = tk.Frame(inner, bg=BG)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=label+":", bg=BG, fg=MUTED,
                     font=("Segoe UI", 9), width=17, anchor="w").pack(side="left")
            var = tk.StringVar(value=str(candidate.get(key, "")))
            entries[key] = var
            tk.Entry(row, textvariable=var, bg=INPUT, fg=TEXT,
                     insertbackground=TEXT, relief="flat",
                     font=("Segoe UI", 10)).pack(side="left", fill="x", expand=True, ipady=4)

        def save_and_close():
            for key, var in entries.items():
                candidate[key] = var.get()
            try:
                candidate["deneyim_yil"] = float(candidate.get("deneyim_yil") or 0)
            except ValueError:
                candidate["deneyim_yil"] = 0.0

            cid = add_candidate(self.db, candidate)
            candidate["id"] = cid

            if EXCEL_VAR:
                try:
                    candidate["eklenme_tarihi"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    aday_ekle_excel(candidate, EXCEL_DOSYA)
                except Exception:
                    pass

            win.destroy()
            self._list_candidates()
            self.notebook.select(2)
            self.status_var.set(f"Candidate added: {candidate.get('ad_soyad','')}")

        btn_row = tk.Frame(win, bg=BG)
        btn_row.pack(fill="x", padx=14, pady=8)
        flat_btn(btn_row, "Save",   save_and_close, color=GREEN).pack(side="left", padx=(0, 8))
        flat_btn(btn_row, "Cancel", win.destroy,    color=PANEL).pack(side="left")

    def _list_candidates(self, candidates=None):
        if candidates is None:
            candidates = get_all_candidates(self.db)
        for row in self.cand_tree.get_children():
            self.cand_tree.delete(row)
        for c in candidates:
            score = c.get("score", "")
            if isinstance(score, (int, float)):
                tag = "good" if score >= 70 else ("mid" if score >= 40 else "low")
            else:
                tag = "mid"; score = ""
            self.cand_tree.insert("", "end", iid=str(c["id"]), tags=(tag,), values=(
                c["id"],
                c.get("full_name",""),
                c.get("city",""),
                c.get("education","")[:50],
                c.get("exp_years",""),
                c.get("skills","")[:60],
                c.get("languages","")[:40],
                score,
            ))
        self.cand_count_var.set(f"{len(candidates)} candidates")

    def _apply_filters(self):
        filters = {k: v.get() for k, v in self._filter_vars.items()}
        self._list_candidates(filter_candidates(self.db, filters))

    def _compute_scores(self):
        req_skills = [s.strip().lower() for s in
                      self._score_skills.get().split(",") if s.strip()]
        try:
            min_exp = float(self._score_exp.get() or 0)
        except ValueError:
            min_exp = 0
        req_lang = self._score_lang.get().strip().lower()

        candidates = get_all_candidates(self.db)
        for c in candidates:
            score = 0
            # Skills (max 60)
            if req_skills:
                c_skills = c.get("skills","").lower()
                matched  = sum(1 for s in req_skills if s in c_skills)
                score   += int((matched / len(req_skills)) * 60)
            else:
                score += 30
            # Experience (max 25)
            c_exp = float(c.get("exp_years", 0) or 0)
            if min_exp > 0:
                score += min(25, int((c_exp / min_exp) * 25))
            else:
                score += 15
            # Language (max 15)
            if req_lang:
                if req_lang in c.get("languages","").lower():
                    score += 15
            else:
                score += 8
            c["score"] = min(score, 100)

        candidates.sort(key=lambda c: c.get("score", 0), reverse=True)
        self._list_candidates(candidates)

    def _sort_by(self, col):
        candidates = get_all_candidates(self.db)
        try:
            candidates.sort(key=lambda c: (c.get(col) or 0)
                            if col == "exp_years" else str(c.get(col) or ""))
        except Exception:
            pass
        self._list_candidates(candidates)

    def _show_candidate_detail(self, _=None):
        sel = self.cand_tree.selection()
        if not sel: return
        cid = int(sel[0])
        self._selected_cid = cid
        cur = self.db.cursor()
        cur.execute("SELECT * FROM candidates WHERE id=?", (cid,))
        row = cur.fetchone()
        if not row: return
        c = dict(zip([d[0] for d in cur.description], row))
        # Map DB columns to detail vars
        mapping = {"email":"email","phone":"phone","linkedin":"linkedin","github":"github"}
        for var_key, db_key in mapping.items():
            self._detail_vars[var_key].set(c.get(db_key,"") or "")
        self._notes_box.delete("1.0","end")
        self._notes_box.insert("1.0", c.get("notes","") or "")

    def _save_note(self):
        if self._selected_cid is None:
            messagebox.showwarning("Warning","Select a candidate first!"); return
        note = self._notes_box.get("1.0","end").strip()
        update_candidate_field(self.db, self._selected_cid, "notes", note)
        self.status_var.set("Note saved.")

    def _delete_candidate(self):
        sel = self.cand_tree.selection()
        if not sel:
            messagebox.showwarning("Warning","Select a candidate to delete!"); return
        if messagebox.askyesno("Confirm","Delete this candidate?"):
            delete_candidate(self.db, int(sel[0]))
            self._list_candidates()

    def _export_excel(self):
        if not EXCEL_VAR:
            messagebox.showerror("Missing Library","Excel export requires:\n\n  pip install openpyxl"); return
        candidates = get_all_candidates(self.db)
        if not candidates:
            messagebox.showwarning("Warning","No candidates in the pool yet!"); return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")],
            initialfile=EXCEL_DOSYA)
        if not path: return
        # Map to Turkish field names expected by excel module
        mapped = []
        for c in candidates:
            mapped.append({
                "id": c["id"], "ad_soyad": c.get("full_name",""),
                "email": c.get("email",""), "telefon": c.get("phone",""),
                "sehir": c.get("city",""), "linkedin": c.get("linkedin",""),
                "github": c.get("github",""), "egitim_ozet": c.get("education",""),
                "deneyim_yil": c.get("exp_years",""),
                "deneyim_ozet": c.get("exp_summary",""),
                "beceri_str": c.get("skills",""), "dil_str": c.get("languages",""),
                "kaynak_dosya": c.get("source_file",""),
                "eklenme_tarihi": c.get("date",""),
                "notlar": c.get("notes",""),
            })
        try:
            excel_yenile(mapped, path)
            messagebox.showinfo("Success", f"Excel saved:\n{path}")
            self.status_var.set(f"Excel saved: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── DATABASE TAB ──────────────────────────────

    def save_document_btn(self):
        if not self.last_text and not self.last_words:
            messagebox.showwarning("Warning","Run OCR first!"); return
        save_document(self.db, os.path.basename(self.active_path),
                      self.last_text, len(self.last_words), len(self.last_blocks))
        messagebox.showinfo("Success","Document saved to database!")
        self.show_all_docs()
        self.notebook.select(3)

    def search_docs(self):
        q = self.search_entry.get().strip()
        self._fill_doc_tree(search_documents(self.db, q) if q else get_all_documents(self.db))

    def show_all_docs(self):
        self._fill_doc_tree(get_all_documents(self.db))

    def _fill_doc_tree(self, data):
        for row in self.doc_tree.get_children():
            self.doc_tree.delete(row)
        for row in data:
            self.doc_tree.insert("","end",values=row)

    def _show_doc_text(self, _=None):
        sel = self.doc_tree.selection()
        if not sel: return
        doc_id = self.doc_tree.item(sel[0])["values"][0]
        cur = self.db.cursor()
        cur.execute("SELECT text FROM documents WHERE id=?", (doc_id,))
        row = cur.fetchone()
        if row:
            self.selected_text.delete("1.0","end")
            self.selected_text.insert("1.0", row[0])

    def delete_doc(self):
        sel = self.doc_tree.selection()
        if not sel:
            messagebox.showwarning("Warning","Select a document to delete!"); return
        doc_id = self.doc_tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Confirm","Delete this document?"):
            delete_document(self.db, doc_id)
            self.show_all_docs()


# ─────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
