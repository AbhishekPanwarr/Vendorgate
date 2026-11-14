"""Concrete mock verifiers (Phase 2 hand fixtures)."""

from backend.app.adapters.mocks.mockbase import MockVerifier


class IrsMock(MockVerifier):
    name = "irs"
    fixture_file = "irs.jsonl"
    key_field = "tax_id"


class GstMock(MockVerifier):
    name = "gst"
    fixture_file = "gst.jsonl"
    key_field = "gstin"


class ViesMock(MockVerifier):
    name = "vies"
    fixture_file = "vies.jsonl"
    key_field = "vat_id"


class RegistryMock(MockVerifier):
    name = "registry"
    fixture_file = "registry.jsonl"
    key_field = "name_key"


class BankMock(MockVerifier):
    name = "bank"
    fixture_file = "bank.jsonl"
    key_field = "acct_key"
