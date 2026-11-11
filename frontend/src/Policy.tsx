import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function Policy() {
  const [p, setP] = useState<any>(null);
  useEffect(() => {
    fetch("/api/v1/policy").then((r) => r.json()).then(setP);
  }, []);
  if (!p) return <div style={{ padding: 16 }}>loading…</div>;
  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 900, margin: "0 auto", padding: 16 }}>
      <p><Link to="/">← dashboard</Link></p>
      <h1>Policy</h1>
      <p data-testid="policy-hash">policy hash: <code>{p.policy_hash}</code> <button onClick={() => navigator.clipboard.writeText(p.policy_hash)}>copy</button></p>
      <h2>Assumptions A-01…A-15</h2>
      <ol data-testid="assumptions">
        {(p.assumptions ?? []).map((a: any) => <li key={a.id}><b>{a.id}</b> {a.text}</li>)}
      </ol>
    </div>
  );
}
