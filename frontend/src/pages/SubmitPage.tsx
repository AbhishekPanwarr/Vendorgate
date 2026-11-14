import React, { useState } from 'react';
import { PageHeader } from '../components/layout/PageHeader';
import { Card } from '../components/primitives/Card';
import { Input } from '../components/primitives/Input';
import { Select } from '../components/primitives/Select';
import { Button } from '../components/primitives/Button';
import { Checkbox } from '../components/primitives/Checkbox';
import { Badge } from '../components/primitives/Badge';
import { Drawer } from '../components/primitives/Drawer';
import { ProgressBar } from '../components/primitives/ProgressBar';
import { useApp } from '../context/AppContext';
import { api } from '../api';
import { validateTaxId, maskAccountNumber } from '../utils/validation';
import {
  Check,
  UploadCloud,
  FileText,
  Trash2,
  Plus,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Eye,
  X
} from 'lucide-react';

interface OwnerRow {
  id: string;
  name: string;
  percentage: string;
  role: string;
}

interface UploadedDoc {
  id: string;
  name: string;
  size: string;
  progress: number;
  type: string;
  file?: File;
}

export const SubmitPage: React.FC = () => {
  const { navigate, addToast } = useApp();

  const [step, setStep] = useState<1 | 2 | 3>(1);

  // Form Fields State
  // Requester
  const [reqName, setReqName] = useState('Abhishek Panwar');
  const [reqEmail, setReqEmail] = useState('panwarabhishek629@gmail.com');
  const [reqDept, setReqDept] = useState('Engineering Infrastructure');
  const [reqSpend, setReqSpend] = useState('84000');
  const [reqCurrency, setReqCurrency] = useState('USD');
  const [reqCategory, setReqCategory] = useState('Cloud SaaS & Security');

  // Company
  const [legalName, setLegalName] = useState('Acme Global Systems Ltd');
  const [tradingName, setTradingName] = useState('Acme Systems');
  const [country, setCountry] = useState('US');
  const [entityType, setEntityType] = useState('Corporation');
  const [incDate, setIncDate] = useState('2019-03-14');
  const [website, setWebsite] = useState('https://acmeglobalsys.com');
  const [address, setAddress] = useState('120 Broadway, Suite 1400, New York, NY 10005');

  // Contacts
  const [primaryContactName, setPrimaryContactName] = useState('Marcus Vance');
  const [primaryContactEmail, setPrimaryContactEmail] = useState('marcus@acmeglobalsys.com');
  const [apEmail, setApEmail] = useState('ap@acmeglobalsys.com');

  // Tax
  const [taxId, setTaxId] = useState('12-3456789');
  const [taxValidation, setTaxValidation] = useState<{ valid?: boolean; error?: string; validating?: boolean }>({ valid: true });

  // Banking
  const [bankHolderName, setBankHolderName] = useState('Acme Systems Holdings LLC');
  const [bankName, setBankName] = useState('JPMorgan Chase Bank, N.A.');
  const [accountNumber, setAccountNumber] = useState('98471281');
  const [isAccountFocused, setIsAccountFocused] = useState(false);
  const [routingNumber, setRoutingNumber] = useState('021000021');

  // Owners
  const [owners, setOwners] = useState<OwnerRow[]>([
    { id: '1', name: 'Marcus Vance', percentage: '60', role: 'Managing Director' },
    { id: '2', name: 'Helena Troy', percentage: '40', role: 'VP Operations' }
  ]);

  // Documents (real File objects; attached as file:<docId> on submit)
  const [documents, setDocuments] = useState<UploadedDoc[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<UploadedDoc | null>(null);

  // Review & Submit
  const [attestationChecked, setAttestationChecked] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Validate Tax ID on blur
  const handleTaxBlur = () => {
    setTaxValidation({ validating: true });
    setTimeout(() => {
      const res = validateTaxId(country, taxId);
      setTaxValidation({ valid: res.valid, error: res.error, validating: false });
    }, 200);
  };

  const addOwner = () => {
    setOwners(prev => [
      ...prev,
      { id: Math.random().toString(), name: '', percentage: '', role: 'Beneficial Owner' }
    ]);
  };

  const removeOwner = (id: string) => {
    setOwners(prev => prev.filter(o => o.id !== id));
  };

  const handleFileUpload = (file: File) => {
    const newDoc: UploadedDoc = {
      id: Math.random().toString(),
      name: file.name,
      size: file.size > 1024 * 1024 ? `${(file.size / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(file.size / 1024))} KB`,
      progress: 100,
      type: file.name.toLowerCase().endsWith('.pdf') ? 'PDF Attachment' : 'General Attachment',
      file,
    };
    setDocuments(prev => [...prev, newDoc]);
    addToast({ title: `Uploaded ${file.name}`, variant: 'success' });
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const entityMap: Record<string, string> = {
        Corporation: 'LLC', 'LLC': 'LLC', 'Sole Proprietorship': 'SOLE_PROP',
      };
      const taxIdType = country === 'US' ? 'EIN' : country === 'IN' ? 'GSTIN' : 'VAT';
      const formType = country === 'US' ? 'W9' : country === 'IN' ? 'GST_CERT' : 'VAT_CERT';
      const docTypeFor = (name: string) => {
        const n = name.toLowerCase();
        if (/w-?9/.test(n)) return 'W9';
        if (/void|cheque|check/.test(n)) return 'VOIDED_CHEQUE';
        if (/coi|insurance|liability/.test(n)) return 'COI';
        if (/incorp|certificate of incorporation/.test(n)) return 'INCORP_CERT';
        if (/bank|letter/.test(n)) return 'BANK_LETTER';
        return null;
      };
      const payload: Record<string, unknown> = {
        schema_version: '1.0',
        submission_type: 'NEW_VENDOR',
        existing_vendor_id: null,
        requester: {
          name: reqName, email: reqEmail, department: reqDept,
          business_justification: 'Submitted via VendorGate intake',
          expected_annual_spend: { amount: Number(reqSpend) || 0, currency: reqCurrency },
          category: 'OFFICE_SUPPLIES', data_access: false, one_time: false,
        },
        company: {
          legal_name: legalName, trading_name: tradingName || null,
          entity_type: entityMap[entityType] ?? 'LLC', country,
          incorporation_date: incDate,
          registered_address: { line1: address, line2: null, city: '', region: '', postal_code: '', country },
          remit_to_address: null, website: website || null,
          primary_contact: { name: primaryContactName, email: primaryContactEmail, phone: '' },
          ap_contact: { name: '', email: apEmail, phone: '' },
          owners: owners.filter(o => o.name).map(o => ({ name: o.name, ownership_pct: Number(o.percentage) || 0, role: o.role || 'OWNER' })),
        },
        tax: {
          country, tax_id_type: taxIdType, tax_id: taxId, secondary_ids: {},
          tax_classification: entityMap[entityType] ?? 'LLC', form_type: formType, vat_id: null,
        },
        bank: {
          country, currency: reqCurrency, account_holder_name: bankHolderName, bank_name: bankName,
          account_number: accountNumber.replace(/\D/g, ''),
          routing_number: country === 'US' ? routingNumber : null,
          iban: country === 'US' ? null : routingNumber, swift_bic: null, ifsc: null, sort_code: null,
        },
        documents: documents.map((d, i) => {
          const t = docTypeFor(d.name) ?? (country === 'US' ? 'W9' : country === 'IN' ? 'GST_CERT' : 'VAT_CERT');
          return { doc_id: `d${i + 1}`, doc_type: t, filename: d.name, sha256: 'pending-upload' };
        }),
        declarations: { aliases: [], bank_change_justification: null, remit_address_justification: null },
        submitter_meta: {},
      };
      const withFiles = documents.map((d, i) => ({ d, idx: i }));
      const files = withFiles
        .filter(({ d }) => d.file)
        .map(({ d, idx }) => ({ docId: `d${idx + 1}`, name: d.name, data: d.file as Blob }));
      const out = await api.submit(payload, files);
      addToast({
        title: 'Submission accepted',
        description: `Run ${out.run_id} created. Initiating 13-stage automated pipeline.`,
        variant: 'success',
      });
      navigate(`/runs/${out.run_id}?case_id=${out.case_id}`);
    } catch (e) {
      addToast({
        title: 'Submission failed',
        description: e instanceof Error ? e.message : 'Validation error',
        variant: 'danger',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="dot-grid-pattern py-6 px-2 flex justify-center">
      <div className="w-full max-w-[720px] space-y-8 animate-in fade-in-0 duration-240">
        <PageHeader
          title="Submit Vendor"
          description="Initiate compliance screening, document parsing, and bank verification."
        />

        {/* Step Indicator */}
        <div className="flex items-center justify-between border-b border-border-subtle pb-5">
          {[
            { num: 1, label: 'Vendor' },
            { num: 2, label: 'Documents' },
            { num: 3, label: 'Review' }
          ].map((st, idx) => {
            const isActive = step === st.num;
            const isDone = step > st.num;

            return (
              <React.Fragment key={st.num}>
                <div
                  onClick={() => isDone && setStep(st.num as any)}
                  className={`flex items-center gap-2.5 select-none ${
                    isDone ? 'cursor-pointer' : ''
                  }`}
                >
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-[12px] font-medium transition-all ${
                      isDone
                        ? 'bg-accent text-white'
                        : isActive
                        ? 'border-2 border-accent text-accent font-semibold'
                        : 'border border-border text-text-tertiary bg-surface'
                    }`}
                  >
                    {isDone ? <Check size={12} strokeWidth={3} /> : st.num}
                  </div>
                  <span
                    className={`text-[13px] font-medium ${
                      isActive ? 'text-text-primary' : 'text-text-tertiary'
                    }`}
                  >
                    {st.label}
                  </span>
                </div>

                {idx < 2 && (
                  <div
                    className={`flex-1 h-[2px] mx-4 transition-colors ${
                      step > idx + 1 ? 'bg-accent' : 'bg-border'
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* STEP 1: VENDOR FORM */}
        {step === 1 && (
          <div className="space-y-6">
            {/* Requester Section */}
            <Card padding="compact" title="1. Internal Requester Details">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Requester name" value={reqName} onChange={e => setReqName(e.target.value)} />
                <Input label="Requester email" value={reqEmail} onChange={e => setReqEmail(e.target.value)} />
                <Input label="Department" value={reqDept} onChange={e => setReqDept(e.target.value)} />
                <div className="grid grid-cols-2 gap-2">
                  <Input label="Expected annual spend" value={reqSpend} onChange={e => setReqSpend(e.target.value)} variant="number" />
                  <Select
                    label="Currency"
                    value={reqCurrency}
                    onChange={setReqCurrency}
                    options={[
                      { value: 'USD', label: 'USD ($)' },
                      { value: 'EUR', label: 'EUR (€)' },
                      { value: 'GBP', label: 'GBP (£)' }
                    ]}
                  />
                </div>
              </div>
            </Card>

            {/* Company Section */}
            <Card padding="compact" title="2. Company Identity">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Legal entity name" value={legalName} onChange={e => setLegalName(e.target.value)} />
                <Input label="Trading / DBA name" value={tradingName} onChange={e => setTradingName(e.target.value)} />
                <Select
                  label="Country of incorporation"
                  value={country}
                  onChange={setCountry}
                  options={[
                    { value: 'US', label: 'United States' },
                    { value: 'DE', label: 'Germany (DE)' },
                    { value: 'GB', label: 'United Kingdom' },
                    { value: 'IN', label: 'India (IN)' }
                  ]}
                />
                <Input label="Incorporation date" type="date" value={incDate} onChange={e => setIncDate(e.target.value)} />
                <Input label="Website URL" value={website} onChange={e => setWebsite(e.target.value)} />
                <Input label="Registered physical address" value={address} onChange={e => setAddress(e.target.value)} />
              </div>
            </Card>

            {/* Contacts Section */}
            <Card padding="compact" title="3. Authorized Contacts">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Primary contact name" value={primaryContactName} onChange={e => setPrimaryContactName(e.target.value)} />
                <Input label="Primary contact email" value={primaryContactEmail} onChange={e => setPrimaryContactEmail(e.target.value)} />
                <Input label="Accounts Payable (AP) email" value={apEmail} onChange={e => setApEmail(e.target.value)} containerClassName="md:col-span-2" />
              </div>
            </Card>

            {/* Tax Section */}
            <Card padding="compact" title="4. Tax Identification">
              <div className="space-y-4">
                <div className="relative">
                  <Input
                    label={country === 'US' ? 'US EIN (Format XX-XXXXXXX)' : country === 'IN' ? 'GSTIN (15 characters)' : 'VAT Registration Number'}
                    value={taxId}
                    onChange={e => setTaxId(e.target.value)}
                    onBlur={handleTaxBlur}
                    error={taxValidation.error}
                    helperText="Validated in real-time against statutory checksum specifications."
                    rightElement={
                      taxValidation.validating ? (
                        <Loader2 size={16} className="animate-spin text-accent" />
                      ) : taxValidation.valid ? (
                        <CheckCircle2 size={16} className="text-success" />
                      ) : null
                    }
                  />
                </div>
              </div>
            </Card>

            {/* Banking Section */}
            <Card padding="compact" title="5. Remittance Banking Details">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                  label="Bank account holder name"
                  value={bankHolderName}
                  onChange={e => setBankHolderName(e.target.value)}
                  helperText="Must match registered company legal name."
                />
                <Input
                  label="Bank Name"
                  value={bankName}
                  onChange={e => setBankName(e.target.value)}
                />
                <Input
                  label="Account number (masked on blur)"
                  value={isAccountFocused ? accountNumber : maskAccountNumber(accountNumber)}
                  onFocus={() => setIsAccountFocused(true)}
                  onBlur={() => setIsAccountFocused(false)}
                  onChange={e => setAccountNumber(e.target.value)}
                  variant="number"
                />
                <Input
                  label={country === 'US' ? 'ABA Routing Number (9 digits)' : 'IBAN / Swift Code'}
                  value={routingNumber}
                  onChange={e => setRoutingNumber(e.target.value)}
                />
              </div>
            </Card>

            {/* Beneficial Owners Section */}
            <Card padding="compact" title="6. Beneficial Ownership (>25%)">
              <div className="space-y-3">
                {owners.map((owner, idx) => (
                  <div key={owner.id} className="flex items-center gap-2">
                    <Input
                      placeholder="Owner legal name"
                      value={owner.name}
                      onChange={e => {
                        const val = e.target.value;
                        setOwners(prev => prev.map(o => o.id === owner.id ? { ...o, name: val } : o));
                      }}
                    />
                    <Input
                      placeholder="Share %"
                      value={owner.percentage}
                      onChange={e => {
                        const val = e.target.value;
                        setOwners(prev => prev.map(o => o.id === owner.id ? { ...o, percentage: val } : o));
                      }}
                      className="w-24"
                      variant="number"
                    />
                    <Input
                      placeholder="Role (e.g. Director)"
                      value={owner.role}
                      onChange={e => {
                        const val = e.target.value;
                        setOwners(prev => prev.map(o => o.id === owner.id ? { ...o, role: val } : o));
                      }}
                    />
                    {owners.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeOwner(owner.id)}
                        aria-label="Remove owner"
                        className="text-text-tertiary hover:text-danger p-2 rounded hover:bg-subtle"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                ))}

                <Button
                  size="sm"
                  variant="ghost"
                  leftIcon={<Plus size={14} />}
                  onClick={addOwner}
                >
                  Add owner
                </Button>
              </div>
            </Card>

            {/* Sticky Form Footer */}
            <div className="sticky bottom-4 z-20 p-4 rounded-[8px] bg-surface border border-border shadow-md dark:shadow-none flex items-center justify-between">
              <Button variant="ghost" onClick={() => navigate('/')}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => setStep(2)}
                disabled={!legalName || !taxId || !!taxValidation.error}
              >
                Continue to Documents →
              </Button>
            </div>
          </div>
        )}

        {/* STEP 2: DOCUMENTS */}
        {step === 2 && (
          <div className="space-y-6">
            <Card padding="compact" title="Required Document Attachments">
              <div className="space-y-4">
                <p className="text-[13px] text-text-secondary">
                  Based on policy rules for <span className="font-semibold text-text-primary">{country}</span> corporation,
                  the following verification documents are required:
                </p>

                {/* Dropzone */}
                <div
                  onDragOver={e => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onDrop={e => {
                    e.preventDefault();
                    setIsDragging(false);
                    const f = e.dataTransfer.files?.[0];
                    if (f) handleFileUpload(f);
                  }}
                  className={`h-40 rounded-[8px] border-2 border-dashed flex flex-col items-center justify-center p-6 text-center transition-all ${
                    isDragging
                      ? 'border-accent bg-accent-subtle/50 shadow-[0_0_12px_rgba(79,70,229,0.15)]'
                      : 'border-border hover:border-accent/60 bg-subtle/20'
                  }`}
                >
                  <UploadCloud size={32} className="text-text-tertiary mb-2 stroke-[1.5]" />
                  <div className="text-[13px] font-medium text-text-primary">
                    Drop PDF documents here or click to browse
                  </div>
                  <div className="text-[11px] text-text-tertiary mt-1">
                    Accepts PDF, TIFF, PNG up to 10MB per file
                  </div>
                  <input
                    type="file"
                    id="doc-upload"
                    className="sr-only"
                      onChange={e => {
                        if (e.target.files && e.target.files[0]) {
                          handleFileUpload(e.target.files[0]);
                        }
                      }}
                  />
                  <label htmlFor="doc-upload" className="mt-2 text-[12px] text-accent font-medium hover:underline cursor-pointer">
                    Browse files
                  </label>
                </div>

                {/* Attached Files List */}
                <div className="space-y-2 pt-2">
                  {documents.map(doc => (
                    <div
                      key={doc.id}
                      className="p-3 rounded-[6px] border border-border bg-surface flex items-center justify-between text-[13px]"
                    >
                      <div className="flex items-center gap-2.5 truncate">
                        <FileText size={18} className="text-accent shrink-0" />
                        <span className="font-medium text-text-primary truncate">{doc.name}</span>
                        <span className="text-[11px] text-text-tertiary font-mono">({doc.size})</span>
                        <Badge size="sm" color="neutral">{doc.type}</Badge>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setPreviewDoc(doc)}
                          className="text-[12px] text-accent hover:underline flex items-center gap-1"
                        >
                          <Eye size={14} />
                          <span>Preview</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => setDocuments(prev => prev.filter(d => d.id !== doc.id))}
                          className="text-text-tertiary hover:text-danger p-1 rounded hover:bg-subtle"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>

            <div className="sticky bottom-4 z-20 p-4 rounded-[8px] bg-surface border border-border shadow-md dark:shadow-none flex items-center justify-between">
              <Button variant="ghost" onClick={() => setStep(1)}>
                ← Back to Vendor
              </Button>
              <Button variant="primary" onClick={() => setStep(3)}>
                Review Submission →
              </Button>
            </div>
          </div>
        )}

        {/* STEP 3: REVIEW & SUBMIT */}
        {step === 3 && (
          <div className="space-y-6">
            <Card padding="compact" title="Review Submission Summary">
              <div className="space-y-6 text-[13px]">
                {/* Section 1 summary */}
                <div className="space-y-2 pb-4 border-b border-border-subtle">
                  <div className="flex justify-between items-center">
                    <span className="text-[12px] uppercase font-semibold text-text-tertiary">Vendor Profile</span>
                    <button type="button" onClick={() => setStep(1)} className="text-[12px] text-accent hover:underline">Edit</button>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-[13px]">
                    <div>Legal Name: <span className="font-medium text-text-primary">{legalName}</span></div>
                    <div>Country: <span className="font-medium text-text-primary">{country}</span></div>
                    <div>Tax ID: <span className="font-mono text-text-primary">{taxId}</span></div>
                    <div>Spend: <span className="font-medium text-text-primary">${Number(reqSpend).toLocaleString()}</span></div>
                  </div>
                </div>

                {/* Section 2 summary */}
                <div className="space-y-2 pb-4 border-b border-border-subtle">
                  <div className="flex justify-between items-center">
                    <span className="text-[12px] uppercase font-semibold text-text-tertiary">Banking Details</span>
                    <button type="button" onClick={() => setStep(1)} className="text-[12px] text-accent hover:underline">Edit</button>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-[13px]">
                    <div>Bank: <span className="font-medium text-text-primary">{bankName}</span></div>
                    <div>Holder: <span className="font-medium text-text-primary">{bankHolderName}</span></div>
                    <div>Account: <span className="font-mono text-text-primary">{maskAccountNumber(accountNumber)}</span></div>
                    <div>Routing: <span className="font-mono text-text-primary">{routingNumber}</span></div>
                  </div>
                </div>

                {/* Section 3 summary */}
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-[12px] uppercase font-semibold text-text-tertiary">Attached Documents ({documents.length})</span>
                    <button type="button" onClick={() => setStep(2)} className="text-[12px] text-accent hover:underline">Edit</button>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {documents.map(d => (
                      <span key={d.id} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-subtle border border-border text-[12px]">
                        <FileText size={14} className="text-accent" />
                        <span>{d.name}</span>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Attestation Checkbox */}
                <div className="pt-4 border-t border-border-subtle">
                  <Checkbox
                    checked={attestationChecked}
                    onChange={e => setAttestationChecked(e.target.checked)}
                    label="I confirm the information provided is accurate and authentic under statutory vendor onboarding guidelines."
                  />
                </div>

                {/* Submit Button */}
                <Button
                  size="lg"
                  variant="primary"
                  className="w-full h-11 text-[14px]"
                  disabled={!attestationChecked}
                  loading={isSubmitting}
                  onClick={handleSubmit}
                >
                  Submit vendor
                </Button>
              </div>
            </Card>

            <div className="flex justify-start">
              <Button variant="ghost" onClick={() => setStep(2)}>
                ← Back to Documents
              </Button>
            </div>
          </div>
        )}

        {/* PDF Document Preview Drawer */}
        <Drawer
          isOpen={!!previewDoc}
          onClose={() => setPreviewDoc(null)}
          width="wide"
          title={previewDoc?.name || 'Document Preview'}
          subtitle="Extracted text and signature OCR layers"
        >
          <div className="space-y-4">
            <div className="p-4 rounded-[6px] bg-subtle border border-border flex items-center justify-between text-[12px]">
              <div>File size: <span className="font-mono font-medium">{previewDoc?.size}</span></div>
              <Badge size="sm" color="success">OCR Passed</Badge>
            </div>

            <div className="h-[480px] rounded-[6px] border border-border bg-canvas p-6 flex flex-col items-center justify-center text-center space-y-3">
              <FileText size={48} className="text-text-tertiary stroke-[1.2]" />
              <div className="text-[14px] font-medium text-text-primary">
                {previewDoc?.name}
              </div>
              <p className="text-[12px] text-text-secondary max-w-sm">
                Document contains valid machine-readable metadata and digital certificate signing.
              </p>
            </div>
          </div>
        </Drawer>
      </div>
    </div>
  );
};
