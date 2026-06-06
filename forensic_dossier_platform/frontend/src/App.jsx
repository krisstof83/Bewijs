import { useEffect, useMemo, useState } from 'react'
import Sidebar from './components/Sidebar'
import EvidenceTable from './components/EvidenceTable'
import TimelinePanel from './components/TimelinePanel'
import RelationsPanel from './components/RelationsPanel'
import AnalysisPanel from './components/AnalysisPanel'
import {
  autoTag,
  fetchEvidence,
  fetchGraph,
  fetchInconsistencies,
  fetchPrivacy,
  fetchScenarios,
  fetchTimeline,
  runScan,
  runSearch
} from './lib/api'

export default function App() {
  const [dark, setDark] = useState(true)
  const [evidence, setEvidence] = useState([])
  const [timeline, setTimeline] = useState([])
  const [graph, setGraph] = useState({ nodes: [], edges: [] })
  const [findings, setFindings] = useState([])
  const [scenarios, setScenarios] = useState([])
  const [privacy, setPrivacy] = useState(null)
  const [query, setQuery] = useState('')
  const [personFilter, setPersonFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [status, setStatus] = useState('Gereed')

  const loadAll = async () => {
    const [e, t, g, f, s, p] = await Promise.all([
      fetchEvidence({ person: personFilter, type: typeFilter || undefined }),
      fetchTimeline(),
      fetchGraph(),
      fetchInconsistencies(),
      fetchScenarios(),
      fetchPrivacy()
    ])
    setEvidence(e.data)
    setTimeline(t.data)
    setGraph(g.data)
    setFindings(f.data)
    setScenarios(s.data)
    setPrivacy(p.data)
  }

  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    loadAll().catch(() => setStatus('Backend offline - start Flask server'))
  }, [dark])

  const onScan = async () => {
    setStatus('Scannen...')
    await runScan('../sample_data')
    await loadAll()
    setStatus('Scan afgerond')
  }

  const onAutoTag = async () => {
    setStatus('Auto-tagging...')
    await autoTag()
    await loadAll()
    setStatus('Auto-tagging klaar')
  }

  const visibleEvidence = useMemo(() => evidence, [evidence])

  const onSearch = async () => {
    if (!query.trim()) {
      await loadAll()
      return
    }
    const { data } = await runSearch(query)
    setEvidence(data)
  }

  const onApplyFilters = async () => {
    const { data } = await fetchEvidence({ person: personFilter || undefined, type: typeFilter || undefined })
    setEvidence(data)
  }

  return (
    <div className="min-h-screen flex text-ink bg-slate-950">
      <Sidebar onScan={onScan} onAutoTag={onAutoTag} dark={dark} setDark={setDark} />
      <main className="flex-1 p-6 space-y-4">
        <div className="flex justify-between items-center gap-3">
          <p className="text-slate-300">Audit status: {status}</p>
          <div className="flex gap-2 items-center">
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Zoeken op tekst" className="bg-slate-900 border border-slate-800 rounded p-2 text-sm" />
            <button onClick={onSearch} className="bg-accent text-slate-900 rounded px-4">Zoek</button>
            <a href="http://localhost:5050/api/export/pdf" className="bg-slate-700 rounded px-4 py-2 text-sm">Export PDF</a>
          </div>
        </div>

        <div className="flex gap-2 items-center">
          <input value={personFilter} onChange={(e) => setPersonFilter(e.target.value)} placeholder="Filter persoon" className="bg-slate-900 border border-slate-800 rounded p-2 text-sm" />
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="bg-slate-900 border border-slate-800 rounded p-2 text-sm">
            <option value="">Alle types</option>
            <option value="document">Document</option>
            <option value="chat_export">Chat export</option>
            <option value="image">Image</option>
            <option value="data">Data</option>
          </select>
          <button onClick={onApplyFilters} className="bg-slate-700 rounded px-4 py-2 text-sm">Filter</button>
          {privacy && <span className="text-xs text-slate-400">AVG-risico: {privacy.risk_level} ({privacy.files_with_personal_data} PII-bestanden)</span>}
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="col-span-2"><EvidenceTable evidence={visibleEvidence} /></div>
          <AnalysisPanel findings={findings} scenarios={scenarios} />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <TimelinePanel events={timeline} />
          <RelationsPanel graph={graph} />
        </div>
      </main>
    </div>
  )
}
