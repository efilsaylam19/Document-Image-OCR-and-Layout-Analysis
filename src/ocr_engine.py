"""
Document Image OCR and Layout Analysis
Tools: OpenCV, pytesseract
"""

import cv2
import pytesseract
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import os

# Tesseract executable path (required on Windows)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ─────────────────────────────────────────────────
# 1. IMAGE LOADING & PRE-PROCESSING
# ─────────────────────────────────────────────────

def load_image(file_path: str) -> np.ndarray:
    """Load an image from disk and return it in BGR format."""
    img = cv2.imread(file_path)
    if img is None:
        raise FileNotFoundError(f"Image not found: {file_path}")
    return img


def preprocess(img: np.ndarray) -> np.ndarray:
    """
    Basic pre-processing steps to improve OCR accuracy:
    - Convert to grayscale
    - Reduce noise with Gaussian blur
    - Apply Otsu's thresholding
    """
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Reduce noise with Gaussian blur
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # Otsu's thresholding: white background, black text
    _, thresholded = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return thresholded


# ─────────────────────────────────────────────────
# 2. TEXT EXTRACTION (OCR)
# ─────────────────────────────────────────────────

def extract_text(preprocessed_img: np.ndarray, lang: str = "tur+eng") -> str:
    """
    Extract text from a pre-processed image.

    lang options:
      "tur"     → Turkish only
      "eng"     → English only
      "tur+eng" → Turkish and English together
    """
    pil_img = Image.fromarray(preprocessed_img)
    # psm 6: treat the image as a single uniform block of text → cleaner output
    config = "--psm 6 --oem 3"
    text = pytesseract.image_to_string(pil_img, lang=lang, config=config)
    return text.strip()


def get_word_positions(preprocessed_img: np.ndarray, lang: str = "tur+eng") -> list:
    """
    Return the bounding box coordinates of each word detected in the image.
    """
    pil_img = Image.fromarray(preprocessed_img)
    data = pytesseract.image_to_data(pil_img, lang=lang, output_type=pytesseract.Output.DICT)

    words = []
    for i, word in enumerate(data["text"]):
        if word.strip() and int(data["conf"][i]) > 40:  # confidence score > 40
            words.append({
                "text":   word,
                "x":      data["left"][i],
                "y":      data["top"][i],
                "width":  data["width"][i],
                "height": data["height"][i],
                "conf":   data["conf"][i],
            })
    return words


# ─────────────────────────────────────────────────
# 3. LAYOUT ANALYSIS
# ─────────────────────────────────────────────────

def find_text_blocks(img: np.ndarray) -> list:
    """
    Detect text blocks (paragraphs, headings, columns) using
    OpenCV morphological operations.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresholded = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Dilate horizontally and vertically to merge text lines into blocks
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
    dilated = cv2.dilate(thresholded, kernel, iterations=3)

    # Find connected regions
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    blocks = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Filter out small noise regions
        if w > 50 and h > 10:
            blocks.append({"x": x, "y": y, "width": w, "height": h})

    # Sort top-to-bottom
    blocks.sort(key=lambda b: b["y"])
    return blocks


def find_lines(img: np.ndarray) -> dict:
    """
    Detect horizontal and vertical lines using the Hough Line Transform.
    Useful for tables, forms, and separator lines.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                             minLineLength=100, maxLineGap=10)

    horizontal, vertical = [], []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
            if angle < 10:        # horizontal line
                horizontal.append((x1, y1, x2, y2))
            elif angle > 80:      # vertical line
                vertical.append((x1, y1, x2, y2))

    return {"horizontal": horizontal, "vertical": vertical}


# ─────────────────────────────────────────────────
# 4. VISUAL OUTPUT
# ─────────────────────────────────────────────────

def show_results(original_img: np.ndarray,
                 preprocessed_img: np.ndarray,
                 blocks: list,
                 words: list) -> np.ndarray:
    """
    Draw detected blocks and words on the original image and display results side by side.
    """
    output = original_img.copy()

    # Draw text blocks with a blue rectangle
    for block in blocks:
        x, y, w, h = block["x"], block["y"], block["width"], block["height"]
        cv2.rectangle(output, (x, y), (x + w, y + h), (255, 100, 0), 2)

    # Draw individual words with a green rectangle
    for word in words:
        x, y, w, h = word["x"], word["y"], word["width"], word["height"]
        cv2.rectangle(output, (x, y), (x + w, y + h), (0, 200, 0), 1)

    # Display side by side using Matplotlib
    fig, axes = plt.subplots(1, 3, figsize=(18, 7))
    axes[0].imshow(cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB))
    axes[0].set_title("Original Image")
    axes[0].axis("off")

    axes[1].imshow(preprocessed_img, cmap="gray")
    axes[1].set_title("Pre-processed (for OCR)")
    axes[1].axis("off")

    axes[2].imshow(cv2.cvtColor(output, cv2.COLOR_BGR2RGB))
    axes[2].set_title("Layout + Word Detection")
    axes[2].axis("off")

    plt.tight_layout()
    plt.savefig("analysis_result.png", dpi=150, bbox_inches="tight")
    plt.show()

    return output


# ─────────────────────────────────────────────────
# 5. MAIN PIPELINE
# ─────────────────────────────────────────────────

def analyze_document(file_path: str, lang: str = "tur+eng") -> dict:
    """
    Run the full analysis pipeline with a single function call.
    Returns: text, words, blocks, lines
    """
    print(f"[1/5] Loading image: {file_path}")
    img = load_image(file_path)

    print("[2/5] Applying pre-processing...")
    preprocessed = preprocess(img)

    print("[3/5] Extracting text (OCR)...")
    text = extract_text(preprocessed, lang=lang)
    words = get_word_positions(preprocessed, lang=lang)

    print("[4/5] Analyzing layout...")
    blocks = find_text_blocks(img)
    lines  = find_lines(img)

    print("[5/5] Displaying results...")
    show_results(img, preprocessed, blocks, words)

    result = {
        "text":              text,
        "word_count":        len(words),
        "block_count":       len(blocks),
        "horizontal_lines":  len(lines["horizontal"]),
        "vertical_lines":    len(lines["vertical"]),
        "words":             words,
        "blocks":            blocks,
    }

    print("\n" + "=" * 50)
    print("ANALYSIS COMPLETE")
    print("=" * 50)
    print(f"Words found    : {result['word_count']}")
    print(f"Text blocks    : {result['block_count']}")
    print(f"Horizontal lines: {result['horizontal_lines']}")
    print(f"Vertical lines  : {result['vertical_lines']}")
    print("\n--- EXTRACTED TEXT ---")
    print(result["text"] if result["text"] else "(no text found)")

    return result


# ─────────────────────────────────────────────────
# USAGE EXAMPLE
# ─────────────────────────────────────────────────

if __name__ == "__main__":
    # Set the path to your image file here:
    IMAGE_PATH = "assets/sample_document.png"

    # Language: "tur" / "eng" / "tur+eng"
    LANG = "tur+eng"

    if not os.path.exists(IMAGE_PATH):
        print(f"ERROR: '{IMAGE_PATH}' not found.")
        print("Please update IMAGE_PATH with the path to your image file.")
    else:
        result = analyze_document(IMAGE_PATH, lang=LANG)
