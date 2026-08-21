import { useEffect, useState } from 'react'
import {
  approveUser,
  createParkingSpot,
  createReservation,
  createUser,
  createVehicle,
  deleteUser,
  exitParkingSession,
  getAlerts,
  getParkingSessions,
  getMyParkingSessions,
  getParkingSpots,
  getPayments,
  payPayment,
  getPendingUsers,
  getReservations,
  getUsers,
  getVehicles,
  rejectUser,
  resolveAlert,
  updateSpotStatus,
} from '../services/api'

function Head({ title, subtitle, onRefresh, loading }) {
  return <header className="page-head"><div><p className="eyebrow">SMARTPARK OPERATIONS</p><h1>{title}</h1><p className="muted">{subtitle}</p></div><button type="button" onClick={onRefresh} disabled={loading}>{loading ? 'Loading...' : '↻ Refresh data'}</button></header>
}

function ErrorMessage({ error }) {
  return error && <p className="error">{error}</p>
}

function StatusFilter({ value, onChange, options }) {
  return <select aria-label="Filter by status" value={value} onChange={event => onChange(event.target.value)}><option value="ALL">All statuses</option>{options.map(option => <option key={option} value={option}>{option}</option>)}</select>
}

function PaymentsAdminList() {
  const [items, setItems] = useState([]); const [status, setStatus] = useState('ALL'); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const load = async () => { setLoading(true); try { setItems(await getPayments()); setError('') } catch (err) { setError(err.message) } finally { setLoading(false) } }
  useEffect(() => { load() }, [])
  const shown = items.filter(item => status === 'ALL' || item.status === status)
  return <><Head title="Payments" subtitle="Review completed parking transactions and outstanding balances." onRefresh={load} loading={loading} /><ErrorMessage error={error} /><div className="filters"><StatusFilter value={status} onChange={setStatus} options={['PAID', 'PENDING', 'UNPAID']} /></div><div className="panel table-wrap"><table><thead><tr><th>ID</th><th>Session</th><th>Amount</th><th>Method</th><th>Status</th><th>Paid at</th></tr></thead><tbody>{shown.length ? shown.map(item => <tr key={item.id}><td>{item.id}</td><td>{item.parking_session_id}</td><td>{item.amount} DT</td><td>{item.payment_method || '—'}</td><td><span className={`status ${String(item.status).toLowerCase()}`}>{item.status}</span></td><td>{item.paid_at ? new Date(item.paid_at).toLocaleString() : '—'}</td></tr>) : <tr><td colSpan="6" className="empty">{items.length ? 'No payments match this status.' : 'No payments found in the database.'}</td></tr>}</tbody></table></div></>
}

export function PaymentsLive({ currentRole }) {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const load = async () => { setLoading(true); try { setItems(await getPayments()); setError('') } catch (err) { setError(err.message) } finally { setLoading(false) } }
  const pay = async id => { try { await payPayment(id); await load() } catch (err) { setError(err.message) } }
  useEffect(() => { load() }, [])

  return <><Head title="Payments" subtitle={currentRole === 'USER' ? 'Your completed parking visits and outstanding balances.' : 'Review completed parking transactions and outstanding balances.'} onRefresh={load} loading={loading} /><ErrorMessage error={error} /><div className="panel table-wrap"><table><thead><tr><th>ID</th><th>Parking</th><th>Amount</th><th>Status</th><th>Paid at</th>{currentRole === 'USER' && <th>Action</th>}</tr></thead><tbody>{items.length ? items.map(item => <tr key={item.id}><td>{item.id}</td><td>{item.parking_session_id ? `Session #${item.parking_session_id}` : `Reservation #${item.reservation_id}`}</td><td>{item.amount} DT</td><td><span className={`status ${String(item.status).toLowerCase()}`}>{item.status}</span></td><td>{item.paid_at ? new Date(item.paid_at).toLocaleString() : '—'}</td>{currentRole === 'USER' && <td>{item.status !== 'PAID' && <button type="button" className="small-button" onClick={() => pay(item.id)}>Pay now</button>}</td>}</tr>) : <tr><td colSpan={currentRole === 'USER' ? 6 : 5} className="empty">No payments found.</td></tr>}</tbody></table></div></>
}

