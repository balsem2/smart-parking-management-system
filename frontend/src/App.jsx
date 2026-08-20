import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import { AnalyticsPage, SettingsPage } from './pages/OperationsPages'
import Login from './pages/Login'
import Register from './pages/Register'
import { AlertsLive, PaymentsLive, PendingAccountsLive, ReservationsLive, SessionsLive, SpotsLive, UsersLive, VehiclesLive } from './pages/OperationsLive'
import ResetPassword from './pages/ResetPassword'
import { getMe } from './services/api'
import './App.css'
import './auth.css'

function decodeToken(token) {
  if (!token) return null
  try {
    const payload = token.split('.')[1]
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const raw = atob(normalized)
    return JSON.parse(raw)
  } catch {
    return null
  }
}

const MENU_BY_ROLE = {
  SUPER_ADMIN: ['Dashboard', 'Vehicles', 'Parking Spots', 'Parking Sessions', 'Reservations', 'Users', 'Pending Accounts', 'Payments', 'Alerts', 'Analytics', 'Settings'],
  ADMIN: ['Dashboard', 'Vehicles', 'Parking Spots', 'Parking Sessions', 'Reservations', 'Users', 'Pending Accounts', 'Payments', 'Alerts', 'Analytics', 'Settings'],
  OPERATOR: ['Dashboard', 'Vehicles', 'Parking Spots', 'Parking Sessions', 'Reservations', 'Payments', 'Alerts', 'Analytics'],
  SECURITY: ['Dashboard', 'Vehicles', 'Parking Spots', 'Parking Sessions', 'Alerts'],
  USER: ['Dashboard', 'Reservations', 'Payments'],
}

export default function App() {
  const [page, setPage] = useState('Dashboard')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [authPage, setAuthPage] = useState(() => {
    if (window.location.pathname === '/reset-password') return 'reset-password'
    return localStorage.getItem('smartpark_token') ? 'app' : 'login'
  })
  const [user, setUser] = useState(() => decodeToken(localStorage.getItem('smartpark_token')))

  const refreshUser = async () => {
    const token = localStorage.getItem('smartpark_token')
    if (!token) {
      setUser(null)
      return
    }
    try {
      const me = await getMe()
      setUser({ ...decodeToken(token), role: me.role, username: me.username, email: me.email })
    } catch {
      localStorage.removeItem('smartpark_token')
      setUser(null)
      setAuthPage('login')
    }
  }

  useEffect(() => {
    if (authPage === 'app') refreshUser()
  }, [authPage])

  const role = user?.role || 'USER'
  const visiblePages = MENU_BY_ROLE[role] || MENU_BY_ROLE.USER
  const safePage = visiblePages.includes(page) ? page : 'Dashboard'

  useEffect(() => {
    if (page !== safePage) setPage(safePage)
  }, [page, safePage])

  const logout = () => { localStorage.removeItem('smartpark_token'); setUser(null); setAuthPage('login') }

  if (authPage === 'reset-password') return <ResetPassword onReset={() => setAuthPage('login')} />
  if (authPage === 'login') return <Login onLogin={() => { setAuthPage('app'); refreshUser() }} onRegister={() => setAuthPage('register')} />
  if (authPage === 'register') return <Register onLogin={() => setAuthPage('login')} />

  const pages = {
    Dashboard,
    Vehicles: VehiclesLive,
    'Parking Spots': SpotsLive,
    'Parking Sessions': SessionsLive,
    Reservations: ReservationsLive,
    Users: UsersLive,
    'Pending Accounts': PendingAccountsLive,
    Payments: PaymentsLive,
    Alerts: AlertsLive,
    Analytics: AnalyticsPage,
    Settings: SettingsPage,
  }

  const Page = pages[safePage] || Dashboard

  return <main className="shell"><Sidebar activePage={safePage} onNavigate={setPage} onLogout={logout} mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} role={role} pages={visiblePages.map(name => {
    const map = {
      Dashboard: ['Dashboard', '⌂'],
      Vehicles: ['Vehicles', '▣'],
      'Parking Spots': ['Parking Spots', '▦'],
      'Parking Sessions': ['Parking Sessions', '◷'],
      Reservations: ['Reservations', '□'],
      Users: ['Users', '♙'],
      'Pending Accounts': ['Pending Accounts', '✓'],
      Payments: ['Payments', '◈'],
      Alerts: ['Alerts', '⚑'],
      Analytics: ['Analytics', '⌁'],
      Settings: ['Settings', '⚙'],
    }
    return map[name]
  })} /><section className="content"><div className="topbar"><button className="menu-button" onClick={() => setMobileOpen(true)}>☰</button><div className="global-search">⌕ <input placeholder="Search vehicles, plates, sessions..." /></div><button className="icon-button" aria-label="Notifications">♧<i /></button><div className="top-avatar">{(user?.username || 'U').slice(0, 2).toUpperCase()}</div></div><Page /></section></main>
}
