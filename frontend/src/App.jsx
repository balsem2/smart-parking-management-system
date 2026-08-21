import { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar'
import DashboardLive from './pages/DashboardLive'
import { AnalyticsPage, SettingsPage } from './pages/OperationsPages'
import Login from './pages/Login'
import Register from './pages/Register'
import { AlertsLive, PaymentsLive, PendingAccountsLive, ReservationsLive, SessionsLive, SpotsManageLive, UsersLive, VehiclesLive } from './pages/OperationsLive'
import { CustomerParkingLive, CustomerReservationsLive } from './pages/CustomerParking'
import ResetPassword from './pages/ResetPassword'
import CameraDetection from './pages/CameraDetection'
import SmartParking from './pages/SmartParking'
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
  SUPER_ADMIN: ['Dashboard', 'Camera Detection', 'Vehicles', 'Parking Spots', 'Parking Sessions', 'Reservations', 'Users', 'Pending Accounts', 'Payments', 'Alerts', 'Analytics', 'Settings'],
  ADMIN: ['Dashboard', 'Camera Detection', 'Vehicles', 'Parking Spots', 'Parking Sessions', 'Reservations', 'Users', 'Pending Accounts', 'Payments', 'Alerts', 'Analytics', 'Settings'],
  OPERATOR: ['Dashboard', 'Camera Detection', 'Vehicles', 'Parking Spots', 'Parking Sessions', 'Reservations', 'Payments', 'Alerts', 'Analytics'],
  SECURITY: ['Dashboard', 'Camera Detection', 'Vehicles', 'Parking Spots', 'Parking Sessions', 'Alerts'],
  USER: ['Smart Parking', 'My Parking', 'Reservations', 'Payments'],
}

export default function App() {
  const [page, setPage] = useState('Dashboard')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [authPage, setAuthPage] = useState(() => {
    if (window.location.pathname === '/reset-password') return 'reset-password'
    if (window.location.pathname === '/register' || new URLSearchParams(window.location.search).get('entry') === 'register') return 'register'
    return localStorage.getItem('smartpark_token') ? 'app' : 'login'
  })
  const [user, setUser] = useState(() => decodeToken(localStorage.getItem('smartpark_token')))
  const [profileLoading, setProfileLoading] = useState(() => Boolean(localStorage.getItem('smartpark_token')))

  const refreshUser = async () => {
    const token = localStorage.getItem('smartpark_token')
    if (!token) {
      setUser(null)
      setProfileLoading(false)
      return
    }
    try {
      const me = await getMe()
      setUser({ ...decodeToken(token), role: me.role, username: me.username, email: me.email })
    } catch {
      localStorage.removeItem('smartpark_token')
      setUser(null)
      setAuthPage('login')
    } finally {
      setProfileLoading(false)
    }
  }

  useEffect(() => {
    if (authPage === 'app') refreshUser()
  }, [authPage])

  const role = user?.role || 'USER'
  const visiblePages = MENU_BY_ROLE[role] || MENU_BY_ROLE.USER
  const safePage = visiblePages.includes(page) ? page : visiblePages[0]

  useEffect(() => {
    if (page !== safePage) setPage(safePage)
  }, [page, safePage])

  const logout = () => { localStorage.removeItem('smartpark_token'); setUser(null); setProfileLoading(false); setAuthPage('login') }

  if (authPage === 'reset-password') return <ResetPassword onReset={() => setAuthPage('login')} />
  if (authPage === 'login') return <Login onLogin={() => { setProfileLoading(true); setAuthPage('app') }} onRegister={() => setAuthPage('register')} />
  if (authPage === 'register') return <Register onLogin={() => setAuthPage('login')} />
  if (profileLoading) return <main className="auth"><section className="auth-card"><p className="eyebrow">SMARTPARK AI</p><h1>Loading your workspace...</h1></section></main>

  const pages = {
    Dashboard: DashboardLive,
    'Camera Detection': CameraDetection,
    Vehicles: VehiclesLive,
    'Parking Spots': SpotsManageLive,
    'Parking Sessions': SessionsLive,
    'My Parking': CustomerParkingLive,
    'Smart Parking': SmartParking,
    Reservations: role === 'USER' ? CustomerReservationsLive : ReservationsLive,
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
      'My Parking': ['My Parking', 'P'],
      'Smart Parking': ['Smart Parking', 'S'],
      Dashboard: ['Dashboard', '⌂'],
      'Camera Detection': ['Camera Detection', '◉'],
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
  })} /><section className="content"><div className="topbar"><button className="menu-button" onClick={() => setMobileOpen(true)}>☰</button><div className="global-search">⌕ <input placeholder="Search vehicles, plates, sessions..." /></div><button className="icon-button" aria-label="Notifications">♧<i /></button><div className="top-avatar">{(user?.username || 'U').slice(0, 2).toUpperCase()}</div></div><Page currentRole={role} /></section></main>
}
