export default function Sidebar({ onScan, onAutoTag, dark, setDark }) {
  return (
    <aside className="w-72 bg-panel p-4 border-r border-slate-800 flex flex-col gap-3">
      <h1 className="text-ink text-xl font-bold">ForensicOps</h1>
      <button onClick={onScan} className="bg-accent text-slate-900 font-semibold rounded p-2">Scan bewijsbron</button>
      <button onClick={onAutoTag} className="bg-slate-700 text-ink rounded p-2">AI auto-tagging</button>
      <button onClick={() => setDark(!dark)} className="bg-slate-700 text-ink rounded p-2">Dark mode toggle</button>
      <nav className="text-slate-300 text-sm mt-4 space-y-1">
        <p>• Dashboard</p>
        <p>• Tijdlijn</p>
        <p>• Relatienetwerk</p>
        <p>• Analyse</p>
        <p>• Export</p>
      </nav>
    </aside>
  )
}
