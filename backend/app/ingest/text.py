"""Text-layer extraction + scanned fallback (OCR)."""

import io

MIN_CHARS_PER_PAGE = 40


def extract_text_layer(data: bytes) -> tuple[list[str], bool]:
    """Returns (pages, has_text_layer). Images always count as no text layer."""
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    if not pages:
        return [], False
    mean_chars = sum(len(p) for p in pages) / len(pages)
    return pages, mean_chars >= MIN_CHARS_PER_PAGE


def ocr_pdf_bytes(data: bytes, dpi: int = 300) -> tuple[list[str], float]:
    import pdfplumber
    from PIL import Image
    import pytesseract

    pages: list[str] = []
    confs: list[float] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            img = page.to_image(resolution=dpi).original
            if not isinstance(img, Image.Image):
                img = Image.fromarray(img)
            text = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            words = [w for w, c in zip(text["text"], text["conf"], strict=True) if w.strip()]
            pages.append(" ".join(words))
            valid = [float(c) for c in text["conf"] if float(c) >= 0]
            confs.extend(valid)
    mean_conf = sum(confs) / len(confs) if confs else 0.0
    return pages, mean_conf
