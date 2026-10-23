import { useEffect, useMemo, useRef, useState } from 'react'
import {
  Activity, ArrowDownRight, ArrowUpRight, BadgeCheck, BarChart3, Bot, ChevronDown,
  CircleHelp, FileUp, Filter, Layers3, Menu, Search, ShieldAlert, Sparkles,
  WalletCards, X,
} from 'lucide-react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

type Transaction = {
  id: number; supplier: string; description: string; amount: number; invoice_id: string
  transaction_date: string; category: string; category_confidence: number
  is_duplicate: boolean; duplicate_reason: string
}
type Dashboard = {
  kpis: { total_spend: number; transaction_count: number; duplicate_count: number; needs_review: number; data_quality_score: number }
  categories: { name: string; value: number }[]
  top_suppliers: { name: string; value: number }[]
  recent_transactions: Transaction[]
}
type PolicySource = { source: string; section: string; text: string; score: number }

const palette = ['#c6f36b', '#67d9bb', '#83a7ff', '#fac675', '#c4a4ff', '#f18d9b']
const currency = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })
const blankDashboard: Dashboard = {
  kpis: { total_spend: 0, transaction_count: 0, duplicate_count: 0, needs_review: 0, data_quality_score: 0 },
  categories: [], top_suppliers: [], recent_transactions: [],
}

