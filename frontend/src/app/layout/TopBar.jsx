import { Link, useLocation } from 'react-router-dom'

import Icon from '@/shared/components/Icon'
import { useAuth } from '@/features/auth/AuthContext'

const TITLES = {
  '/': 'Dành cho bạn',
  '/upload': 'Tải video',
  '/profile': 'Hồ sơ của bạn',
  '/moderation': 'Hàng đợi kiểm duyệt',
}

export default function TopBar() {
  const { pathname } = useLocation()
  const { user, isAuthenticated } = useAuth()

  return (
    <header className="topbar">
      <div className="topbar-title">
        <span className="crumb">Janus</span>
        <span className="crumb-sep">/</span>
        <strong>{TITLES[pathname] || 'Trang'}</strong>
      </div>

      <div className="topbar-actions">
        {isAuthenticated && (
          <span className="role-pill" title="Vai trò hiện tại">
            <i />
            {user.role}
          </span>
        )}
        <Link to="/upload" className="button primary">
          <Icon name="upload" size={15} />
          Tải video
        </Link>
        {isAuthenticated ? (
          <Link to="/profile" className="avatar" aria-label="Hồ sơ">
            {user.display_name.slice(0, 2).toUpperCase()}
          </Link>
        ) : (
          <Link to="/login" className="button ghost">
            Đăng nhập
          </Link>
        )}
      </div>
    </header>
  )
}
