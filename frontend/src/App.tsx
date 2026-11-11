import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useParams, Link } from "react-router-dom";
import CasePage from "./Case";
import Dashboard from "./Dashboard";
import Approvals from "./Approvals";

function Submit() {
  const nav = useNavigate();
  const [name, setName] = useState("Test Vendor");
  const [country, setCountry] = useState("US");
  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload = {
      schema_version: "1.0",
      submission_type: "NEW_VENDOR",
      existing_vendor_id: null,
      requester: {
        name: "Dana Whitfield", email: "dana@buyer.example", department: "Facilities",
        business_justification: "skeleton submit", expected_annual_spend: { amount: 1000, currency: "USD" },
        category: "OFFICE_SUPPLIES", data_access: false, one_time: false,
      },
      company: {
        legal_name: name, trading_name: null, entity_type: "LLC", country,
        incorporation_date: "2016-04-12",
        registered_address: { line1: "410 Market St", line2: null, city: "Columbus", region: "OH", postal_code: "43215", country },
        remit_to_address: null, website: "https://example.com",
        primary_contact: { name: "A", email: "a@example.com", phone: "+16145550142" },
        ap_contact: { name: "B", email: "b@example.com", phone: "+16145550143" },
        owners: [],
      },
      tax: { country, tax_id_type: "EIN", tax_id: "12-3456789", secondary_ids: {}, tax_classification: "LLC", form_type: "W9", vat_id: null },
      bank: { country, currency: "USD", account_holder_name: name, bank_name: "Bank", account_number: "000123456789", routing_number: "011000015", iban: null, swift_bic: null, ifsc: null, sort_code: null },
      documents: [],
      declarations: { aliases: [], bank_change_justification: null, remit_address_justification: null },
      submitter_meta: {},
    };
    const fd = new FormData();
    fd.append("payload", JSON.stringify(payload));
    const r = await fetch("/api/v1/submissions", { method: "POST", body: fd });
    const j = await r.json();
    nav(`/runs/${j.run_id}?case_id=${j.case_id}`);
  }
  return (
    <form onSubmit={onSubmit}>
      <h1>VendorGate — submit</h1>
      <input value={name} onChange={(e) => setName(e.target.value)} aria-label="legal name" />
      <input value={country} onChange={(e) => setCountry(e.target.value)} aria-label="country" />
      <input type="file" aria-label="file" />
      <button type="submit">Submit</button>
    </form>
  );
}

function Run() {
  const { runId } = useParams();
  const q = new URLSearchParams(window.location.search);
  const [events, setEvents] = useState<string[]>([]);
  const [decision, setDecision] = useState("");
  const [delta, setDelta] = useState<any>(null);
  useEffect(() => {
    const es = new EventSource(`/api/v1/runs/${runId}/events`);
    es.onmessage = (m) => {
      setEvents((p) => [...p, m.data]);
      try {
        const j = JSON.parse(m.data);
        if (j.type === "decision.made") setDecision(JSON.stringify(j.data));
        if (j.type === "run.completed") {
          fetch(`/api/v1/runs/${runId}`).then((r) => r.json()).then((run) => setDelta(run.delta ?? null));
        }
      } catch { /* ignore */ }
    };
    void q;
    return () => es.close();
  }, [runId]);
  return (
    <div>
      <h1>Run {runId}</h1>
      {decision && <div role="status">{decision}</div>}
      {delta && (
        <div style={{ border: "1px solid", padding: 8, margin: "8px 0" }}>
          <b>Delta run</b> — Re-ran: {delta.rerun} · Served from cache: {delta.cached}
          {(delta.resolved ?? []).length > 0 && <div>✓ Resolved: {delta.resolved.join(", ")}</div>}
          {(delta.introduced ?? []).length > 0 && <div>⚠ Introduced: {delta.introduced.join(", ")}</div>}
        </div>
      )}
      <ul>{events.map((e, i) => <li key={i}>{e}</li>)}</ul>
    </div>
  );
}

function Admin() {
  async function reset() {
    await fetch("/api/v1/admin/reset", { method: "POST" });
  }
  return <div><h1>Admin</h1><button onClick={reset}>Reset demo data</button></div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/submit" element={<Submit />} />
        <Route path="/runs/:runId" element={<Run />} />
        <Route path="/cases/:caseId" element={<CasePage />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/admin" element={<Admin />} />
      </Routes>
    </BrowserRouter>
  );
}
