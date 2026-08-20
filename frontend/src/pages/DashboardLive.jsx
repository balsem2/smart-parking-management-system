import { useEffect, useState } from 'react'
import StatCard from '../components/StatCard'
import { getDashboardOverview, getOccupancy, getParkingSpots, WS_URL } from '../services/api'

function statusClass(status) {
  return String(status || 'unknown').toLowerCase()
}

export default function DashboardLive() {
  const [overview, setOverview] = useState(null)
  const [occupancy, setOccupancy] = useState(null)
  const [spots, setSpots] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function refresh() {
    setLoading(true)
    try {
      const [overviewData, occupancyData, spotsData] = await Promise.all([
        getDashboardOverview(), getOccupancy(), getParkingSpots(),
      ])
      setOverview(overviewData)
      setOccupancy(occupancyData)
      setSpots(spotsData)
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
    const socket = new WebSocket(WS_URL)
    socket.onmessage = refresh
    return () => socket.close()
  }, [])

  const rate = occupancy?.occupancy_rate_percent || 0
  const cards = [
    ['Total parking spots', occupancy?.total_spots || 0, 'Current facility capacity', ''],
    ['Available spots', occupancy?.available_spots || 0, `${rate}% occupancy`, 'free'],
    ['Occupied spots', occupancy?.occupied_spots || 0, `${rate}% of capacity`, 'occupied'],
    ['Active sessions', overview?.active_sessions || 0, 'Currently in progress', ''],
    ["Today's revenue", `${overview?.revenue || 0} DT`, 'Paid parking revenue', 'revenue'],
  ]

  return <>
    <header className="page-head"><div><p className="eyebrow">OPERATIONS OVERVIEW</p><h1>Good morning, Balsem.</h1><p className="muted">Here is what’s happening at SmartPark Central today.</p></div><button type="button" onClick={refresh} disabled={loading}>{loading ? 'Loading...' : '↻ Refresh data'}</button></header>
    {error && <p className="error">{error}</p>}
    <section className="cards">{cards.map(([label, value, note, tone]) => <StatCard key={label} label={label} value={value} note={note} tone={tone} />)}</section>
    <section className="dashboard-grid"><article className="panel occupancy"><div className="panel-title"><div><p className="eyebrow">LIVE CAPACITY</p><h2>Parking occupancy</h2></div><span className="live-label"><i />LIVE</span></div><div className="occupancy-body"><div className="ring"><strong>{rate}%</strong><span>occupied</span></div><div className="occupancy-legend"><p><i className="dot free" />{occupancy?.available_spots || 0} <span>Available spots</span></p><p><i className="dot occupied" />{occupancy?.occupied_spots || 0} <span>Occupied spots</span></p></div></div><div className="duration"><span>Average parking duration</span><strong>{overview?.average_parking_duration_minutes || 0} min</strong><span>Peak time</span><strong>{overview?.peak_hour || '—'}</strong></div></article><article className="panel realtime"><div className="panel-title"><div><p className="eyebrow">SYSTEM STATUS</p><h2>Real-time status</h2></div></div><div className="connected"><span><i />Connected</span><strong>Live updates are active</strong><p>Parking events are syncing instantly.</p></div><div className="system-line"><span>API connection</span><b>Operational</b></div></article></section>
    <section className="dashboard-grid lower"><article className="panel"><div className="panel-title"><div><p className="eyebrow">PARKING MAP</p><h2>Spot availability</h2></div></div><div className="dashboard-spots">{spots.map(spot => <div className={`dashboard-spot ${statusClass(spot.status)}`} key={spot.id}><strong>{spot.number}</strong><span>{spot.status}</span></div>)}</div>{!spots.length && <p className="muted">No parking spots found.</p>}</article></section>
  </>
}