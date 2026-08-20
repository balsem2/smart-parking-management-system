import { useState } from 'react'
import { login } from '../services/api'

export default function Login({ onLogin, onRegister }) {
  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const submit = async (event) => { event.preventDefault(); try { const data = await login(form); localStorage.setItem('smartpark_token', data.access_token); onLogin() } catch (err) { setError(err.message) } }
  return <main className="auth"><section className="auth-card"><div className="auth-brand">SP</div><p className="eyebrow">SMARTPARK AI</p><h1>Welcome back</h1><p>Sign in to manage your parking operations.</p><form onSubmit={submit}><label>Email<input required type="email" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></label><label>Password<input required type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>{error && <small className="error">{error}</small>}<button>Sign in</button></form><p className="switch">New to SmartPark? <button type="button" onClick={onRegister}>Create an account</button></p></section></main>
}
