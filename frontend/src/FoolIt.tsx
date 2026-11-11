import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const BASES = ["HP-1", "HP-2", "HP-3", "HP-3-HIGH", "EC-1", "EC-3a", "EC-3b", "EC-4a", "EC-4b"];

export default function FoolIt() {
  const [ops, setOps] = useState<any[]>([]);
  const [vendors, setVendors] = useState<any[]>([]);
  const [vendor, setVendor] = useState("HP-1");
  const [sel, setSel] = useState<string[]>([]);
  const [res, setRes] = useState<any>(null);
  const [counts, setCounts] = useState({ attempts: 0, critical: 0, criticalApprovals: 0 });
  useEffect(() => {
    fetch("/api/v1/foolit/operators").then((r) => r.json()).then(setOps);
    fetch("/api/v1/vendors").then((r) => r.json()).then((v) => setVendors(v.map((x: any) => x.vendor_id)));
  }, []);
  function toggle(id: string) {
    setSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  }
  async function run() {
    const r = await fetch("/api/v1/foolit/run", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ vendor_id: vendor, ops: sel }),
    }).then((x) => x.json());
    setRes(r);
    setCounts((c) => ({
      attempts: c.attempts + 1,
      critical: c.critical + (r.expected?.critical ? 1 : 0),
      criticalApprovals: c.criticalApprovals + (r.expected?.critical && r.actual?.status === "APPROVED" ? 1 : 0),
    }));
  }
  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 1000, margin: "0 auto", padding: 16 }}>
      <p><Link to="/">← dashboard</Link></p>
      <h1>Fool-it Lab</h1>
      <p>Attempts: <b data-testid="attempts">{counts.attempts}</b> · critical: {counts.critical} · critical approvals: <b data-testid="crit-approvals">{counts.criticalApprovals}</b></p>
      <label>base vendor <select value={vendor} onChange={(e) => setVendor(e.target.value)}>
        {BASES.map((b) => <option key={b} value={b}>{b}</option>)}
      </select></label>
      <h2>Operators M-01…M-48</h2>
      <div style={{ columns: 2 }}>
        {ops.map((o) => (
          <label key={o.id} style={{ display: "block" }}>
            <input type="checkbox" checked={sel.includes(o.id)} onChange={() => toggle(o.id)} />
            <b>{o.id}</b> {o.description}
          </label>))}
      </div>
      <button onClick={run} data-testid="run">Run through pipeline</button>
      {res && (
        <div data-testid="result" style={{ marginTop: 12, border: "1px solid #999", padding: 12 }}>
          <div>Operator says the system should: <b>{res.expected.status}</b> ({(res.expected.blocking_reason_codes ?? []).join(", ")})</div>
          <div>System did: <b>{res.actual.status === res.expected.status ? "✓ " : "✗ "}{res.actual.status}</b> ({(res.actual.reason_codes ?? []).join(", ")})</div>
        </div>)}
    </div>
  );
}
