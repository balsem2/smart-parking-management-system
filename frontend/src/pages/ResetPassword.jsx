import { useState, useEffect } from 'react'
import { resetPassword } from '../services/api'
import '../auth.css'

export default function ResetPassword({ onReset }) {
  const [token, setToken] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    setToken(params.get('token') || '')
  }, [])

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    if (!token) return setError('Invalid or missing reset token')
    if (password.length < 8) return setError('Password must be at least 8 characters')
    if (password !== confirmPassword) return setError('Passwords do not match')

    setLoading(true)
    try {
      await resetPassword({ token, password })
      setSuccess(true)
      setTimeout(() => onReset?.(), 2000)
    } catch (err) {
      setError(err.message || 'Failed to reset password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth">
      <section className="auth-card">
        <div className="auth-brand">SP</div>
        <p className="eyebrow">SMARTPARK AI</p>
        <h1>Reset Password</h1>
        {!token && <p className="error">Invalid or missing reset token. Please check your password reset link.</p>}
        {success && <p>Password reset successfully! Redirecting to login...</p>}
        {!success && token && (
          <form onSubmit={handleSubmit}>
            <label>New Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} disabled={loading} required /></label>
            <label>Confirm Password<input type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} disabled={loading} required /></label>
            {error && <small className="error">{error}</small>}
            <button type="submit" disabled={loading}>{loading ? 'Resetting...' : 'Reset Password'}</button>
          </form>
        )}
        {!token && <button type="button" onClick={() => onReset?.()}>Back to Login</button>}
      </section>
    </main>
  )
}
