import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function Dashboard() {
  const [m, setM] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);
  useEffect(() => {
    fetch("/api/v1/metrics/dashboard").then((r) => r.json()).then(setM);
    fetch("/api/v1/cases").then((r) => r.json()).then(setCases);
  }, []);
  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 960, margin: "0 auto", padding: 16 }}>
      <h1>VendorGate dashboard</h1>
      <div style={{ display: "flex", gap: 12 }}>
        {(["volume", "auto_approve_rate"] as const).map((k) => (
          <div key={k} style={{ border: "1px solid #ccc", padding: 12 }}>{k}: <b>{m ? JSON.stringify(m[k]) : "…"}</b></div>
        ))}
        <div style={{ border: "1px solid #ccc", padding: 12 }}>by_status: <b>{m ? JSON.stringify(m.by_status) : "…"}</b></div>
      </div>
      <h2>Runs</h2>
      <table border={1} cellPadding={4}>
        <thead><tr><th>case</th><th>status</th><th>tier</th><th>score</th><th>reasons</th></tr></thead>
        <tbody>{cases.map((c) => (
          <tr key={c.case_id}><td><Link to={`/cases/${c.case_id}`}>{c.case_id}</Link></td>
            <td>{c.status}</td><td>{c.tier}</td><td>{c.score}</td><td>{(c.reason_codes ?? []).join(", ")}</td></tr>
        ))}</tbody>
      </table>
      <p><Link to="/submit">New submission</Link> · <Link to="/benchmark">Benchmark</Link> · <Link to="/foolit">Fool-it Lab</Link> · <Link to="/policy">Policy</Link></p>
    </div>
  );
}
