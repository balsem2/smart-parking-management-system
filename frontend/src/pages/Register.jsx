import { useState } from 'react'
import { register } from '../services/api'

export default function Register({ onLogin }) {
  const [form, setForm] = useState({ full_name: '', national_id: '', plate_number: '', username: '', email: '', password: '' })
  const [error, setError] = useState('')
  const submit = async (event) => { event.preventDefault(); try { await register(form); onLogin() } catch (err) { setError(err.message) } }
  return <main className="auth"><section className="auth-card"><div className="auth-brand">SP</div><p className="eyebrow">SMARTPARK AI</p><h1>Create your parking account</h1><p>Register your vehicle once and it will be recognized automatically.</p><form onSubmit={submit}><label>Full name<input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label><label>CIN<input required value={form.national_id} onChange={(e) => setForm({ ...form, national_id: e.target.value.toUpperCase() })} /></label><label>Vehicle plate<input required value={form.plate_number} onChange={(e) => setForm({ ...form, plate_number: e.target.value.toUpperCase() })} /></label><label>Username<input required minLength="3" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></label><label>Email<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label><label>Password<input required type="password" minLength="8" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>{error && <small className="error">{error}</small>}<button>Create account</button></form><p className="switch">Already have an account? <button type="button" onClick={onLogin}>Sign in</button></p></section></main>
}
