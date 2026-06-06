import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

export default function TimelinePanel({ events }) {
  const series = events.map((event, index) => ({
    index,
    date: event.time?.slice(0, 10),
    value: index + 1
  }))

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 p-4">
      <h2 className="text-ink font-semibold mb-3">Chronologische tijdlijn</h2>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series}>
            <XAxis dataKey="date" hide />
            <YAxis hide />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#38BDF8" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
