import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

type Finding = { check_id: string; outcome: string; severity: number; reason_code: string | null; title: string; detail: string; evidence: { kind: string; ref: string; summary: string }[]; cached?: boolean; duration_ms?: number };

export default function CasePage() {
  const { caseId } = useParams();
  const [data, setData] = useState<any>(null);
  const [verify, setVerify] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [tab, setTab] = useState("findings");
  const [msg, setMsg] = useState<any>(null);
  const [cb, setCb] = useState({ number: "", source: "VENDOR_MASTER", outcome: "verified", attested: false });
  const [cbResult, setCbResult] = useState<any>(null);
  const [toast, setToast] = useState("");
  const [events, setEvents] = useState<any[]>([]);
  useEffect(() => {
    fetch(`/api/v1/cases/${caseId}`).then((r) => r.json()).then(setData);
    fetch(`/api/v1/cases/${caseId}/messages`).then((r) => r.json()).then(setMsg);
    fetch(`/api/v1/cases/${caseId}/events`).then((r) => r.json()).then(setEvents).catch(() => {});
  }, [caseId]);
  async function resubmitSame() {
    const run = data.run ?? {};
    const body = new FormData();
    body.append("payload", JSON.stringify(run.payload ?? {}));
    const r = await fetch(`/api/v1/cases/${caseId}/resubmit`, {
      method: "POST", headers: { "If-Match": String(data.current_version ?? 1) }, body,
    }).then((x) => x.json().then((j) => ({ status: x.status, body: j })));
    if (r.status === 409) setToast("No changes detected");
    else if (r.status === 412) setToast("Version mismatch — reloading");
    else if (r.status === 403) setToast("Not resubmittable");
    else setToast(`Resubmitted as v${r.body.new_version}`);
  }
  if (!data) return <div>Loading…</div>;
  const d = data.run?.decision ?? {};
  const findings: Finding[] = data.run?.findings ?? [];
  const comps = d.score?.components ?? {};
  const blocking = findings.filter((f) => f.outcome === "FAIL");
  async function verifyChain() {
    const r = await fetch(`/api/v1/cases/${caseId}/audit/verify`).then((x) => x.json());
    setVerify(r);
  }
  async function sendCallback() {
    const r = await fetch(`/api/v1/cases/${caseId}/callback`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ number_used: cb.number, number_source: cb.source, outcome: cb.outcome, attested: cb.attested, number_age_days: 60 }),
    }).then((x) => x.json());
    setCbResult(r);
  }
  const dupPair = findings.filter((f) => f.check_id === "C-DUP-02");
  const adjudications: any[] = data.run?.adjudications ?? [];
  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 960, margin: "0 auto", padding: 16 }}>
      <h1>
        {d.status === "APPROVED" ? "✅" : d.status === "PENDING" ? "⏳" : "⛔"} {d.status}
        <span style={{ fontSize: 14, marginLeft: 12 }}>tier {d.tier} · score {d.score?.total}</span>
      </h1>
      <div style={{ marginBottom: 12 }}>
        {["findings", "message", "network", "audit"].map((t) => (
          <button key={t} onClick={() => setTab(t)} style={{ fontWeight: tab === t ? "bold" : "normal", marginRight: 8 }}>{t}</button>
        ))}
      </div>
      {tab === "message" && (
        <div>
          <h2>Message</h2>
          {(d.awaiting ?? []).includes("VENDOR") && d.status === "PENDING" && (
            <div><button onClick={resubmitSame}>Resubmit unchanged (expect 409)</button></div>
          )}
          {toast && <div role="status">{toast}</div>}
          {msg ? <div><h3>{msg.subject}</h3><pre style={{ whiteSpace: "pre-wrap" }}>{msg.body}</pre>
            <p>rendered from template (LLM polish runs best-effort only)</p>
            <p>checker: {(msg.checker_errors ?? []).length === 0 ? "✅ clean" : `⛔ ${(msg.checker_errors ?? []).join("; ")}`}</p>
            <ul>{(msg.items ?? []).map((it: any, i: number) => <li key={i}>{it.fix_code}: {it.title}</li>)}</ul>
          </div> : <p>Loading…</p>}
        </div>
      )}
      {tab === "network" && (
        <div>
          <h2>Network</h2>
          {(data.run?.claims ?? []).filter((c: any) => c.doc_id).slice(0, 1).map((c: any) => (
            <div key={c.doc_id}>
              <embed src={`/api/v1/cases/${caseId}/docs/${c.doc_id}`} type="application/pdf" width="100%" height="400px" />
            </div>
          ))}
          {dupPair.length > 0 ? <div>
            <p>Shared bank account links this submission to <b>{dupPair[0].detail}</b></p>
            <ul>{findings.filter((f) => f.check_id.startsWith("C-DUP")).map((f, i) => <li key={i}>{f.check_id}: {f.title}</li>)}</ul>
          </div> : <p>No shared-attribute clusters for this case.</p>}
        </div>
      )}
      {tab === "audit" && (
        <div>
          <h2>Audit</h2>
          <button onClick={verifyChain}>Verify chain</button>
          {verify && <div role="status">{verify.ok ? `✅ chain ok (${verify.length} events)` : `⛔ broken at ${verify.broken_at}`}</div>}
          <h3>Case events</h3>
          <ul>{events.filter((e: any) => ["nudge.sent", "appeal.received", "case.closed", "attempt.recorded"].includes(e.type)).map((e: any, i: number) => (
            <li key={i}>{e.type} — {JSON.stringify(e.payload)}</li>
          ))}</ul>
        </div>
      )}
      {(d.awaiting ?? []).map((a: string) => <span key={a} style={{ border: "1px solid", padding: "2px 8px", marginRight: 8 }}>awaiting {a}</span>)}
      {(d.counterfactuals ?? []).map((c: any, i: number) => (
        <div key={i} style={{ background: "#f6f6f6", padding: 8, marginTop: 8 }}>
          Fix {c.fix_set.join(", ")} → <b>{c.status}</b> (score {c.score}) · {c.note}
        </div>
      ))}
      <h2>Callback desk</h2>
      <div>
        <input aria-label="callback number" placeholder="number dialed" value={cb.number} onChange={(e) => setCb({ ...cb, number: e.target.value })} />
        <select aria-label="number source" value={cb.source} onChange={(e) => setCb({ ...cb, source: e.target.value })}>
          <option value="VENDOR_MASTER">Vendor master</option>
          <option value="REGISTRY">Registry</option>
          <option value="PUBLIC_DIRECTORY">Public directory</option>
          <option value="FROM_REQUEST">From the request</option>
        </select>
        <label><input type="checkbox" checked={cb.attested} onChange={(e) => setCb({ ...cb, attested: e.target.checked })} /> attested</label>
        <button onClick={sendCallback}>Record callback</button>
        {cbResult && <div role="status">{cbResult.ok ? "✅ independent — findings cleared" : `⛔ ${cbResult.reason}`}</div>}
      </div>
      {tab === "findings" && (<div>
      {adjudications.length > 0 && (<div>
        <h3>Adjudication</h3>
        {adjudications.map((a: any, i: number) => (
          <div key={i}>{a.llm_unavailable ? "S8 adjudication: LLM unavailable — deterministic stands" : `S8 adjudication: ${a.label} (explain-only unless corroborated)`}</div>
        ))}
      </div>)}
      <h2>Score waterfall</h2>
      {Object.entries(comps).map(([k, v]: [string, any]) => (
        <div key={k}>{k} <progress value={v.points} max={25} /> {v.points} <small>{(v.drivers ?? []).join("; ")}</small></div>
      ))}
      <h2>Blocking items ({blocking.length})</h2>
      <ol>{(d.required_actions ?? []).map((a: any, i: number) => <li key={i}>{a.code} — {(a.field_paths ?? []).join(", ")}</li>)}</ol>
      <h2>Findings ({findings.length})</h2>
      <table border={1} cellPadding={4}>
        <thead><tr><th>check</th><th>outcome</th><th>reason</th><th>ms</th></tr></thead>
        <tbody>{findings.map((f, i) => (
          <tr key={i} onClick={() => setOpen(open === f.check_id + i ? null : f.check_id + i)} style={{ cursor: "pointer" }}>
            <td>{f.check_id}</td><td>{f.outcome}</td><td>{f.reason_code}</td><td>{f.duration_ms}</td>
          </tr>
        ))}</tbody>
      </table>
      {open && tab === "findings" && (() => {
        const f = findings.find((x, i) => x.check_id + i === open);
        return f ? <div style={{ border: "1px solid #ccc", padding: 8, marginTop: 8 }}>
          <b>{f.title}</b><p>{f.detail}</p>
          <ul>{f.evidence.map((e, j) => <li key={j}>[{e.kind}] {e.ref}: {e.summary}{e.kind === "llm" ? " (explain-only)" : ""}</li>)}</ul>
          {(data.run?.claims ?? []).filter((c: any) => c.doc_id && f.evidence.some((e: any) => e.ref === c.id || e.ref === c.path)).slice(0, 3).map((c: any, k: number) => (
            <div key={k}><small>doc {c.doc_id} p{c.page}: “{c.quote}”</small></div>
          ))}
        </div> : null;
      })()}
      </div>)}
    </div>
  );
}
