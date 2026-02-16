import { useState, useEffect, useRef } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell, PieChart, Pie,
} from 'recharts'

const API = '/api'

// ─── Helpers ──────────────────────────────────────────────────────────────────
const fmtNum = (n) => (n != null ? Math.round(n).toLocaleString() : '—')
const fmtEur = (n) => `€${fmtNum(n)}`
const fmtPct = (n) => (n != null ? `${n > 0 ? '+' : ''}${n.toFixed(1)}%` : '—')

function scoreColor(score) {
  if (score >= 7) return '#059669'
  if (score >= 5) return '#d97706'
  return '#dc2626'
}

function scoreVerdict(score) {
  if (score >= 7) return 'BUY'
  if (score >= 5) return 'HOLD'
  return 'AVOID'
}

function dpeColor(dpe) {
  const colors = {
    A: '#16a34a', B: '#65a30d', C: '#ca8a04', D: '#ea580c',
    E: '#dc2626', F: '#b91c1c', G: '#7f1d1d',
  }
  return colors[dpe] || '#9ca3af'
}

const STEPS = [
  { id: 1, icon: '🗄️', label: 'Database Setup' },
  { id: 2, icon: '🔍', label: 'Scraping Data' },
  { id: 3, icon: '📊', label: 'Investment Analysis' },
  { id: 4, icon: '☁️', label: 'Google Sheets Sync' },
]

