import { useState } from 'react'
import { NavLink } from 'react-router-dom'

import Icon from '@/shared/components/Icon'
import { useAuth } from '@/features/auth/AuthContext'



const NAV_ITEMS = [
  { to: '/', label: 'Dành cho bạn', icon: 'home', end: true },
  { to: '/edit-video', label: 'Chỉnh sửa video', icon: 'film', auth: true },
  { to: '/moderation', label: 'Kiểm duyệt', icon: 'shield', roles: ['moderator', 'admin'] },
]

const SEARCH_HISTORY = ['video ngắn', 'kiểm duyệt', 'janus']
const SEARCH_SUGGEST = ['video hot', 'nội dung mới', 'xu hướng']

export default function SideNav() {
  const { user, isAuthenticated, logout } = useAuth()
  const [searchOpen, setSearchOpen] = useState(false)

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

      <div className="nav-search-wrap">
        <div className="nav-search">
          <Icon name="search" size={16} />
          <input type="text" placeholder="Tìm kiếm" onFocus={() => setSearchOpen(true)} onBlur={() => setTimeout(() => setSearchOpen(false), 150)} />
        </div>
        {searchOpen && (
          <div className="search-dropdown">
            <div className="search-section">
              <div className="search-section-title">Lịch sử tìm kiếm</div>
              {SEARCH_HISTORY.map((item) => (
                <button key={item} type="button" className="search-item">
                  <Icon name="clock" size={14} />
                  <span>{item}</span>
                </button>
              ))}
            </div>
            <div className="search-section">
              <div className="search-section-title">Gợi ý</div>
              {SEARCH_SUGGEST.map((item) => (
                <button key={item} type="button" className="search-item">
                  <Icon name="search" size={14} />
                  <span>{item}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      <nav className="side-nav" aria-label="Điều hướng chính">
        {NAV_ITEMS.filter((item) => {
          if (item.roles) return user && item.roles.includes(user.role)
          if (item.auth) return isAuthenticated
          return true
        }).map((item) => (
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
      </div>
    </aside>
  )
}