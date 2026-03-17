import { useState, useEffect, useCallback, useRef } from 'react'
import MapView from './components/Map/MapView'
import LeadList from './components/Leads/LeadList'
import LeadDetail from './components/Leads/LeadDetail'
import ScraperPanel from './components/Scraper/ScraperPanel'
import { getMapPins, getStats } from './api/client'

export default function App() {
  const [view, setView] = useState('map')       // 'map' | 'scraper'
  const [pins, setPins] = useState([])
  const [stats, setStats] = useState(null)
  const [selectedLead, setSelectedLead] = useState(null)   // { id, lat, lng, ... }
  const [detailOpen, setDetailOpen] = useState(false)
  const [toast, setToast] = useState(null)
  const toastTimer = useRef(null)

  const loadPins = useCallback(() => {
    getMapPins().then(setPins).catch(() => {})
  }, [])

  const loadStats = useCallback(() => {
    getStats().then(setStats).catch(() => {})
  }, [])

  useEffect(() => {
    loadPins()
    loadStats()
  }, [loadPins, loadStats])

  function showToast(message, type = 'success') {
    clearTimeout(toastTimer.current)
    setToast({ message, type })
    toastTimer.current = setTimeout(() => setToast(null), 3500)
  }

  function handleSelectLead(lead) {
    setSelectedLead(lead)
    setDetailOpen(true)
  }

  function handleCloseDetail() {
    setDetailOpen(false)
    setTimeout(() => setSelectedLead(null), 250) // wait for animation
  }

  function handleUpdated() {
    loadPins()
    loadStats()
  }

  function handleDeleted() {
    loadPins()
    loadStats()
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <span className="header-logo">GAVA Recruitment</span>

        <nav className="header-nav">
          <button
            className={`nav-btn${view === 'map' ? ' active' : ''}`}
            onClick={() => setView('map')}
          >
            Map &amp; Leads
          </button>
          <button
            className={`nav-btn${view === 'scraper' ? ' active' : ''}`}
            onClick={() => setView('scraper')}
          >
            Scraper
          </button>
        </nav>

        {stats && (
          <div className="header-stats">
            <div className="stat-pill"><strong>{stats.total}</strong> Leads</div>
            {stats.by_status?.new > 0 &&
              <div className="stat-pill" style={{ color: 'var(--new)' }}>
                <strong>{stats.by_status.new}</strong> New
              </div>}
            {stats.by_status?.contacted > 0 &&
              <div className="stat-pill" style={{ color: 'var(--contacted)' }}>
                <strong>{stats.by_status.contacted}</strong> Contacted
              </div>}
            {stats.by_status?.converted > 0 &&
              <div className="stat-pill" style={{ color: 'var(--converted)' }}>
                <strong>{stats.by_status.converted}</strong> Converted
              </div>}
          </div>
        )}
      </header>

      {/* Body */}
      <div className="app-body">
        {view === 'map' ? (
          <>
            {/* Sidebar */}
            <aside className="sidebar">
              <LeadList
                selectedId={selectedLead?.id}
                onSelect={handleSelectLead}
              />
            </aside>

            {/* Map */}
            <main className="main-panel">
              <MapView
                pins={pins}
                onSelectPin={handleSelectLead}
                selectedPin={selectedLead}
              />

              {/* Detail drawer */}
              <div className={`detail-panel${detailOpen ? ' open' : ''}`}>
                {selectedLead && (
                  <LeadDetail
                    leadId={selectedLead.id}
                    onClose={handleCloseDetail}
                    onDeleted={handleDeleted}
                    onUpdated={handleUpdated}
                    showToast={showToast}
                  />
                )}
              </div>
            </main>
          </>
        ) : (
          <main className="main-panel" style={{ overflow: 'auto' }}>
            <ScraperPanel showToast={showToast} />
          </main>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className={`toast ${toast.type}`} onClick={() => setToast(null)}>
          {toast.message}
        </div>
      )}
    </div>
  )
}
