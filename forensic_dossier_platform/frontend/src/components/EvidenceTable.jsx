export default function EvidenceTable({ evidence }) {
  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
      <h2 className="text-ink font-semibold mb-3">Bewijsviewer</h2>
      <div className="overflow-auto max-h-80">
        <table className="w-full text-sm text-slate-200">
          <thead>
            <tr className="text-left text-slate-400">
              <th>ID</th><th>Bestand</th><th>Type</th><th>Datum</th><th>Relevantie</th><th>Sterkte</th><th>Tags</th>
            </tr>
          </thead>
          <tbody>
            {evidence.map((row) => (
              <tr key={row.evidence_id} className="border-t border-slate-800 align-top">
                <td>{row.evidence_id}</td>
                <td>{row.filename}</td>
                <td>{row.type}</td>
                <td>{row.date?.slice(0, 10)}</td>
                <td>{row.legal_relevance}</td>
                <td>{row.evidence_strength}</td>
                <td>{(row.tags || []).join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
