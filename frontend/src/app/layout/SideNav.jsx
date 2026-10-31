import { NavLink } from 'react-router-dom'

import Icon from '@/shared/components/Icon'
import { useAuth } from '@/features/auth/AuthContext'

const NAV_ITEMS = [
  { to: '/', label: 'Dành cho bạn', icon: 'home', end: true },
  { to: '/moderation', label: 'Kiểm duyệt', icon: 'shield', roles: ['moderator', 'admin'] },
]

export default function SideNav() {
  const { user, isAuthenticated, logout } = useAuth()

  return (
    <aside className="sidenav">
      <div className="brand-row">
        <NavLink to="/" className="brand">
          <span className="brand-mark">
            <Icon name="play" size={14} />
          </span>
          Janus
        </NavLink>
      </div>

      <div className="nav-search">
        <Icon name="search" size={16} />
        <input type="text" placeholder="Tìm kiếm" />
      </div>

      <nav className="side-nav" aria-label="Điều hướng chính">
        {NAV_ITEMS.filter((item) => !item.roles || (user && item.roles.includes(user.role))).map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon name={item.icon} size={18} />
            <span>{item.label}</span>
          </NavLink>
        ))}
        {isAuthenticated && (
          <>
            <NavLink to="/upload" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Icon name="upload" size={18} />
              <span>Tải video</span>
            </NavLink>
            <NavLink to="/profile" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <Icon name="user" size={18} />
              <span>Hồ sơ</span>
            </NavLink>
          </>
        )}
      </nav>

      <div className="side-foot">
        {isAuthenticated ? (
          <>
            <div className="side-user">
              <span className="avatar">{user.display_name.slice(0, 2).toUpperCase()}</span>
              <div className="side-user-copy">
                <strong>{user.display_name}</strong>
                <span>{user.role}</span>
              </div>
            </div>
            <button type="button" className="nav-item" onClick={logout}>
              <Icon name="logout" size={18} />
              <span>Đăng xuất</span>
            </button>
          </>
        ) : null}
        <p className="side-note">Dữ liệu demo · không phải kết luận kiểm duyệt</p>
      </div>
    </aside>
  )
}
