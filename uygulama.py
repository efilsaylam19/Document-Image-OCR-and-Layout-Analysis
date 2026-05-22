"""
Document Image OCR and Layout Analysis
Final Projesi - Tam Uygulama
Kullanılan: OpenCV, pytesseract, Tkinter, SQLite
"""

import cv2
import pytesseract
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sqlite3
import os
from datetime import datetime

# Windows Tesseract yolu
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─────────────────────────────────────────────────
# VERİTABANI
# ─────────────────────────────────────────────────

def veritabani_baslat(db_yolu="belgeler.db"):
    baglanti = sqlite3.connect(db_yolu)
    cursor = baglanti.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS belgeler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dosya_adi TEXT,
            tarih TEXT,
            metin TEXT,
            kelime_sayisi INTEGER,
            blok_sayisi INTEGER
        )
    """)
    baglanti.commit()
    return baglanti

def belge_kaydet(baglanti, dosya_adi, metin, kelime_sayisi, blok_sayisi):
    cursor = baglanti.cursor()
    cursor.execute("""
        INSERT INTO belgeler (dosya_adi, tarih, metin, kelime_sayisi, blok_sayisi)
        VALUES (?, ?, ?, ?, ?)
    """, (dosya_adi, datetime.now().strftime("%Y-%m-%d %H:%M"), metin, kelime_sayisi, blok_sayisi))
    baglanti.commit()

def belge_ara(baglanti, arama):
    cursor = baglanti.cursor()
    cursor.execute("SELECT id, dosya_adi, tarih, kelime_sayisi FROM belgeler WHERE metin LIKE ?",
                   (f"%{arama}%",))
    return cursor.fetchall()

def tum_belgeler(baglanti):
    cursor = baglanti.cursor()
    cursor.execute("SELECT id, dosya_adi, tarih, kelime_sayisi FROM belgeler ORDER BY id DESC")
    return cursor.fetchall()

def belge_sil(baglanti, belge_id):
    cursor = baglanti.cursor()
    cursor.execute("DELETE FROM belgeler WHERE id=?", (belge_id,))
    baglanti.commit()

# ─────────────────────────────────────────────────
# GÖRÜNTÜ İŞLEME
# ─────────────────────────────────────────────────

def goruntu_yukle(yol):
    return cv2.imread(yol)

def on_isleme(img):
    gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bulanik = cv2.GaussianBlur(gri, (3, 3), 0)
    _, esikli = cv2.threshold(bulanik, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return esikli

def parlaklik_kontrast(img, parlaklik=0, kontrast=1.0):
    """Parlaklık ve kontrast ayarı"""
    ayarli = cv2.convertScaleAbs(img, alpha=kontrast, beta=parlaklik)
    return ayarli

def gurultu_gider(img):
    """Median blur ile gürültü giderme"""
    return cv2.medianBlur(img, 3)

def egiklik_duzelt(img):
    """Görüntü eğikliğini tespit edip düzeltir"""
    gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    _, esikli = cv2.threshold(gri, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    koordinatlar = np.column_stack(np.where(esikli > 0))
    if len(koordinatlar) == 0:
        return img
    aci = cv2.minAreaRect(koordinatlar)[-1]
    if aci < -45:
        aci = -(90 + aci)
    else:
        aci = -aci
    (y, x) = gri.shape[:2]
    merkez = (x // 2, y // 2)
    M = cv2.getRotationMatrix2D(merkez, aci, 1.0)
    duzeltilmis = cv2.warpAffine(img, M, (x, y), flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)
    return duzeltilmis

def kenar_tespit(img):
    """Canny kenar tespiti"""
    gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    return cv2.Canny(gri, 50, 150)

def metin_bloklari_bul(img):
    gri = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, esikli = cv2.threshold(gri, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
    genisletilmis = cv2.dilate(esikli, kernel, iterations=3)
    konturlar, _ = cv2.findContours(genisletilmis, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bloklar = []
    for k in konturlar:
        x, y, w, h = cv2.boundingRect(k)
        if w > 50 and h > 10:
            bloklar.append((x, y, w, h))
    return bloklar

def ocr_uygula(img, dil="tur+eng"):
    islenmis = on_isleme(img)
    pil_img = Image.fromarray(islenmis)
    config = "--psm 6 --oem 3"
    metin = pytesseract.image_to_string(pil_img, lang=dil, config=config)
    veri = pytesseract.image_to_data(pil_img, lang=dil, config=config,
                                      output_type=pytesseract.Output.DICT)
    kelimeler = [(veri["left"][i], veri["top"][i], veri["width"][i], veri["height"][i])
                 for i, k in enumerate(veri["text"])
                 if k.strip() and int(veri["conf"][i]) > 40]
    return metin.strip(), kelimeler

# ─────────────────────────────────────────────────
# YARDIMCI: numpy → Tkinter görüntüsü
# ─────────────────────────────────────────────────

def numpy_to_tk(img, max_en=500, max_boy=400):
    if len(img.shape) == 2:
        pil = Image.fromarray(img)
    else:
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pil.thumbnail((max_en, max_boy), Image.LANCZOS)
    return ImageTk.PhotoImage(pil)

# ─────────────────────────────────────────────────
# ANA UYGULAMA
# ─────────────────────────────────────────────────

class OCRUygulama:
    # Renk paleti
    BG       = "#0f1117"
    PANEL    = "#1a1d27"
    KART     = "#21253a"
    VURGU    = "#4f8ef7"
    VURGU2   = "#a78bfa"
    YESIL    = "#34d399"
    SARI     = "#fbbf24"
    METIN    = "#e2e8f0"
    SOLUK    = "#64748b"
    KENARLIK = "#2d3250"

    def __init__(self, kok):
        self.kok = kok
        self.kok.title("Belge OCR ve Layout Analiz Sistemi")
        self.kok.geometry("1280x800")
        self.kok.minsize(1100, 700)
        self.kok.configure(bg=self.BG)

        self.db = veritabani_baslat()
        self.aktif_img = None
        self.islenmis_img = None

        self._stil_ayarla()
        self._arayuz_olustur()

    # ── STİL ────────────────────────────────────

    def _stil_ayarla(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=self.BG, foreground=self.METIN,
                     fieldbackground=self.KART, font=("Segoe UI", 10))

        # Notebook
        s.configure("TNotebook", background=self.BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=self.PANEL, foreground=self.SOLUK,
                     padding=[18, 8], font=("Segoe UI", 10))
        s.map("TNotebook.Tab",
              background=[("selected", self.KART)],
              foreground=[("selected", self.VURGU)])

        # Butonlar
        s.configure("Ana.TButton", background=self.VURGU, foreground="#ffffff",
                     padding=[14, 8], font=("Segoe UI", 10, "bold"), borderwidth=0)
        s.map("Ana.TButton", background=[("active", "#3b7de8")])

        s.configure("Ikincil.TButton", background=self.KART, foreground=self.METIN,
                     padding=[10, 6], font=("Segoe UI", 9), borderwidth=0)
        s.map("Ikincil.TButton", background=[("active", "#2d3250")])

        s.configure("Tehlike.TButton", background="#dc2626", foreground="#ffffff",
                     padding=[10, 6], font=("Segoe UI", 9, "bold"), borderwidth=0)
        s.map("Tehlike.TButton", background=[("active", "#b91c1c")])

        # Treeview
        s.configure("Treeview", background=self.KART, foreground=self.METIN,
                     fieldbackground=self.KART, rowheight=32,
                     font=("Segoe UI", 10), borderwidth=0)
        s.configure("Treeview.Heading", background=self.PANEL, foreground=self.VURGU,
                     font=("Segoe UI", 10, "bold"), relief="flat")
        s.map("Treeview", background=[("selected", self.VURGU)],
              foreground=[("selected", "#ffffff")])

        # Scrollbar
        s.configure("TScrollbar", background=self.PANEL, troughcolor=self.BG,
                     borderwidth=0, arrowsize=12)

    # ── YARDIMCI WİDGETLER ──────────────────────

    def _kart(self, parent, **kwargs):
        return tk.Frame(parent, bg=self.KART,
                        highlightbackground=self.KENARLIK,
                        highlightthickness=1, **kwargs)

    def _etiket(self, parent, text, buyuk=False, soluk=False, vurgu=False, **kwargs):
        renk = self.VURGU if vurgu else (self.SOLUK if soluk else self.METIN)
        font = ("Segoe UI", 13, "bold") if buyuk else ("Segoe UI", 10)
        return tk.Label(parent, text=text, bg=parent["bg"], fg=renk, font=font, **kwargs)

    def _stat_kart(self, parent, baslik, deger_var, renk, emoji):
        kart = tk.Frame(parent, bg=self.KART, highlightbackground=self.KENARLIK,
                        highlightthickness=1, padx=16, pady=10)
        tk.Label(kart, text=emoji, bg=self.KART, font=("Segoe UI", 18)).pack()
        tk.Label(kart, textvariable=deger_var, bg=self.KART, fg=renk,
                 font=("Segoe UI", 20, "bold")).pack()
        tk.Label(kart, text=baslik, bg=self.KART, fg=self.SOLUK,
                 font=("Segoe UI", 9)).pack()
        return kart

    # ── ANA ARAYÜZ ──────────────────────────────

    def _arayuz_olustur(self):
        # ─ Header ─
        header = tk.Frame(self.kok, bg=self.PANEL, height=58,
                          highlightbackground=self.KENARLIK, highlightthickness=1)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="  📄", bg=self.PANEL, fg=self.VURGU,
                 font=("Segoe UI", 18)).pack(side="left", padx=(16, 4))
        tk.Label(header, text="Belge OCR ve Layout Analiz Sistemi",
                 bg=self.PANEL, fg=self.METIN,
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(header, text="OpenCV  ·  pytesseract  ·  SQLite",
                 bg=self.PANEL, fg=self.SOLUK,
                 font=("Segoe UI", 9)).pack(side="right", padx=20)

        # ─ Notebook ─
        self.notebook = ttk.Notebook(self.kok)
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        self._tab_analiz()
        self._tab_veritabani()

        # ─ Status bar ─
        self.status_var = tk.StringVar(value="  Hazır")
        status = tk.Label(self.kok, textvariable=self.status_var,
                          bg=self.PANEL, fg=self.SOLUK,
                          font=("Segoe UI", 9), anchor="w",
                          highlightbackground=self.KENARLIK, highlightthickness=1)
        status.pack(fill="x", side="bottom")

    # ── TAB: ANALİZ ─────────────────────────────

    def _tab_analiz(self):
        tab = tk.Frame(self.notebook, bg=self.BG)
        self.notebook.add(tab, text="   🔍  Analiz   ")

        # ─ Sol sütun ─
        sol = tk.Frame(tab, bg=self.BG)
        sol.pack(side="left", fill="both", expand=True, padx=(12, 6), pady=12)

        # Görüntü önizleme kartı
        oniz_kart = self._kart(sol)
        oniz_kart.pack(fill="both", expand=True, pady=(0, 8))

        oniz_header = tk.Frame(oniz_kart, bg=self.KART)
        oniz_header.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(oniz_header, text="Görüntü Önizleme", bg=self.KART,
                 fg=self.VURGU, font=("Segoe UI", 10, "bold")).pack(side="left")

        self.goruntu_label = tk.Label(oniz_kart, bg="#12151f",
                                       text="📂\n\nGörüntü yüklemek için\naşağıdaki butona tıklayın",
                                       fg=self.SOLUK, font=("Segoe UI", 11),
                                       cursor="hand2")
        self.goruntu_label.pack(fill="both", expand=True, padx=10, pady=10)
        self.goruntu_label.bind("<Button-1>", lambda e: self.goruntu_yukle_btn())

        # Ana butonlar
        btn_kart = self._kart(sol)
        btn_kart.pack(fill="x", pady=(0, 8))

        btn_ic = tk.Frame(btn_kart, bg=self.KART)
        btn_ic.pack(padx=12, pady=10)

        ttk.Button(btn_ic, text="📂  Görüntü Yükle", style="Ana.TButton",
                   command=self.goruntu_yukle_btn).pack(side="left", padx=(0, 8))
        ttk.Button(btn_ic, text="🔍  OCR Başlat", style="Ana.TButton",
                   command=self.ocr_baslat).pack(side="left", padx=(0, 8))
        ttk.Button(btn_ic, text="💾  Kaydet", style="Ikincil.TButton",
                   command=self.kaydet).pack(side="left")

        # Görüntü iyileştirme kartı
        iy_kart = self._kart(sol)
        iy_kart.pack(fill="x")

        tk.Label(iy_kart, text="Görüntü İyileştirme  (OpenCV)",
                 bg=self.KART, fg=self.VURGU2,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 4))

        slider_frame = tk.Frame(iy_kart, bg=self.KART)
        slider_frame.pack(fill="x", padx=12, pady=(0, 4))

        # Parlaklık satırı
        satir1 = tk.Frame(slider_frame, bg=self.KART)
        satir1.pack(fill="x", pady=2)
        tk.Label(satir1, text="☀  Parlaklık", bg=self.KART, fg=self.METIN,
                 font=("Segoe UI", 9), width=13, anchor="w").pack(side="left")
        self.parlaklik = tk.IntVar(value=0)
        tk.Scale(satir1, from_=-100, to=100, orient="horizontal",
                 variable=self.parlaklik, bg=self.KART, fg=self.METIN,
                 highlightbackground=self.KART, troughcolor="#2d3250",
                 activebackground=self.VURGU, length=240, showvalue=True,
                 command=self._canli_guncelle).pack(side="left", padx=6)

        # Kontrast satırı
        satir2 = tk.Frame(slider_frame, bg=self.KART)
        satir2.pack(fill="x", pady=2)
        tk.Label(satir2, text="◑  Kontrast", bg=self.KART, fg=self.METIN,
                 font=("Segoe UI", 9), width=13, anchor="w").pack(side="left")
        self.kontrast = tk.DoubleVar(value=1.0)
        tk.Scale(satir2, from_=0.5, to=3.0, resolution=0.1, orient="horizontal",
                 variable=self.kontrast, bg=self.KART, fg=self.METIN,
                 highlightbackground=self.KART, troughcolor="#2d3250",
                 activebackground=self.VURGU, length=240, showvalue=True,
                 command=self._canli_guncelle).pack(side="left", padx=6)

        # İşlem butonları
        islem_frame = tk.Frame(iy_kart, bg=self.KART)
        islem_frame.pack(fill="x", padx=12, pady=(4, 12))

        for metin, komut in [
            ("🔧 Gürültü Gider", self.gurultu_gider_btn),
            ("📐 Eğiklik Düzelt", self.egiklik_duzelt_btn),
            ("⬜ Kenar Tespit", self.kenar_tespit_btn),
            ("↩ Sıfırla", self.sifirla),
        ]:
            ttk.Button(islem_frame, text=metin, style="Ikincil.TButton",
                       command=komut).pack(side="left", padx=(0, 6))

        # ─ Sağ sütun ─
        sag = tk.Frame(tab, bg=self.BG)
        sag.pack(side="right", fill="both", expand=True, padx=(6, 12), pady=12)

        # Stat kartları
        stat_frame = tk.Frame(sag, bg=self.BG)
        stat_frame.pack(fill="x", pady=(0, 8))

        self.v_kelime   = tk.StringVar(value="—")
        self.v_blok     = tk.StringVar(value="—")
        self.v_karakter = tk.StringVar(value="—")

        for (baslik, var, renk, emoji), yon in zip([
            ("Kelime",    self.v_kelime,   self.YESIL, "📝"),
            ("Blok",      self.v_blok,     self.VURGU, "🗂"),
            ("Karakter",  self.v_karakter, self.SARI,  "🔤"),
        ], ["left", "left", "left"]):
            k = self._stat_kart(stat_frame, baslik, var, renk, emoji)
            k.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # Çıkarılan metin kartı
        metin_kart = self._kart(sag)
        metin_kart.pack(fill="both", expand=True)

        metin_header = tk.Frame(metin_kart, bg=self.KART)
        metin_header.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(metin_header, text="Çıkarılan Metin", bg=self.KART,
                 fg=self.VURGU, font=("Segoe UI", 10, "bold")).pack(side="left")

        self.bilgi_label = tk.Label(metin_header, text="", bg=self.KART,
                                     fg=self.SOLUK, font=("Segoe UI", 9))
        self.bilgi_label.pack(side="right")

        metin_ic = tk.Frame(metin_kart, bg=self.KART)
        metin_ic.pack(fill="both", expand=True, padx=10, pady=10)

        self.metin_kutusu = tk.Text(metin_ic, bg="#12151f", fg=self.METIN,
                                     font=("Consolas", 11), wrap="word",
                                     insertbackground=self.METIN,
                                     relief="flat", padx=12, pady=10,
                                     selectbackground=self.VURGU)
        sb_metin = ttk.Scrollbar(metin_ic, command=self.metin_kutusu.yview)
        self.metin_kutusu.config(yscrollcommand=sb_metin.set)
        sb_metin.pack(side="right", fill="y")
        self.metin_kutusu.pack(fill="both", expand=True)

    # ── TAB: VERİTABANI ─────────────────────────

    def _tab_veritabani(self):
        tab = tk.Frame(self.notebook, bg=self.BG)
        self.notebook.add(tab, text="   🗄  Veritabanı   ")

        # Arama kartı
        ara_kart = self._kart(tab)
        ara_kart.pack(fill="x", padx=12, pady=(12, 6))

        ara_ic = tk.Frame(ara_kart, bg=self.KART)
        ara_ic.pack(fill="x", padx=12, pady=10)

        tk.Label(ara_ic, text="🔎", bg=self.KART, fg=self.VURGU,
                 font=("Segoe UI", 13)).pack(side="left")

        self.arama_kutusu = tk.Entry(ara_ic, bg="#12151f", fg=self.METIN,
                                      font=("Segoe UI", 11),
                                      insertbackground=self.METIN,
                                      relief="flat", width=40)
        self.arama_kutusu.pack(side="left", padx=8, ipady=5)
        self.arama_kutusu.bind("<Return>", lambda e: self.ara())

        ttk.Button(ara_ic, text="Ara", style="Ana.TButton",
                   command=self.ara).pack(side="left", padx=(0, 6))
        ttk.Button(ara_ic, text="Tümünü Göster", style="Ikincil.TButton",
                   command=self.tum_belgeleri_goster).pack(side="left")
        ttk.Button(ara_ic, text="🗑  Seçili Sil", style="Tehlike.TButton",
                   command=self.secili_sil).pack(side="right")

        # Tablo kartı
        tablo_kart = self._kart(tab)
        tablo_kart.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        tk.Label(tablo_kart, text="Kayıtlı Belgeler", bg=self.KART,
                 fg=self.VURGU, font=("Segoe UI", 10, "bold")).pack(
                 anchor="w", padx=12, pady=(10, 6))

        tablo_ic = tk.Frame(tablo_kart, bg=self.KART)
        tablo_ic.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        kolonlar = ("id", "dosya_adi", "tarih", "kelime_sayisi")
        self.tablo = ttk.Treeview(tablo_ic, columns=kolonlar, show="headings")

        self.tablo.heading("id",            text="#")
        self.tablo.heading("dosya_adi",     text="Dosya Adı")
        self.tablo.heading("tarih",         text="Tarih")
        self.tablo.heading("kelime_sayisi", text="Kelime")

        self.tablo.column("id",            width=45,  anchor="center")
        self.tablo.column("dosya_adi",     width=400)
        self.tablo.column("tarih",         width=160, anchor="center")
        self.tablo.column("kelime_sayisi", width=90,  anchor="center")

        sb_tablo = ttk.Scrollbar(tablo_ic, orient="vertical", command=self.tablo.yview)
        self.tablo.configure(yscrollcommand=sb_tablo.set)
        sb_tablo.pack(side="right", fill="y")
        self.tablo.pack(fill="both", expand=True)
        self.tablo.tag_configure("tek",   background=self.KART)
        self.tablo.tag_configure("cift",  background="#1e2235")

        # Seçili metin kartı
        sec_kart = self._kart(tab)
        sec_kart.pack(fill="x", padx=12, pady=(0, 12))

        tk.Label(sec_kart, text="Seçili Belgenin Metni", bg=self.KART,
                 fg=self.VURGU, font=("Segoe UI", 10, "bold")).pack(
                 anchor="w", padx=12, pady=(10, 4))

        self.secili_metin = tk.Text(sec_kart, bg="#12151f", fg=self.METIN,
                                     font=("Consolas", 10), height=5, wrap="word",
                                     relief="flat", padx=12, pady=8,
                                     selectbackground=self.VURGU)
        self.secili_metin.pack(fill="x", padx=10, pady=(0, 10))

        self.tablo.bind("<<TreeviewSelect>>", self._tablo_sec)
        self.tum_belgeleri_goster()

    # ── BUTON FONKSİYONLARI ─────────────────────

    def goruntu_yukle_btn(self):
        yol = filedialog.askopenfilename(
            title="Görüntü Seç",
            filetypes=[("Görüntü Dosyaları", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("Tümü", "*.*")]
        )
        if not yol:
            return
        self.aktif_yol = yol
        self.aktif_img = goruntu_yukle(yol)
        self.islenmis_img = self.aktif_img.copy()
        self.parlaklik.set(0)
        self.kontrast.set(1.0)
        self._goruntu_goster(self.islenmis_img)
        self.metin_kutusu.delete("1.0", "end")
        self.bilgi_label.config(text="")
        self.v_kelime.set("—")
        self.v_blok.set("—")
        self.v_karakter.set("—")
        self.status_var.set(f"  📂  Yüklendi: {os.path.basename(yol)}")

    def _goruntu_goster(self, img):
        tk_img = numpy_to_tk(img)
        self.goruntu_label.config(image=tk_img, text="")
        self.goruntu_label.image = tk_img

    def _canli_guncelle(self, _=None):
        if self.aktif_img is None:
            return
        ayarli = parlaklik_kontrast(self.aktif_img,
                                     self.parlaklik.get(),
                                     self.kontrast.get())
        self.islenmis_img = ayarli
        self._goruntu_goster(ayarli)

    def gurultu_gider_btn(self):
        if self.islenmis_img is None:
            messagebox.showwarning("Uyarı", "Önce bir görüntü yükleyin!")
            return
        self.islenmis_img = gurultu_gider(self.islenmis_img)
        self._goruntu_goster(self.islenmis_img)

    def egiklik_duzelt_btn(self):
        if self.islenmis_img is None:
            messagebox.showwarning("Uyarı", "Önce bir görüntü yükleyin!")
            return
        self.islenmis_img = egiklik_duzelt(self.islenmis_img)
        self._goruntu_goster(self.islenmis_img)

    def kenar_tespit_btn(self):
        if self.islenmis_img is None:
            messagebox.showwarning("Uyarı", "Önce bir görüntü yükleyin!")
            return
        kenar = kenar_tespit(self.islenmis_img)
        self._goruntu_goster(kenar)

    def sifirla(self):
        if self.aktif_img is None:
            return
        self.islenmis_img = self.aktif_img.copy()
        self.parlaklik.set(0)
        self.kontrast.set(1.0)
        self._goruntu_goster(self.islenmis_img)

    def ocr_baslat(self):
        if self.islenmis_img is None:
            messagebox.showwarning("Uyarı", "Önce bir görüntü yükleyin!")
            return

        self.bilgi_label.config(text="⏳ İşleniyor...")
        self.status_var.set("  ⏳  OCR çalışıyor...")
        self.kok.update()

        metin, kelimeler = ocr_uygula(self.islenmis_img)
        bloklar = metin_bloklari_bul(self.islenmis_img)

        self.son_metin = metin
        self.son_kelime_sayisi = len(kelimeler)
        self.son_blok_sayisi = len(bloklar)

        # Kelimeleri görüntü üzerine çiz
        cikti = self.islenmis_img.copy()
        for (x, y, w, h) in kelimeler:
            cv2.rectangle(cikti, (x, y), (x+w, y+h), (0, 200, 0), 1)
        for (x, y, w, h) in bloklar:
            cv2.rectangle(cikti, (x, y), (x+w, y+h), (255, 100, 0), 2)
        self._goruntu_goster(cikti)

        # Metni göster
        self.metin_kutusu.delete("1.0", "end")
        self.metin_kutusu.insert("1.0", metin if metin else "(Metin bulunamadı)")

        self.v_kelime.set(str(len(kelimeler)))
        self.v_blok.set(str(len(bloklar)))
        self.v_karakter.set(str(len(metin)))
        self.bilgi_label.config(text="✅ Tamamlandı")
        self.status_var.set(f"  ✅  OCR tamamlandı — {os.path.basename(self.aktif_yol)}")

    def kaydet(self):
        if not hasattr(self, "son_metin"):
            messagebox.showwarning("Uyarı", "Önce OCR çalıştırın!")
            return
        belge_kaydet(self.db, os.path.basename(self.aktif_yol),
                     self.son_metin, self.son_kelime_sayisi, self.son_blok_sayisi)
        messagebox.showinfo("Başarılı", "Belge veritabanına kaydedildi!")
        self.tum_belgeleri_goster()
        self.notebook.select(1)

    def ara(self):
        arama = self.arama_kutusu.get().strip()
        if not arama:
            self.tum_belgeleri_goster()
            return
        sonuclar = belge_ara(self.db, arama)
        self._tablo_doldur(sonuclar)

    def tum_belgeleri_goster(self):
        sonuclar = tum_belgeler(self.db)
        self._tablo_doldur(sonuclar)

    def _tablo_doldur(self, veri):
        for satir in self.tablo.get_children():
            self.tablo.delete(satir)
        for i, satir in enumerate(veri):
            tag = "tek" if i % 2 == 0 else "cift"
            self.tablo.insert("", "end", values=satir, tags=(tag,))

    def _tablo_sec(self, _):
        secili = self.tablo.selection()
        if not secili:
            return
        belge_id = self.tablo.item(secili[0])["values"][0]
        cursor = self.db.cursor()
        cursor.execute("SELECT metin FROM belgeler WHERE id=?", (belge_id,))
        sonuc = cursor.fetchone()
        if sonuc:
            self.secili_metin.delete("1.0", "end")
            self.secili_metin.insert("1.0", sonuc[0])

    def secili_sil(self):
        secili = self.tablo.selection()
        if not secili:
            messagebox.showwarning("Uyarı", "Silinecek bir kayıt seçin!")
            return
        belge_id = self.tablo.item(secili[0])["values"][0]
        if messagebox.askyesno("Onay", "Bu kaydı silmek istediğinize emin misiniz?"):
            belge_sil(self.db, belge_id)
            self.tum_belgeleri_goster()

# ─────────────────────────────────────────────────
# BAŞLAT
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    kok = tk.Tk()
    uygulama = OCRUygulama(kok)
    kok.mainloop()
