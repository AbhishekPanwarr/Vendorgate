"""Doc renderer: values -> labeled PDF + ground-truth L1 extraction entry.

Ground truth comes from the authored values (datagen is the source of truth
for synthetic docs); quotes are the rendered label lines verbatim.
"""

import hashlib
import io

FOOTER = "SYNTHETIC — NOT AN OFFICIAL FORM"

# (label, field) per doc type; labels match classifier anchors.
LAYOUTS: dict[str, list[tuple[str, str]]] = {
    "W9": [("Request for Taxpayer Identification Number", None),
           ("Form W-9 (Rev. March 2024)", "form_revision"),
           ("Name of business", "business_name"),
           ("Taxpayer Identification Number", "tin"),
           ("Tax classification", "tax_classification"),
           ("Signature", "signature_present"),
           ("Date", "signature_date")],
    "GST_CERT": [("Goods and Services Tax Registration Certificate", None),
                 ("Legal Name", "legal_name"), ("Trade Name", "trade_name"),
                 ("GSTIN", "gstin"), ("Registration Date", "registration_date"),
                 ("Status", "status")],
    "VAT_CERT": [("VAT registration certificate", None),
                 ("Legal Name", "legal_name"),
                 ("VAT identification number", "vat_id"),
                 ("Effective Date", "effective_date")],
    "INCORP_CERT": [("Certificate of Incorporation", None),
                    ("Legal Name", "legal_name"),
                    ("Registration No", "registration_no"),
                    ("Incorporation Date", "incorporation_date"),
                    ("Status", "status")],
    "BANK_LETTER": [("Bank Letter", None),
                    ("this is to certify that", None),
                    ("Account Holder", "account_holder"),
                    ("Account Number", "account_number"),
                    ("Routing", "routing"),
                    ("Letter Date", "letter_date"),
                    ("Signatory", "signatory")],
    "COI": [("Certificate of Liability Insurance", None),
            ("Named Insured", "insured_name"), ("Insurer", "insurer"),
            ("Policy No", "policy_no"), ("Expiry Date", "expiry_date"),
            ("Certificate Holder", "certificate_holder")],
    "W8BEN": [("Certificate of Foreign Status", None),
              ("Form W-8BEN", None),
              ("Name", "name"), ("Country of Residence", "country"),
              ("Signature", "signature_present"), ("Date", "signature_date")],
}


def render_pdf(doc_type: str, values: dict[str, str | None]) -> bytes:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    # uncompressed: avoids incidental byte patterns (e.g. /JS) tripping the
    # upload active-content check; keeps text extraction byte-stable
    c = canvas.Canvas(buf, pagesize=letter, pageCompression=0)
    c.setFont("Helvetica", 11)
    y = 750
    for label, field in LAYOUTS[doc_type]:
        line = label if field is None else f"{label}: {values.get(field) or ''}"
        c.drawString(60, y, line)
        y -= 18
    c.setFont("Helvetica", 8)
    c.drawString(60, 40, FOOTER)
    c.save()
    return buf.getvalue()


def degrade_pdf(pdf: bytes, seed: int = 0) -> bytes:
    """Rasterize, add noise, return image-only PDF (no text layer)."""
    import io as _io
    import random

    import pdfplumber
    from PIL import Image, ImageDraw
    import pytesseract  # noqa: F401 (ensures OCR available downstream)

    rng = random.Random(seed)
    pages = []
    with pdfplumber.open(_io.BytesIO(pdf)) as doc:
        for page in doc.pages:
            img = page.to_image(resolution=150).original
            if not isinstance(img, Image.Image):
                img = Image.fromarray(img)
            px = img.load()
            w, h = img.size
            for _ in range(w * h // 200):
                x, y = rng.randrange(w), rng.randrange(h)
                v = rng.randint(200, 255)
                px[x, y] = (v, v, v)
            pages.append(img.convert("RGB"))
    out = _io.BytesIO()
    pages[0].save(out, format="PDF", save_all=True, append_images=pages[1:])
    return out.getvalue()


def l1_entry(doc_type: str, values: dict[str, str | None]) -> dict:
    entry = {}
    for label, field in LAYOUTS[doc_type]:
        if field is None:
            continue
        v = values.get(field)
        if v:
            quote = f"{label}: {v}"
            entry[field] = {"value": v, "quote": quote, "page": 1, "confidence": 1.0}
        else:
            entry[field] = {"value": None, "quote": None, "page": None, "confidence": 0.0}
    entry["_tokens_used"] = 0
    entry["_datagen"] = True
    return entry


def doc_sha(pdf: bytes) -> str:
    return hashlib.sha256(pdf).hexdigest()
