"""Upload safety (C-DOC-00): magic bytes, size, pages, encryption, active content."""

MAX_MB = 10
MAX_PAGES = 20

_PDF_MAGIC = b"%PDF"
_PNG_MAGIC = b"\x89PNG"
_JPG_MAGIC = b"\xff\xd8\xff"


def sniff_mime(data: bytes) -> str | None:
    if data.startswith(_PDF_MAGIC):
        return "pdf"
    if data.startswith(_PNG_MAGIC):
        return "png"
    if data.startswith(_JPG_MAGIC):
        return "jpg"
    return None


def check_upload(filename: str, data: bytes) -> tuple[bool, str]:
    if len(data) > MAX_MB * 1024 * 1024:
        return False, "UPLOAD_TOO_LARGE"
    mime = sniff_mime(data)
    if mime is None:
        return False, "UPLOAD_BAD_MIME"
    if mime == "pdf":
        if b"/Encrypt" in data[:4096]:
            return False, "UPLOAD_ENCRYPTED"
        if b"/JS" in data or b"/JavaScript" in data or b"/Launch" in data:
            return False, "UPLOAD_ACTIVE_CONTENT"
        count = data.count(b"/Type/Page") - data.count(b"/Type/Pages")
        if count > MAX_PAGES:
            return False, "UPLOAD_TOO_MANY_PAGES"
    return True, ""
