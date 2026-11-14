from typing import Any

from pydantic import BaseModel
from pydantic import Field

from backend.app.domain.enums import DocType
from backend.app.domain.enums import SubmissionType


class Money(BaseModel):
    amount: float
    currency: str


class Requester(BaseModel):
    name: str
    email: str
    department: str
    business_justification: str
    expected_annual_spend: Money
    category: str
    data_access: bool = False
    one_time: bool = False


class Address(BaseModel):
    line1: str
    line2: str | None = None
    city: str
    region: str
    postal_code: str
    country: str


class Contact(BaseModel):
    name: str
    email: str
    phone: str


class Owner(BaseModel):
    name: str
    ownership_pct: float
    role: str


class Company(BaseModel):
    legal_name: str
    trading_name: str | None = None
    entity_type: str
    country: str
    incorporation_date: str
    registered_address: Address
    remit_to_address: Address | None = None
    website: str | None = None
    primary_contact: Contact
    ap_contact: Contact
    owners: list[Owner] = Field(default_factory=list)


class Tax(BaseModel):
    country: str
    tax_id_type: str
    tax_id: str
    secondary_ids: dict[str, str] = Field(default_factory=dict)
    tax_classification: str
    form_type: str
    vat_id: str | None = None


class Bank(BaseModel):
    country: str
    currency: str
    account_holder_name: str
    bank_name: str
    account_number: str
    routing_number: str | None = None
    iban: str | None = None
    swift_bic: str | None = None
    ifsc: str | None = None
    sort_code: str | None = None


class DocumentRef(BaseModel):
    doc_id: str
    doc_type: DocType
    filename: str
    sha256: str


class Declarations(BaseModel):
    aliases: list[str] = Field(default_factory=list)
    bank_change_justification: str | None = None
    remit_address_justification: str | None = None


class VendorSubmission(BaseModel):
    schema_version: str = "1.0"
    submission_type: SubmissionType = SubmissionType.NEW_VENDOR
    existing_vendor_id: str | None = None
    requester: Requester
    company: Company
    tax: Tax
    bank: Bank
    documents: list[DocumentRef] = Field(default_factory=list)
    declarations: Declarations = Field(default_factory=Declarations)
    submitter_meta: dict[str, Any] = Field(default_factory=dict)
