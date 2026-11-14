"""S1 document ingestion: safety -> text/OCR -> injection -> classify -> extract -> freshness."""

from typing import Any

from backend.app.domain.enums import Source
from backend.app.domain.models import Claim
from backend.app.ingest import classifier
from backend.app.ingest import extract_regex
from backend.app.ingest import injection
from backend.app.ingest import upload
from backend.app.ingest.text import extract_text_layer
from backend.app.ingest.text import ocr_pdf_bytes

_doc_counter = [0]


def _claim(
    doc_id: str,
    field: str,
    value: Any,
    quote: str | None,
    page: int | None,
    conf: float,
    text_layer: bool,
) -> Claim:
    _doc_counter[0] += 1
    val = None if value is None else str(value)
    return Claim(
        id=f"clm_doc_{_doc_counter[0]}",
        path=f"doc:{doc_id}.{field}",
        raw=val,
        value=val,
        source=Source.DOC,
        doc_id=doc_id,
        page=page,
        quote=quote,
        confidence=conf,
    )


def ingest_document(
    doc_id: str, declared: str, filename: str, data: bytes, today: Any
) -> dict[str, Any]:
    """Returns {claims, text_pages, text_layer, detected_type, injection_hits,
    freshness: {...}, upload_ok, upload_reason}."""
    out: dict[str, Any] = {"doc_id": doc_id, "declared": declared, "claims": [], "freshness": {}}
    ok, reason = upload.check_upload(filename, data)
    out["upload_ok"] = ok
    out["upload_reason"] = reason
    if not ok:
        return out
    pages, layered = extract_text_layer(data)
    out["text_layer"] = layered
    if not layered:
        try:
            pages, conf = ocr_pdf_bytes(data)
            out["ocr_conf"] = conf
        except Exception:
            pages = []
    pages = [p for p in pages if p.strip()]
    out["text_pages"] = pages
    text = "\n".join(pages)
    out["injection_hits"] = injection.scan_document(data, text)
    dtype, score, confident = classifier.classify(text)
    out["detected_type"] = dtype
    out["detect_score"] = score
    out["detect_confident"] = confident
    for field, hits in extract_regex.extract(text).items():
        for val, quote in hits[:3]:
            out["claims"].append(_claim(doc_id, field.lower(), val, quote, 1, 0.9, layered))
    return out
