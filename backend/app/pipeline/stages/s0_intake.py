"""S0: intake & normalization — submission fields become claims."""

import itertools

from backend.app.domain.enums import Source
from backend.app.domain.models import Claim
from backend.app.domain.submission import VendorSubmission
from backend.app.matching.normalize import canon_address
from backend.app.matching.normalize import canon_domain
from backend.app.matching.normalize import canon_id
from backend.app.matching.normalize import canon_money
from backend.app.matching.normalize import canon_phone
from backend.app.matching.normalize import canon_text

_counter = itertools.count(1)


def _claim(path: str, raw: object, value: object, source: Source = Source.FORM) -> Claim:
    raw_s = None if raw is None else str(raw)
    val_s = None if value is None else str(value)
    return Claim(id=f"clm_{next(_counter)}", path=path, raw=raw_s, value=val_s, source=source)


def build_claims(sub: VendorSubmission) -> list[Claim]:
    claims: list[Claim] = []
    c = sub.company
    legal, _ = canon_text(c.legal_name)
    claims.append(_claim("company.legal_name", c.legal_name, legal))
    if c.trading_name:
        trading, _ = canon_text(c.trading_name)
        claims.append(_claim("company.trading_name", c.trading_name, trading))
    claims.append(_claim("company.entity_type", c.entity_type, canon_id(c.entity_type)))
    claims.append(_claim("company.country", c.country, (c.country or "").upper()))
    claims.append(_claim("company.incorporation_date", c.incorporation_date, c.incorporation_date))
    addr = c.registered_address
    claims.append(
        _claim(
            "company.registered_address", addr.model_dump_json(), canon_address(addr.model_dump())
        )
    )
    claims.append(
        _claim("company.registered_address.country", addr.country, (addr.country or "").upper())
    )
    claims.append(
        _claim("company.registered_address.region", addr.region, (addr.region or "").upper())
    )
    if c.remit_to_address:
        claims.append(
            _claim(
                "company.remit_to_address",
                c.remit_to_address.model_dump_json(),
                canon_address(c.remit_to_address.model_dump()),
            )
        )
    if c.website:
        claims.append(_claim("company.website", c.website, canon_domain(c.website)))
    for role in ("primary_contact", "ap_contact"):
        contact = getattr(c, role)
        claims.append(_claim(f"company.{role}.email", contact.email, contact.email.strip().lower()))
        claims.append(
            _claim(
                f"company.{role}.phone",
                contact.phone,
                canon_phone(contact.phone, c.country) or contact.phone,
            )
        )
    for i, o in enumerate(c.owners):
        n, _ = canon_text(o.name)
        claims.append(_claim(f"company.owners.{i}.name", o.name, n))

    t = sub.tax
    claims.append(_claim("tax.country", t.country, (t.country or "").upper()))
    claims.append(_claim("tax.tax_id_type", t.tax_id_type, (t.tax_id_type or "").upper()))
    claims.append(_claim("tax.tax_id", t.tax_id, canon_id(t.tax_id)))
    for k, v in (t.secondary_ids or {}).items():
        claims.append(_claim(f"tax.secondary_ids.{k}", v, canon_id(v)))
    claims.append(
        _claim("tax.tax_classification", t.tax_classification, canon_id(t.tax_classification))
    )
    claims.append(_claim("tax.form_type", t.form_type, (t.form_type or "").upper()))
    if t.vat_id:
        claims.append(_claim("tax.vat_id", t.vat_id, canon_id(t.vat_id)))

    b = sub.bank
    claims.append(_claim("bank.country", b.country, (b.country or "").upper()))
    claims.append(_claim("bank.currency", b.currency, (b.currency or "").upper()))
    holder, _ = canon_text(b.account_holder_name)
    claims.append(_claim("bank.account_holder_name", b.account_holder_name, holder))
    bank_name, _ = canon_text(b.bank_name)
    claims.append(_claim("bank.bank_name", b.bank_name, bank_name))
    claims.append(
        _claim(
            "bank.account_number",
            b.account_number,
            "".join(ch for ch in (b.account_number or "") if ch.isdigit()),
        )
    )
    for f in ("routing_number", "iban", "swift_bic", "ifsc", "sort_code"):
        v = getattr(b, f)
        if v:
            claims.append(_claim(f"bank.{f}", v, canon_id(v)))

    r = sub.requester
    claims.append(_claim("requester.category", r.category, (r.category or "").upper()))
    claims.append(
        _claim(
            "requester.expected_annual_spend_usd",
            r.expected_annual_spend.amount,
            canon_money(r.expected_annual_spend.amount, r.expected_annual_spend.currency),
        )
    )
    claims.append(_claim("requester.data_access", r.data_access, str(bool(r.data_access))))
    claims.append(_claim("requester.one_time", r.one_time, str(bool(r.one_time))))
    for i, d in enumerate(sub.documents):
        claims.append(_claim(f"documents.{i}.doc_type", d.doc_type.value, d.doc_type.value))
    return claims