export function AlertsLive() {
  const [items, setItems] = useState([]); const [status, setStatus] = useState('ALL'); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const load = async () => { setLoading(true); try { setItems(await getAlerts()); setError('') } catch (err) { setError(err.message) } finally { setLoading(false) } }
  const resolve = async id => { try { await resolveAlert(id); await load() } catch (err) { setError(err.message) } }
  useEffect(() => { load() }, [])
  const shown = items.filter(item => status === 'ALL' || item.status === status)
  return <><Head title="Alerts" subtitle="Review and resolve operational events that need attention." onRefresh={load} loading={loading} /><ErrorMessage error={error} /><div className="filters"><StatusFilter value={status} onChange={setStatus} options={['ACTIVE', 'RESOLVED']} /></div><div className="panel table-wrap"><table><thead><tr><th>ID</th><th>Type</th><th>Message</th><th>Severity</th><th>Status</th><th>Action</th></tr></thead><tbody>{shown.length ? shown.map(item => <tr key={item.id}><td>{item.id}</td><td>{item.alert_type}</td><td>{item.message}</td><td><span className={`status ${String(item.severity).toLowerCase()}`}>{item.severity}</span></td><td>{item.status}</td><td>{item.status === 'ACTIVE' && <button type="button" className="small-button" onClick={() => resolve(item.id)}>Resolve</button>}</td></tr>) : <tr><td colSpan="6" className="empty">{items.length ? 'No alerts match this status.' : 'No alerts found in the database.'}</td></tr>}</tbody></table></div></>
}

export function SpotsLive() {
  const [items, setItems] = useState([]); const [status, setStatus] = useState('ALL'); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const load = async () => { setLoading(true); try { setItems(await getParkingSpots()); setError('') } catch (err) { setError(err.message) } finally { setLoading(false) } }
  const cycle = async item => { const states = ['FREE', 'OCCUPIED', 'RESERVED', 'MAINTENANCE']; const next = states[(states.indexOf(item.status) + 1) % states.length]; try { await updateSpotStatus(item.id, next); await load() } catch (err) { setError(err.message) } }
  useEffect(() => { load() }, [])
  const shown = items.filter(item => status === 'ALL' || item.status === status)
  return <><Head title="Parking spots" subtitle="Monitor availability and update parking space status in real time." onRefresh={load} loading={loading} /><ErrorMessage error={error} /><div className="filters"><StatusFilter value={status} onChange={setStatus} options={['FREE', 'OCCUPIED', 'RESERVED', 'MAINTENANCE']} /></div><section className="spot-cards">{shown.map(item => <button type="button" className={`spot-card ${String(item.status).toLowerCase()}`} onClick={() => cycle(item)} key={item.id}><span>{item.zone} · {item.floor || 'Ground'}</span><strong>{item.number}</strong><span className={`status ${String(item.status).toLowerCase()}`}>{item.status}</span></button>)}</section>{!shown.length && <p className="muted">{items.length ? 'No spots match this status.' : 'No parking spots found.'}</p>}</>
}

