export const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8001/ws/dashboard'
export const VISION_URL = import.meta.env.VITE_VISION_URL || 'http://127.0.0.1:8002'

async function request(path, options = {}) {
  const token = localStorage.getItem('smartpark_token')
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Request failed')
  return data
}

export async function login(credentials) {
  return request('/login', { method: 'POST', body: JSON.stringify(credentials) })
}

export async function register(user) {
  return request('/register', { method: 'POST', body: JSON.stringify(user) })
}

export function getDashboardOverview() {
  return request('/analytics/overview')
}

export function getOccupancy() {
  return request('/analytics/occupancy')
}

export function getParkingSpots() {
  return request('/parking-spots')
}

export function getSmartParkingOptions() { return request('/smart-parking/options') }
export function getMyDigitalTicket() { return request('/smart-parking/my-ticket') }
export function getFindMyCar() { return request('/smart-parking/find-my-car') }
export function getRewards() { return request('/smart-parking/rewards') }

export function createParkingSpot(data) {
  return request('/parking-spots', { method: 'POST', body: JSON.stringify(data) })
}

export function getPayments() {
  return request('/payments')
}

export function payPayment(id, paymentMethod = 'CARD') {
  return request(`/payments/${id}/pay`, { method: 'PUT', body: JSON.stringify({ payment_method: paymentMethod }) })
}

export function getAlerts() {
  return request('/alerts')
}

export function resolveAlert(id) {
  return request(`/alerts/${id}/resolve`, { method: 'PUT' })
}

export function updateSpotStatus(id, status) {
  return request(`/parking-spots/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) })
}

export function getParkingSessions() {
  return request('/parking-sessions')
}

export function getMyParkingSessions() {
  return request('/my-parking-sessions')
}

export function exitParkingSession(id) {
  return request(`/parking-sessions/${id}/exit`, { method: 'POST' })
}

export function getMe() {
  return request('/me')
}

export function getUsers() {
  return request('/users')
}

export function createUser(data) {
  return request('/users', { method: 'POST', body: JSON.stringify(data) })
}

export function deleteUser(id) {
  return request(`/users/${id}`, { method: 'DELETE' })
}

export function getPendingUsers() {
  return request('/users/pending')
}

export function approveUser(id) {
  return request(`/users/${id}/approve`, { method: 'POST' })
}

export function rejectUser(id) {
  return request(`/users/${id}/reject`, { method: 'POST' })
}

export function getVehicles() {
  return request('/vehicles')
}

export function createVehicle(data) {
  return request('/vehicles', { method: 'POST', body: JSON.stringify(data) })
}

export function getReservations() {
  return request('/reservations')
}

export function createReservation(data) {
  return request('/reservations', { method: 'POST', body: JSON.stringify(data) })
}

export function resetPassword(data) {
  return request('/reset-password', { method: 'POST', body: JSON.stringify(data) })
}

export function forgotPassword(email) {
  return request('/forgot-password', { method: 'POST', body: JSON.stringify({ email }) })
}