function App() {
  const [dashboard, setDashboard] = useState<Dashboard>(blankDashboard)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [query, setQuery] = useState('')
  const [duplicatesOnly, setDuplicatesOnly] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [question, setQuestion] = useState('What checks are required for duplicate invoices?')
  const [policyAnswer, setPolicyAnswer] = useState('')
  const [sources, setSources] = useState<PolicySource[]>([])
  const [asking, setAsking] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  async function loadDashboard() {
    try {
      const response = await fetch('/api/dashboard')
      if (!response.ok) throw new Error('API is unavailable')
      setDashboard(await response.json())
    } catch {
      setNotice('Could not connect to the API. Start the services with docker compose up --build.')
    }
  }

  async function loadTransactions(search = query, onlyDuplicates = duplicatesOnly) {
    const params = new URLSearchParams({ limit: '100' })
    if (search.trim()) params.set('q', search.trim())
    if (onlyDuplicates) params.set('duplicates_only', 'true')
    try {
      const response = await fetch(`/api/transactions?${params}`)
      if (response.ok) setTransactions(await response.json())
    } catch { /* The dashboard displays the connection message. */ }
  }

  useEffect(() => { void loadDashboard(); void loadTransactions() }, [])
  useEffect(() => {
    const timer = window.setTimeout(() => { void loadTransactions(query, duplicatesOnly) }, 220)
    return () => window.clearTimeout(timer)
  }, [query, duplicatesOnly])

  async function uploadFile(file?: File) {
    if (!file) return
    setBusy(true); setNotice('')
    const form = new FormData(); form.append('file', file)
    try {
      const response = await fetch('/api/import', { method: 'POST', body: form })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || 'Import failed')
      setNotice(`${body.message} ${body.duplicates} likely duplicate(s) flagged.`)
      await loadDashboard(); await loadTransactions()
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Import failed')
    } finally {
      setBusy(false)
      if (fileInput.current) fileInput.current.value = ''
    }
  }

  async function askPolicy(event: React.FormEvent) {
    event.preventDefault(); setAsking(true); setPolicyAnswer(''); setSources([])
    try {
      const response = await fetch('/api/policies/ask', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question }),
      })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || 'Policy search failed')
      setPolicyAnswer(body.answer); setSources(body.sources)
    } catch (error) {
      setPolicyAnswer(error instanceof Error ? error.message : 'Policy search failed')
    } finally { setAsking(false) }
  }

  const categoryCount = dashboard.categories.length
  const avgConfidence = useMemo(() => {
    if (!dashboard.recent_transactions.length) return 0
    return Math.round(dashboard.recent_transactions.reduce((sum, row) => sum + row.category_confidence, 0) / dashboard.recent_transactions.length * 100)
  }, [dashboard.recent_transactions])

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand"><span className="brand-mark"><Layers3 size={19} /></span><span>procure<span className="brand-light">lens</span></span><button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={18} /></button></div>
        <div className="workspace-label">WORKSPACE</div>
        <button className="workspace"><span className="workspace-avatar">A</span><span><b>Acme Corporation</b><small>Procurement team</small></span><ChevronDown size={15} /></button>
        <div className="nav-label">OVERVIEW</div>
        <nav>
          <a className="nav-item active" href="#overview"><BarChart3 size={17} />Spend overview</a>
          <a className="nav-item" href="#transactions"><WalletCards size={17} />Transactions<span className="nav-count">{dashboard.kpis.transaction_count}</span></a>
          <a className="nav-item" href="#quality"><ShieldAlert size={17} />Data quality</a>
          <a className="nav-item" href="#assistant"><Bot size={17} />Policy assistant<span className="new-pill">AI</span></a>
        </nav>
        <div className="sidebar-bottom"><div className="sidebar-help"><span className="help-icon"><CircleHelp size={17} /></span><span><b>Need a hand?</b><small>Explore the product guide</small></span></div><div className="profile"><div className="profile-avatar">DA</div><div><b>Demo Analyst</b><small>Analyst workspace</small></div><ChevronDown size={15} /></div></div>
      </aside>

      {mobileOpen && <button className="backdrop" onClick={() => setMobileOpen(false)} aria-label="Close navigation" />}

      <main className="main-content" id="overview">
        <header className="topbar"><button className="menu-toggle" onClick={() => setMobileOpen(true)} aria-label="Open menu"><Menu size={20} /></button><div className="breadcrumb">Workspace <span>/</span> <b>Spend overview</b></div><div className="topbar-right"><span className="live-dot" />Data synced just now <button className="icon-button" aria-label="Help"><CircleHelp size={18} /></button><div className="top-avatar">DA</div></div></header>
        <div className="page-wrap">
          <section className="page-heading"><div><div className="eyebrow"><span className="eyebrow-dot" />PROCUREMENT INTELLIGENCE</div><h1>Spend overview</h1><p>A clear view of spend, suppliers, and the data behind every decision.</p></div><div className="heading-actions"><button className="date-select" type="button">All imported data</button><button className="primary-button" onClick={() => fileInput.current?.click()} disabled={busy}><FileUp size={16} />{busy ? 'Importing…' : 'Import transactions'}</button><input ref={fileInput} type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" hidden onChange={(e) => void uploadFile(e.target.files?.[0])} /></div></section>

          {notice && <div className={`notice ${notice.includes('Could not connect') ? 'notice-error' : ''}`} role="status">{notice}<button onClick={() => setNotice('')} aria-label="Dismiss"><X size={16} /></button></div>}

          <section className="kpi-grid" aria-label="Spend key performance indicators">
            <Kpi icon={<WalletCards size={17} />} label="Total spend" value={currency.format(dashboard.kpis.total_spend)} note="Sum of imported transactions" trend="Current total" />
            <Kpi icon={<Activity size={17} />} label="Transactions" value={dashboard.kpis.transaction_count.toLocaleString('en-IN')} note="Rows in this workspace" trend="Imported" />
            <Kpi icon={<ShieldAlert size={17} />} label="Potential duplicates" value={dashboard.kpis.duplicate_count.toString()} note="Needs a quick review" trend={dashboard.kpis.duplicate_count ? 'Review' : 'Clear'} />
            <Kpi icon={<BadgeCheck size={17} />} label="Data quality" value={`${dashboard.kpis.data_quality_score}%`} note="Duplicate and review checks" trend={`${avgConfidence}% avg. ML confidence`} />
          </section>

          <section className="analysis-grid">
            <article className="panel category-panel"><div className="panel-head"><div><div className="section-kicker">SPEND MIX</div><h2>Spend by category</h2></div><button className="more-button">This month <ChevronDown size={14} /></button></div><div className="chart-row"><div className="donut-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={dashboard.categories} dataKey="value" nameKey="name" innerRadius="69%" outerRadius="92%" paddingAngle={3} stroke="none">{dashboard.categories.map((entry, index) => <Cell key={entry.name} fill={palette[index % palette.length]} />)}</Pie><Tooltip formatter={(value) => currency.format(Number(value))} contentStyle={{ background: '#1e2824', border: '1px solid #34413a', borderRadius: 12, color: '#f2f5ed' }} /></PieChart></ResponsiveContainer><div className="donut-center"><span>{categoryCount}</span><small>categories</small></div></div><div className="legend-list">{dashboard.categories.map((item, index) => <div className="legend-item" key={item.name}><span className="legend-label"><i style={{ background: palette[index % palette.length] }} />{item.name}</span><b>{currency.format(item.value)}</b></div>)}</div></div><div className="panel-foot"><span><span className="mini-dot" />Categorized spend</span><b>{currency.format(dashboard.kpis.total_spend)} total</b></div></article>

            <article className="panel quality-panel" id="quality"><div className="panel-head"><div><div className="section-kicker">DATA HEALTH</div><h2>Quality signals</h2></div><button className="round-icon" aria-label="More quality details"><ArrowUpRight size={16} /></button></div><div className="quality-score"><div className="score-ring" style={{ '--score': `${dashboard.kpis.data_quality_score * 3.6}deg` } as React.CSSProperties}><div><strong>{dashboard.kpis.data_quality_score}</strong><span>/100</span></div></div><div><b>{dashboard.kpis.data_quality_score >= 90 ? 'Looking healthy' : 'Review recommended'}</b><p>Based on duplicate and classification checks</p></div></div><div className="quality-items"><div className="quality-row"><span><i className="signal signal-green" />Duplicate invoices</span><b>{dashboard.kpis.duplicate_count} flagged</b></div><div className="quality-row"><span><i className="signal signal-amber" />Low-confidence categories</span><b>{dashboard.kpis.needs_review} to review</b></div><div className="quality-row"><span><i className="signal signal-blue" />Classification coverage</span><b>{avgConfidence}% avg. confidence</b></div></div><a className="text-link" href="#transactions">Review flagged transactions <ArrowDownRight size={15} /></a></article>
          </section>

          <section className="panel transactions-panel" id="transactions"><div className="panel-head transaction-head"><div><div className="section-kicker">RECORDS</div><h2>Recent transactions <span className="record-count">{transactions.length}</span></h2></div><div className="table-tools"><label className="search-box"><Search size={15} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search transactions" /></label><button className={`filter-button ${duplicatesOnly ? 'filter-active' : ''}`} onClick={() => setDuplicatesOnly(!duplicatesOnly)}><Filter size={15} />{duplicatesOnly ? 'Duplicates' : 'Filter'}</button></div></div><div className="table-scroll"><table><thead><tr><th>SUPPLIER</th><th>DESCRIPTION</th><th>CATEGORY</th><th>INVOICE</th><th>DATE</th><th>AMOUNT</th><th>STATUS</th></tr></thead><tbody>{transactions.map((row) => <tr key={row.id}><td><span className="supplier-cell"><span className="supplier-avatar">{row.supplier.slice(0, 1).toUpperCase()}</span><b>{row.supplier}</b></span></td><td className="description-cell">{row.description}</td><td><span className="category-chip">{row.category}</span></td><td className="mono">{row.invoice_id}</td><td className="date-cell">{new Date(`${row.transaction_date}T00:00:00`).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })}</td><td className="amount-cell">{currency.format(row.amount)}</td><td>{row.is_duplicate ? <span className="status status-review"><i />Duplicate</span> : <span className="status status-clean"><i />Clear</span>}</td></tr>)}{transactions.length === 0 && <tr><td colSpan={7} className="empty-state">No transactions found. Import a CSV to get started.</td></tr>}</tbody></table></div><div className="table-footer"><span>Showing <b>{transactions.length}</b> of {dashboard.kpis.transaction_count} records</span><button onClick={() => { setDuplicatesOnly(false); setQuery('') }}>Clear filters <X size={13} /></button></div></section>

          <section className="assistant-panel" id="assistant"><div className="assistant-copy"><div className="assistant-icon"><Sparkles size={18} /></div><div className="section-kicker">POLICY COPILOT <span className="beta-tag">BETA</span></div><h2>Ask your procurement policies.</h2><p>Get answers grounded in your policy library, with the source passages attached.</p><div className="assistant-prompt"><span className="prompt-dot" />Try: “What approvals are needed above ₹50,000?”</div></div><form className="assistant-form" onSubmit={(e) => void askPolicy(e)}><label htmlFor="policy-question">Ask a policy question</label><div className="question-input"><input id="policy-question" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about approvals, invoices, suppliers…" /><button aria-label="Search policies" disabled={asking}><Sparkles size={16} /></button></div><div className="answer-area">{asking ? <span className="answer-muted">Searching policy passages…</span> : policyAnswer ? <><p>{policyAnswer}</p>{sources.length > 0 && <div className="source-list">{sources.map((source) => <article className="source-card" key={`${source.source}-${source.section}`}><div><b>{source.source}</b><span>{source.section} · match {Math.round(source.score * 100)}%</span></div><p>“{source.text}”</p></article>)}</div>}</> : <span className="answer-muted">Answers include matching source and section.</span>}</div></form></section>

          <footer className="footer"><span>ProcureLens <span className="footer-sep">·</span> Spend intelligence, made clear.</span><span>Built with FastAPI, scikit-learn, PostgreSQL & React</span></footer>
        </div>
      </main>
    </div>
  )
}

function Kpi({ icon, label, value, note, trend, up }: { icon: React.ReactNode; label: string; value: string; note: string; trend: string; up?: boolean }) {
  return <article className="kpi-card"><div className="kpi-top"><span className="kpi-icon">{icon}</span><span className={`kpi-trend ${up ? 'trend-up' : ''}`}>{up && <ArrowUpRight size={13} />}{trend}</span></div><div className="kpi-label">{label}</div><div className="kpi-value">{value}</div><div className="kpi-note">{note}</div></article>
}

export default App
