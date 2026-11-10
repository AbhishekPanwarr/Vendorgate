import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function Approvals() {
  const [role, setRole] = useState("CONTROLLER");
  const [cases, setCases] = useState<any[]>([]);
  const [actor, setActor] = useState("Priya Nair");
  const [note, setNote] = useState("");
  const [result, setResult] = useState<any>(null);
  useEffect(() => {
    fetch(`/api/v1/approvals?role=${role}`).then((r) => r.json()).then(setCases);
  }, [role]);
  async function approve(caseId: string, action: string) {
    const r = await fetch(`/api/v1/cases/${caseId}/approvals`, {
      method: "POST", headers: { "Content-Type": "application/json", "X-Actor": actor, "X-Role": role },
      body: JSON.stringify({ action, note }),
    }).then((x) => x.json());
    setResult(r);
  }
  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 960, margin: "0 auto", padding: 16 }}>
      <h1>Approvals queue</h1>
      <label>role <select value={role} onChange={(e) => setRole(e.target.value)}>
        <option value="CONTROLLER">Controller</option>
        <option value="COMPLIANCE">Compliance</option>
        <option value="AP_ANALYST">AP Analyst</option>
      </select></label>
      <label> actor <input value={actor} onChange={(e) => setActor(e.target.value)} /></label>
      <table border={1} cellPadding={4}>
        <thead><tr><th>case</th><th>status</th><th>tier</th><th>route</th><th>actions</th></tr></thead>
        <tbody>{cases.map((c) => (
          <tr key={c.case_id}>
            <td><Link to={`/cases/${c.case_id}`}>{c.case_id}</Link></td>
            <td>{c.status}</td><td>{c.tier}</td><td>{(c.approval_route ?? []).join(", ")}</td>
            <td>
              <button onClick={() => approve(c.case_id, "APPROVE")}>Approve</button>
              <button onClick={() => approve(c.case_id, "REJECT")}>Reject</button>
            </td>
          </tr>
        ))}</tbody>
      </table>
      <input aria-label="note" placeholder="note (required)" value={note} onChange={(e) => setNote(e.target.value)} />
      {result && <div role="status">{result.type ? `⛔ ${result.type}` : "✅ recorded"}</div>}
    </div>
  );
}
