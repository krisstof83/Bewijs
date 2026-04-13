export default function RelationsPanel({ graph }) {
  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
      <h2 className="text-ink font-semibold mb-3">Personen & relaties</h2>
      <p className="text-sm text-slate-300">Nodes: {graph.nodes?.length || 0} | Edges: {graph.edges?.length || 0}</p>
      <ul className="text-xs text-slate-400 mt-2 space-y-1 max-h-36 overflow-auto">
        {(graph.edges || []).slice(0, 8).map((edge, idx) => (
          <li key={idx}>{edge.source} → {edge.target} ({edge.weight})</li>
        ))}
      </ul>
    </div>
  )
}
