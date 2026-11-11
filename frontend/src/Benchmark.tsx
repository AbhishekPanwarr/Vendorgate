import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function R(v: any) {
  if (!v || typeof v.rate !== "number") return "—";
  return `${(v.rate * 100).toFixed(1)}% (${v.k}/${v.n})`;
}

export default function Benchmark() {
  const [d, setD] = useState<any>(null);
  useEffect(() => {
    fetch("/api/v1/eval/latest").then((r) => r.json()).then(setD);
  }, []);
  if (!d) return <div style={{ padding: 16 }}>loading…</div>;
  const latest = d["latest.json"];
  const t = latest.test_hybrid;
  const abl = latest.ablation_dev;
  return (
    <div style={{ fontFamily: "system-ui", maxWidth: 1100, margin: "0 auto", padding: 16 }}>
      <p><Link to="/">← dashboard</Link></p>
      <h1>Benchmark</h1>
      <div style={{ border: "2px solid #060", padding: 16, marginBottom: 16 }}>
        <div>E1 critical false-approve rate: <b data-testid="e1">{R(t.E1_critical_false_approve)}</b></div>
        <div>95% upper bound: <b>{(t.E1_critical_false_approve.hi * 100).toFixed(1)}%</b> (n={t.E1_critical_false_approve.n})</div>
      </div>
      <h2>Test split (hybrid, frozen)</h2>
      <table border={1} cellPadding={4} data-testid="metrics">
        <tbody>
          {["E2_false_approve", "E3_false_reject", "E4_friction", "E7_awaiting", "E20_audit_chain"].map((k) => (
            <tr key={k}><td>{k}</td><td>{R((t as any)[k])}</td></tr>
          ))}
          <tr><td>E5 status accuracy</td><td>{(t.E5_status_accuracy.rate * 100).toFixed(1)}%</td></tr>
          <tr><td>E6 reason micro F1</td><td>{t.E6_reason_codes.micro.f1.toFixed(3)}</td></tr>
          <tr><td>E6 exact-set</td><td>{R(t.E6_reason_codes.exact_set)}</td></tr>
          <tr><td>E13 sanctions recall</td><td>{R(t.E13_sanctions.sanctions_recall)}</td></tr>
          <tr><td>E14 network recall</td><td>{R(t.E14_network.recall)}</td></tr>
          <tr><td>E16 invariance</td><td>{R(t.E16_invariance)}</td></tr>
          <tr><td>E21 AUC</td><td>{t.E21_auc.auc.toFixed(3)}</td></tr>
          <tr><td>E18 p50/p95 (s)</td><td>{t.E18_latency.p50} / {t.E18_latency.p95}</td></tr>
        </tbody>
      </table>
      <h2>Confusion (expected → actual)</h2>
      <table border={1} cellPadding={4} data-testid="confusion">
        <thead><tr><th></th><th>APPROVED</th><th>PENDING</th><th>REJECTED</th></tr></thead>
        <tbody>{["APPROVED", "PENDING", "REJECTED"].map((e) => (
          <tr key={e}><td>{e}</td>{["APPROVED", "PENDING", "REJECTED"].map((a) => (
            <td key={a}>{t.E5_status_accuracy.confusion[e][a]}</td>))}</tr>))}</tbody>
      </table>
      <h2>Ablation (dev split, 7 modes)</h2>
      <table border={1} cellPadding={4} data-testid="ablation">
        <thead><tr><th>mode</th><th>E1</th><th>E3</th><th>E5</th><th>E6 F1</th><th>p95</th></tr></thead>
        <tbody>{Object.keys(abl).map((m) => (
          <tr key={m}><td>{m}</td><td>{R(abl[m].E1)}</td><td>{R(abl[m].E3)}</td>
            <td>{(abl[m].E5 * 100).toFixed(1)}%</td><td>{abl[m].E6_f1}</td><td>{abl[m].p95}</td></tr>))}
          <tr><td>llm-only (test-25 slice)</td><td>{R(latest.llm_only_test25.E1_critical_false_approve)}</td>
            <td>{R(latest.llm_only_test25.E3_false_reject)}</td>
            <td>{(latest.llm_only_test25.E5_status_accuracy.rate * 100).toFixed(1)}%</td>
            <td>{latest.llm_only_test25.E6_reason_codes.micro.f1.toFixed(3)}</td>
            <td>{latest.llm_only_test25.E19_cost.tokens} tok</td></tr>
        </tbody>
      </table>
      <h2>Name pairs / extraction / network</h2>
      <pre data-testid="sets">{JSON.stringify(latest.sets, null, 1).slice(0, 2000)}</pre>
      <h2>Limitations</h2>
      <ul data-testid="limitations">{latest.limitations.map((l: string) => <li key={l}>{l}</li>)}</ul>
      <p>Dataset: {latest.manifest.dataset_sha256.slice(0, 12)} · split: {latest.manifest.test_split_sha256.slice(0, 12)} · seed {latest.manifest.seed}</p>
      <p>Synthetic data only; labels encode our policy; no real PII.</p>
    </div>
  );
}
