const defaultPages = [
  ['Dashboard', '⌂'], ['Vehicles', '▣'], ['Parking Spots', '▦'],
  ['Parking Sessions', '◷'], ['Reservations', '□'], ['Users', '♙'],
  ['Pending Accounts', '✓'], ['Payments', '◈'], ['Alerts', '⚑'], ['Analytics', '⌁'], ['Settings', '⚙'],
]

const rolePages = {
  SUPER_ADMIN: defaultPages,
  ADMIN: defaultPages,
  OPERATOR: [['Dashboard', '⌂'], ['Vehicles', '▣'], ['Parking Spots', '▦'], ['Parking Sessions', '◷'], ['Reservations', '□'], ['Payments', '◈'], ['Alerts', '⚑'], ['Analytics', '⌁']],
  SECURITY: [['Dashboard', '⌂'], ['Vehicles', '▣'], ['Parking Spots', '▦'], ['Parking Sessions', '◷'], ['Alerts', '⚑']],
  USER: [['Dashboard', '⌂'], ['Reservations', '□'], ['Payments', '◈']],
}

export default function Sidebar({ activePage, onNavigate, onLogout, mobileOpen, onClose, role = 'ADMIN', pages = defaultPages }) {
  const visiblePages = pages && pages.length ? pages : (rolePages[role] || rolePages.USER)

  return <aside className={mobileOpen ? 'sidebar open' : 'sidebar'}>
    <div className="brand"><b>SP</b><span>SmartPark<small>AI COMMAND CENTER</small></span><button className="close-nav" onClick={onClose}>×</button></div>
    <nav>{visiblePages.map(([page, icon]) => <button type="button" className={page === activePage ? 'active' : ''} onClick={() => { onNavigate(page); onClose() }} key={page}><i>{icon}</i>{page}</button>)}</nav>
    <div className="sidebar-bottom"><p className="connection"><i className="on" />Live / Connected</p><div className="profile"><span>{role.slice(0, 2).toUpperCase()}</span><div><strong>{role.replace('_', ' ')}</strong><small>{role === 'USER' ? 'User account' : 'Staff access'}</small></div><button aria-label="Log out" onClick={onLogout}>↪</button></div></div>
  </aside>
}
