import { Navigate, useLocation } from 'react-router-dom'

import { Spinner } from '@/shared/components/Feedback'
import { useAuth } from '@/features/auth/AuthContext'

/** Yêu cầu đăng nhập: chưa đăng nhập thì chuyển về /login và giữ lại đường dẫn đích. */
export function RequireAuth({ children }) {
  const { isAuthenticated, ready } = useAuth()
  const location = useLocation()

  if (!ready) {
    return (
      <div className="page-center">
        <Spinner label="Đang kiểm tra phiên đăng nhập" />
      </div>
    )
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}

/** Yêu cầu vai trò (moderator/admin) cho các trang quản trị. */
export function RequireRole({ roles, children }) {
  const { user, ready } = useAuth()

  if (!ready) {
    return (
      <div className="page-center">
        <Spinner label="Đang kiểm tra quyền truy cập" />
      </div>
    )
  }
  if (!user || !roles.includes(user.role)) {
    return <Navigate to="/" replace />
  }
  return children
}
