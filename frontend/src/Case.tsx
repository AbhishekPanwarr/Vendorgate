import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

type Finding = { check_id: string; outcome: string; severity: number; reason_code: string | null; title: string; detail: string; evidence: { kind: string; ref: string; summary: string }[]; cached?: boolean; duration_ms?: number };

export default function CasePage() {
  const { caseId } = useParams();
  const [data, setData] = useState<any>(null);
  const [verify, setVerify] = useState<any>(null);
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => {
    fetch(`/api/v1/cases/${caseId}`).then((r) => r.json()).then(setData);
  }, [caseId]);
  if (!data) return <div>Loading…</div>;
  const d = data.run?.decision ?? {};
  const findings: Finding[] = data.run?.findings ?? [];
  const comps = d.score?.components ?? {};
  const blocking = findings.filter((f) => f.outcome === "FAIL");
  async function verifyChain() {
    const r = await fetch(`/api/v1/cases/${caseId}/audit/verify`).then((x) => x.json());
    setVerify(r);
  }
  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 960, margin: "0 auto", padding: 16 }}>
      <h1>
        {d.status === "APPROVED" ? "✅" : d.status === "PENDING" ? "⏳" : "⛔"} {d.status}
        <span style={{ fontSize: 14, marginLeft: 12 }}>tier {d.tier} · score {d.score?.total}</span>
      </h1>
      {(d.awaiting ?? []).map((a: string) => <span key={a} style={{ border: "1px solid", padding: "2px 8px", marginRight: 8 }}>awaiting {a}</span>)}
      {(d.counterfactuals ?? []).map((c: any, i: number) => (
        <div key={i} style={{ background: "#f6f6f6", padding: 8, marginTop: 8 }}>
          Fix {c.fix_set.join(", ")} → <b>{c.status}</b> (score {c.score}) · {c.note}
        </div>
      ))}
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
      {open && (() => {
        const f = findings.find((x, i) => x.check_id + i === open);
        return f ? <div style={{ border: "1px solid #ccc", padding: 8, marginTop: 8 }}>
          <b>{f.title}</b><p>{f.detail}</p>
          <ul>{f.evidence.map((e, j) => <li key={j}>[{e.kind}] {e.ref}: {e.summary}</li>)}</ul>
        </div> : null;
      })()}
      <h2>Audit</h2>
      <button onClick={verifyChain}>Verify chain</button>
      {verify && <div role="status">{verify.ok ? `✅ chain ok (${verify.length} events)` : `⛔ broken at ${verify.broken_at}`}</div>}
    </div>
  );
}
