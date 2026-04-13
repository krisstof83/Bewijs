export default function AnalysisPanel({ findings, scenarios }) {
  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 space-y-4">
      <div>
        <h2 className="text-ink font-semibold mb-3">Forensische analyse</h2>
        <div className="space-y-2 text-sm">
          {findings.length === 0 && <p className="text-slate-400">Geen inconsistenties gevonden.</p>}
          {findings.map((finding, i) => (
            <div key={i} className="bg-slate-800 p-2 rounded text-slate-200">
              <p className="font-semibold">{finding.evidence_id}</p>
              <p>{finding.message}</p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-ink font-semibold mb-2">Tegenpartij-scenario's</h3>
        <ul className="space-y-2 text-xs text-slate-300">
          {scenarios.map((scenario, i) => (
            <li key={i} className="bg-slate-800 p-2 rounded">
              <p className="font-semibold">{scenario.scenario} ({scenario.risk_level})</p>
              <p>{scenario.likely_action}</p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