// ─── Hero Section (Idle) ──────────────────────────────────────────────────────
function Hero({ onStart, loading }) {
  return (
    <div className="hero">
      <div className="hero-card">
        <div className="hero-icon">🏘️</div>
        <h2>Lyon Real Estate Investment Analyzer</h2>
        <p className="hero-desc">
          Automated pipeline that scrapes live property listings, stores data in
          SQLite &amp; Google Sheets, and generates AI-powered investment analysis
          across all 9 arrondissements.
        </p>
        <button className="btn btn-start" onClick={onStart} disabled={loading}>
          <span className="btn-icon">▶</span> Start Analysis
        </button>
        <div className="hero-features">
          <div className="feature">
            <span>🔍</span>
            <span>Live Scraping</span>
          </div>
          <div className="feature">
            <span>🤖</span>
            <span>AI Insights</span>
          </div>
          <div className="feature">
            <span>📊</span>
            <span>Sheets Sync</span>
          </div>
          <div className="feature">
            <span>📈</span>
            <span>ROI Analysis</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Progress Section (Running) ───────────────────────────────────────────────
function Progress({ step, stepLabel }) {
  const pct = Math.round((step / STEPS.length) * 100)
  return (
    <div className="progress-section">
      <div className="progress-card">
        <h2>Analysis in Progress</h2>
        <p className="progress-sublabel">{stepLabel}</p>

        <div className="steps">
          {STEPS.map((s) => {
            let cls = 'step'
            if (s.id < step) cls += ' step-done'
            else if (s.id === step) cls += ' step-active'
            return (
              <div key={s.id} className={cls}>
                <div className="step-indicator">
                  {s.id < step ? '✓' : s.id === step ? s.icon : s.id}
                </div>
                <span className="step-label">{s.label}</span>
              </div>
            )
          })}
        </div>

        <div className="progress-bar-track">
          <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
        </div>
        <span className="progress-pct">{pct}%</span>
      </div>
    </div>
  )
}

// ─── Error View ───────────────────────────────────────────────────────────────
function ErrorView({ error, onRetry }) {
  return (
    <div className="hero">
      <div className="hero-card error-card">
        <div className="hero-icon">⚠️</div>
        <h2>Something went wrong</h2>
        <p className="error-msg">{error}</p>
        <button className="btn btn-start" onClick={onRetry}>
          🔄 Retry
        </button>
      </div>
    </div>
  )
}

// ─── Stat Cards ───────────────────────────────────────────────────────────────
function StatCards({ summary }) {
  const cards = [
    { icon: '🏠', label: 'Properties', value: summary.total, color: '#3b82f6' },
    { icon: '💰', label: 'Avg Price', value: fmtEur(summary.avg_price), color: '#8b5cf6' },
    { icon: '📐', label: 'Avg €/m²', value: fmtEur(summary.avg_m2), color: '#0891b2' },
    { icon: '⭐', label: 'Undervalued', value: summary.undervalued, color: '#059669' },
  ]
  return (
    <div className="stat-cards">
      {cards.map((c, i) => (
        <div key={i} className="stat-card" style={{ borderTopColor: c.color }}>
          <span className="stat-icon">{c.icon}</span>
          <div className="stat-value">{c.value}</div>
          <div className="stat-label">{c.label}</div>
        </div>
      ))}
    </div>
  )
}

// ─── Arrondissement Chart ─────────────────────────────────────────────────────
function ArrondissementChart({ arrondissements }) {
  const chartData = arrondissements.map((a) => ({
    ...a,
    displayName: a.name.replace('Lyon ', ''),
  }))

  const CustomTooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div className="chart-tooltip">
        <strong>{d.name}</strong>
        <div>Avg: {fmtEur(d.avg_m2)}/m²</div>
        <div>Market: {fmtEur(d.market_avg)}/m²</div>
        <div>vs Market: {fmtPct(d.vs_market)}</div>
        <div>Yield: {d.yield_pct}%</div>
        <div>Properties: {d.count}</div>
      </div>
    )
  }

  return (
    <div className="card chart-card">
      <h3>📍 Price by Arrondissement (€/m²)</h3>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 30, top: 5, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis type="number" tickFormatter={(v) => `€${(v / 1000).toFixed(0)}k`} stroke="#94a3b8" />
          <YAxis type="category" dataKey="displayName" width={55} stroke="#94a3b8" fontSize={13} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="avg_m2" name="Avg €/m²" radius={[0, 6, 6, 0]} barSize={24}>
            {chartData.map((entry, i) => (
              <Cell
                key={i}
                fill={
                  entry.vs_market < -5 ? '#059669' :
                  entry.vs_market > 10 ? '#dc2626' : '#3b82f6'
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="chart-legend">
        <span className="legend-item"><span className="dot" style={{ background: '#059669' }} /> Below market</span>
        <span className="legend-item"><span className="dot" style={{ background: '#3b82f6' }} /> At market</span>
        <span className="legend-item"><span className="dot" style={{ background: '#dc2626' }} /> Above market</span>
      </div>
    </div>
  )
}

// ─── DPE Distribution ─────────────────────────────────────────────────────────
function DpeChart({ properties }) {
  const counts = {}
  properties.forEach((p) => {
    const d = p.dpe || '?'
    counts[d] = (counts[d] || 0) + 1
  })
  const data = Object.entries(counts)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => ({ name: k, value: v, fill: dpeColor(k) }))

  return (
    <div className="card chart-card dpe-chart-card">
      <h3>⚡ DPE Distribution</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data} dataKey="value" nameKey="name"
            cx="50%" cy="50%" innerRadius={50} outerRadius={85}
            paddingAngle={3} label={({ name, value }) => `${name} (${value})`}
          >
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

// ─── Properties Table ─────────────────────────────────────────────────────────
function PropertiesTable({ properties }) {
  const [sortKey, setSortKey] = useState('score')
  const [sortAsc, setSortAsc] = useState(false)

  const sorted = [...properties].sort((a, b) => {
    const av = a[sortKey] ?? 0
    const bv = b[sortKey] ?? 0
    return sortAsc ? av - bv : bv - av
  })

  const handleSort = (key) => {
    if (key === sortKey) setSortAsc(!sortAsc)
    else { setSortKey(key); setSortAsc(false) }
  }

  const SortHead = ({ k, children }) => (
    <th onClick={() => handleSort(k)} className="sortable">
      {children} {sortKey === k ? (sortAsc ? '▲' : '▼') : ''}
    </th>
  )

  return (
    <div className="card table-card">
      <h3>📋 All Properties (click headers to sort)</h3>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <SortHead k="score">Score</SortHead>
              <th>Title</th>
              <th>Area</th>
              <SortHead k="price">Price</SortHead>
              <SortHead k="price_m2">€/m²</SortHead>
              <th>DPE</th>
              <SortHead k="roi_5yr">5yr ROI</SortHead>
              <th>Verdict</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((p, i) => (
              <tr key={p.id || i} className={p.is_undervalued ? 'row-undervalued' : ''}>
                <td className="td-rank">{i + 1}</td>
                <td>
                  <span className="score-badge" style={{ background: scoreColor(p.score) }}>
                    {p.score?.toFixed(1)}
                  </span>
                </td>
                <td className="td-title">
                  {p.title?.slice(0, 40)}
                  {p.is_undervalued && <span className="undervalued-tag">★</span>}
                </td>
                <td>{p.arrondissement?.replace('Lyon ', '')}</td>
                <td className="td-num">{fmtEur(p.price)}</td>
                <td className="td-num">{fmtEur(p.price_m2)}</td>
                <td>
                  <span className="dpe-badge" style={{ background: dpeColor(p.dpe) }}>
                    {p.dpe}
                  </span>
                </td>
                <td className="td-num" style={{ color: p.roi_5yr > 0 ? '#059669' : '#dc2626' }}>
                  {p.roi_5yr?.toFixed(1)}%
                </td>
                <td>
                  <span className={`verdict verdict-${scoreVerdict(p.score).toLowerCase()}`}>
                    {scoreVerdict(p.score)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Top Undervalued ──────────────────────────────────────────────────────────
function UndervaluedSection({ properties }) {
  const undervalued = properties.filter((p) => p.is_undervalued).slice(0, 5)
  if (!undervalued.length) return null

  return (
    <div className="card undervalued-card">
      <h3>🏆 Top Undervalued Properties</h3>
      <div className="uv-grid">
        {undervalued.map((p, i) => (
          <div key={p.id || i} className="uv-item">
            <div className="uv-header">
              <span className="uv-rank">#{i + 1}</span>
              <span className="score-badge score-lg" style={{ background: scoreColor(p.score) }}>
                {p.score?.toFixed(1)}/10
              </span>
            </div>
            <h4 className="uv-title">{p.title}</h4>
            <div className="uv-details">
              <div className="uv-row">
                <span>💰 {fmtEur(p.price)}</span>
                <span>📐 {p.size}m²</span>
                <span className="dpe-badge" style={{ background: dpeColor(p.dpe) }}>{p.dpe}</span>
              </div>
              <div className="uv-row">
                <span>📍 {p.arrondissement}</span>
                <span>{fmtEur(p.price_m2)}/m²</span>
              </div>
              <div className="uv-metrics">
                <div className="uv-metric">
                  <span className="uv-metric-val" style={{ color: '#059669' }}>{fmtPct(p.price_vs_market_pct)}</span>
                  <span className="uv-metric-lbl">vs Market</span>
                </div>
                <div className="uv-metric">
                  <span className="uv-metric-val">{p.rental_yield_pct}%</span>
                  <span className="uv-metric-lbl">Yield</span>
                </div>
                <div className="uv-metric">
                  <span className="uv-metric-val" style={{ color: p.roi_5yr > 0 ? '#059669' : '#dc2626' }}>
                    {p.roi_5yr?.toFixed(1)}%
                  </span>
                  <span className="uv-metric-lbl">5yr ROI</span>
                </div>
              </div>
              {p.reno_cost > 0 && (
                <div className="uv-reno">
                  🔧 Renovation: {fmtEur(p.reno_cost)} → Post-reno value: {fmtEur(p.post_reno_value)} (gain: {fmtEur(p.capital_gain)})
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── Dashboard (Done) ─────────────────────────────────────────────────────────
function Dashboard({ data }) {
  return (
    <div className="dashboard">
      <StatCards summary={data.summary} />
      <div className="charts-row">
        <ArrondissementChart arrondissements={data.arrondissements} />
        <DpeChart properties={data.properties} />
      </div>
      <UndervaluedSection properties={data.properties} />
      <PropertiesTable properties={data.properties} />
    </div>
  )
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [phase, setPhase] = useState('idle')
  const [step, setStep] = useState(0)
  const [stepLabel, setStepLabel] = useState('')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)

  const startPipeline = async () => {
    setPhase('running')
    setStep(0)
    setError(null)
    try {
      await fetch(`${API}/run`, { method: 'POST' })
    } catch {
      setError('Cannot connect to server. Is server.py running?')
      setPhase('error')
    }
  }

  const reset = async () => {
    try { await fetch(`${API}/reset`, { method: 'POST' }) } catch {}
    setPhase('idle')
    setData(null)
    setError(null)
  }

  useEffect(() => {
    if (phase !== 'running') return

    const poll = async () => {
      try {
        const res = await fetch(`${API}/status`)
        const s = await res.json()
        setStep(s.step || 0)
        setStepLabel(s.step_label || '')

        if (s.status === 'done') {
          clearInterval(pollRef.current)
          const dRes = await fetch(`${API}/data`)
          const d = await dRes.json()
          setData(d)
          setPhase('done')
        } else if (s.status === 'error') {
          clearInterval(pollRef.current)
          setError(s.error || 'Unknown error')
          setPhase('error')
        }
      } catch { /* keep polling */ }
    }

    pollRef.current = setInterval(poll, 800)
    return () => clearInterval(pollRef.current)
  }, [phase])

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="logo">
            <span className="logo-icon">🏠</span>
            <h1>Nex-Lyon <span className="logo-accent">Analyzer</span></h1>
          </div>
          {phase === 'done' && (
            <div className="header-actions">
              {data?.sheets_url && (
                <a href={data.sheets_url} target="_blank" rel="noopener noreferrer" className="btn btn-sheets">
                  📊 Google Sheets
                </a>
              )}
              <a href={`${API}/report/download`} className="btn btn-download">
                📥 Report
              </a>
              <button onClick={reset} className="btn btn-outline">
                🔄 New Run
              </button>
            </div>
          )}
        </div>
      </header>

      <main className="main">
        {phase === 'idle' && <Hero onStart={startPipeline} />}
        {phase === 'running' && <Progress step={step} stepLabel={stepLabel} />}
        {phase === 'done' && data && <Dashboard data={data} />}
        {phase === 'error' && <ErrorView error={error} onRetry={startPipeline} />}
      </main>

      <footer className="footer">
        Nex-Lyon Real Estate Analyzer &middot; Data for informational purposes only
      </footer>
    </div>
  )
}