export function SpotsManageLive({ currentRole }) {
  const [items, setItems] = useState([])
  const [status, setStatus] = useState('ALL')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ number: '', zone: '', floor: 'Ground', status: 'FREE' })
  const canCreate = ['SUPER_ADMIN', 'ADMIN'].includes(currentRole)

  const load = async () => {
    setLoading(true)
    try {
      setItems(await getParkingSpots())
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const cycle = async item => {
    const states = ['FREE', 'OCCUPIED', 'RESERVED', 'MAINTENANCE']
    const next = states[(states.indexOf(item.status) + 1) % states.length]
    try {
      await updateSpotStatus(item.id, next)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleCreate = async event => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      await createParkingSpot({
        number: form.number.trim().toUpperCase(),
        zone: form.zone.trim().toUpperCase(),
        floor: form.floor.trim() || null,
        status: form.status,
      })
      setForm({ number: '', zone: '', floor: 'Ground', status: 'FREE' })
      setFormOpen(false)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  useEffect(() => { load() }, [])
  const shown = items.filter(item => status === 'ALL' || item.status === status)

  return <>
    <Head title="Parking spots" subtitle="Monitor availability and update parking space status in real time." onRefresh={load} loading={loading} />
    <ErrorMessage error={error} />
    <div className="filters">
      <StatusFilter value={status} onChange={setStatus} options={['FREE', 'OCCUPIED', 'RESERVED', 'MAINTENANCE']} />
      {canCreate && <button type="button" className="small-button" onClick={() => setFormOpen(value => !value)}>{formOpen ? 'Close form' : 'Add spot'}</button>}
    </div>
    {formOpen && <div className="panel vehicle-form-panel"><form onSubmit={handleCreate} className="vehicle-form"><div className="vehicle-form-grid"><label>Spot number<input required placeholder="A-01" value={form.number} onChange={event => setForm({ ...form, number: event.target.value })} /></label><label>Zone<input required placeholder="A" value={form.zone} onChange={event => setForm({ ...form, zone: event.target.value })} /></label><label>Floor<input placeholder="Ground" value={form.floor} onChange={event => setForm({ ...form, floor: event.target.value })} /></label><label>Status<select value={form.status} onChange={event => setForm({ ...form, status: event.target.value })}><option>FREE</option><option>RESERVED</option><option>MAINTENANCE</option></select></label></div><button type="submit" className="small-button vehicle-submit" disabled={submitting}>{submitting ? 'Saving...' : 'Save spot'}</button></form></div>}
    <section className="spot-cards">{shown.map(item => <button type="button" className={`spot-card ${String(item.status).toLowerCase()}`} onClick={() => cycle(item)} key={item.id}><span>{item.zone} - {item.floor || 'Ground'}</span><strong>{item.number}</strong><span className={`status ${String(item.status).toLowerCase()}`}>{item.status}</span></button>)}</section>
    {!shown.length && <p className="muted">{items.length ? 'No spots match this status.' : 'No parking spots found. Add a spot, then keep it FREE so it appears in camera detection.'}</p>}
  </>
}

export function SessionsLive() {
  const [items, setItems] = useState([]); const [status, setStatus] = useState('ALL'); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const load = async () => { setLoading(true); try { setItems(await getParkingSessions()); setError('') } catch (err) { setError(err.message) } finally { setLoading(false) } }
  const exit = async id => { try { await exitParkingSession(id); await load() } catch (err) { setError(err.message) } }
  useEffect(() => { load() }, [])
  const shown = items.filter(item => status === 'ALL' || item.status === status)
  return <><Head title="Parking sessions" subtitle="Track active visits, completed sessions and vehicle exits." onRefresh={load} loading={loading} /><ErrorMessage error={error} /><div className="filters"><StatusFilter value={status} onChange={setStatus} options={['ACTIVE', 'COMPLETED']} /></div><div className="panel table-wrap"><table><thead><tr><th>ID</th><th>Vehicle</th><th>Spot</th><th>Entry</th><th>Duration</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead><tbody>{shown.length ? shown.map(item => <tr key={item.id}><td>{item.id}</td><td>{item.vehicle_id}</td><td>{item.parking_spot_id}</td><td>{item.entry_time ? new Date(item.entry_time).toLocaleString() : '—'}</td><td>{item.duration ?? '—'} min</td><td>{item.amount} DT</td><td>{item.status}</td><td>{item.status === 'ACTIVE' && <button type="button" className="small-button" onClick={() => exit(item.id)}>Exit vehicle</button>}</td></tr>) : <tr><td colSpan="8" className="empty">{items.length ? 'No sessions match this status.' : 'No sessions found.'}</td></tr>}</tbody></table></div></>
}

export function UsersLive({ currentRole }) {
  const [items, setItems] = useState([]); const [role, setRole] = useState('ALL'); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const [formOpen, setFormOpen] = useState(false)
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')
  const [form, setForm] = useState({ username: '', email: '', role: 'SECURITY' })

  const load = async () => { setLoading(true); try { setItems(await getUsers()); setError('') } catch (err) { setError(err.message) } finally { setLoading(false) } }

  const handleCreate = async event => {
    event.preventDefault()
    setSubmitting(true)
    setFormError('')
    setSuccessMessage('')

    try {
      const response = await createUser({
        username: form.username,
        email: form.email,
        role: form.role,
      })
      setForm({ username: '', email: '', role: 'SECURITY' })
      setSuccessMessage(response.email_status === 'sent'
        ? 'Account created. A password setup link was sent to the staff member email.'
        : response.email_status === 'smtp_not_configured'
          ? 'Account created, but SMTP is not configured. Add SMTP settings to backend/.env.'
          : 'Account created, but the password setup email could not be sent. Check SMTP settings.')
      setTimeout(() => setFormOpen(false), 2000)
      await load()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async item => {
    if (!window.confirm(`Delete user ${item.username}? This action cannot be undone.`)) return
    setError('')
    try {
      await deleteUser(item.id)
      setSuccessMessage(`User ${item.username} deleted successfully.`)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => { load() }, [])
  const shown = items.filter(item => role === 'ALL' || item.role === role)

  return <><Head title="Users" subtitle="Manage team members, operators and access permissions." onRefresh={load} loading={loading} /><ErrorMessage error={error || formError} />{successMessage && <div style={{ padding: '0.75rem', marginBottom: '1rem', background: '#e8f5e9', borderRadius: '4px', color: '#2e7d32' }}>{successMessage}</div>}<div className="filters"><StatusFilter value={role} onChange={setRole} options={['SUPER_ADMIN', 'ADMIN', 'OPERATOR', 'SECURITY', 'USER']} /><button type="button" className="small-button" onClick={() => setFormOpen(value => !value)}>{formOpen ? 'Close form' : 'Add staff'}</button></div>{formOpen && <div className="panel" style={{ marginBottom: '1rem', padding: '1rem' }}><form onSubmit={handleCreate} style={{ display: 'grid', gap: '0.75rem' }}><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}><label style={{ display: 'grid', gap: '0.35rem' }}>Username<input required minLength="3" value={form.username} onChange={event => setForm({ ...form, username: event.target.value })} /></label><label style={{ display: 'grid', gap: '0.35rem' }}>Email<input required type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })} /></label><label style={{ display: 'grid', gap: '0.35rem' }}>Role<select value={form.role} onChange={event => setForm({ ...form, role: event.target.value })}><option value="SECURITY">SECURITY</option><option value="OPERATOR">OPERATOR</option><option value="ADMIN">ADMIN</option></select></label></div><p style={{ fontSize: '0.85rem', color: '#666', margin: '0.5rem 0 0 0' }}>The staff member will receive a password reset link via email.</p><button type="submit" className="small-button" disabled={submitting}>{submitting ? 'Creating...' : 'Create account'}</button></form></div>}<div className="panel table-wrap"><table><thead><tr><th>ID</th><th>Username</th><th>Email</th><th>Role</th><th>Status</th>{currentRole === 'SUPER_ADMIN' && <th>Action</th>}</tr></thead><tbody>{shown.length ? shown.map(item => <tr key={item.id}><td>{item.id}</td><td><strong>{item.username}</strong></td><td>{item.email}</td><td>{item.role}</td><td>{item.status || (item.is_active ? 'ACTIVE' : 'INACTIVE')}</td>{currentRole === 'SUPER_ADMIN' && <td><button type="button" className="small-button secondary" onClick={() => handleDelete(item)}>Delete</button></td>}</tr>) : <tr><td colSpan={currentRole === 'SUPER_ADMIN' ? 6 : 5} className="empty">{items.length ? 'No users match this role.' : 'No users found.'}</td></tr>}</tbody></table></div></>
}

export function PendingAccountsLive({ currentRole }) {
  const [items, setItems] = useState([]); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      setItems(await getPendingUsers())
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleAction = async (id, action) => {
    try {
      if (action === 'approve') await approveUser(id)
      if (action === 'reject') await rejectUser(id)
      await load()
    } catch (err) {
      setError(err.message)
    }
  }

  return <><Head title="Pending accounts" subtitle="Review staff account requests before activation." onRefresh={load} loading={loading} /><ErrorMessage error={error} /><div className="panel table-wrap"><table><thead><tr><th>ID</th><th>Username</th><th>Email</th><th>Role</th><th>Status</th>{currentRole === 'SUPER_ADMIN' && <th>Actions</th>}</tr></thead><tbody>{items.length ? items.map(item => <tr key={item.id}><td>{item.id}</td><td><strong>{item.username}</strong></td><td>{item.email}</td><td>{item.role}</td><td>{item.status}</td>{currentRole === 'SUPER_ADMIN' && <td><div className="inline-actions"><button type="button" className="small-button" onClick={() => handleAction(item.id, 'approve')}>Approve</button><button type="button" className="small-button secondary" onClick={() => handleAction(item.id, 'reject')}>Reject</button></div></td>}</tr>) : <tr><td colSpan={currentRole === 'SUPER_ADMIN' ? 6 : 5} className="empty">No pending accounts.</td></tr>}</tbody></table></div></>
}

export function VehiclesLive({ currentRole }) {
  const [items, setItems] = useState([])
  const [status, setStatus] = useState('ALL')
  const [query, setQuery] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState({ plate_number: '', owner_name: '', brand: '', model: '', status: 'VISITOR' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const load = async () => {
    setLoading(true)
    try { setItems(await getVehicles()); setError('') } catch (err) { setError(err.message) } finally { setLoading(false) }
  }

  const handleCreate = async event => {
    event.preventDefault()
    setSubmitting(true)
    try {
      await createVehicle(form)
      setForm({ plate_number: '', owner_name: '', brand: '', model: '', status: 'VISITOR' })
      setFormOpen(false)
      await load()
    } catch (err) { setError(err.message) } finally { setSubmitting(false) }
  }

  useEffect(() => { load() }, [])
  const normalizedQuery = query.trim().toLowerCase()
  const shown = items.filter(item => {
    const matchesStatus = status === 'ALL' || item.status === status
    const searchable = `${item.plate_number} ${item.owner_name || ''} ${item.brand || ''} ${item.model || ''}`.toLowerCase()
    return matchesStatus && searchable.includes(normalizedQuery)
  })

  return <><Head title="Vehicles" subtitle="Manage vehicles permitted to access your parking facility." onRefresh={load} loading={loading} /><ErrorMessage error={error} /><div className="filters"><input aria-label="Search vehicles" placeholder="Search plate, owner or brand" value={query} onChange={event => setQuery(event.target.value)} /><StatusFilter value={status} onChange={setStatus} options={['AUTHORIZED', 'VISITOR', 'VIP', 'BLACKLISTED']} />{['SUPER_ADMIN', 'ADMIN', 'OPERATOR'].includes(currentRole) && <button type="button" className="small-button" onClick={() => setFormOpen(value => !value)}>{formOpen ? 'Close form' : 'Add vehicle'}</button>}</div>{formOpen && <div className="panel vehicle-form-panel"><form onSubmit={handleCreate} className="vehicle-form"><div className="vehicle-form-grid"><label>Plate number<input required value={form.plate_number} onChange={event => setForm({ ...form, plate_number: event.target.value.toUpperCase() })} /></label><label>Owner name<input value={form.owner_name} onChange={event => setForm({ ...form, owner_name: event.target.value })} /></label><label>Brand<input value={form.brand} onChange={event => setForm({ ...form, brand: event.target.value })} /></label><label>Model<input value={form.model} onChange={event => setForm({ ...form, model: event.target.value })} /></label><label>Status<select value={form.status} onChange={event => setForm({ ...form, status: event.target.value })}><option>VISITOR</option><option>AUTHORIZED</option><option>VIP</option><option>BLACKLISTED</option></select></label></div><button type="submit" className="small-button vehicle-submit" disabled={submitting}>{submitting ? 'Saving...' : 'Save vehicle'}</button></form></div>}<div className="panel table-wrap"><table><thead><tr><th>ID</th><th>Plate</th><th>Owner</th><th>Vehicle</th><th>Status</th></tr></thead><tbody>{shown.length ? shown.map(item => <tr key={item.id}><td>{item.id}</td><td><strong>{item.plate_number}</strong></td><td>{item.owner_name || '—'}</td><td>{[item.brand, item.model].filter(Boolean).join(' ') || '—'}</td><td><span className={`status ${String(item.status).toLowerCase()}`}>{item.status}</span></td></tr>) : <tr><td colSpan="5" className="empty">{items.length ? 'No vehicles match your filters.' : 'No vehicles found in the database.'}</td></tr>}</tbody></table></div></>
}

export function ReservationsLive() {
  const [items, setItems] = useState([]); const [status, setStatus] = useState('ALL'); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const load = async () => { setLoading(true); try { setItems(await getReservations()); setError('') } catch (err) { setError(err.message) } finally { setLoading(false) } }
  useEffect(() => { load() }, [])
  const shown = items.filter(item => status === 'ALL' || item.status === status)
  return <><Head title="Reservations" subtitle="Plan parking allocations and manage upcoming vehicle arrivals." onRefresh={load} loading={loading} /><ErrorMessage error={error} /><div className="filters"><StatusFilter value={status} onChange={setStatus} options={['PENDING', 'CONFIRMED', 'CANCELLED', 'COMPLETED']} /></div><div className="panel table-wrap"><table><thead><tr><th>ID</th><th>User</th><th>Vehicle</th><th>Spot</th><th>Start</th><th>End</th><th>Status</th></tr></thead><tbody>{shown.length ? shown.map(item => <tr key={item.id}><td>{item.id}</td><td>{item.user_id}</td><td>{item.vehicle_id}</td><td>{item.parking_spot_id}</td><td>{new Date(item.start_time).toLocaleString()}</td><td>{new Date(item.end_time).toLocaleString()}</td><td>{item.status}</td></tr>) : <tr><td colSpan="7" className="empty">{items.length ? 'No reservations match this status.' : 'No reservations found.'}</td></tr>}</tbody></table></div></>
}
