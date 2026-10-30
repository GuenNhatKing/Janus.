import { apiFetch } from '@/shared/api/client'

/** Đăng nhập, trả về { access_token, token_type }. */
export function login(email, password) {
  return apiFetch('/v1/auth/login', { method: 'POST', body: { email, password }, auth: false })
}

/** Đăng ký, trả về hồ sơ người dùng vừa tạo. */
export function register({ email, displayName, password }) {
  return apiFetch('/v1/auth/register', {
    method: 'POST',
    body: { email, display_name: displayName, password },
    auth: false,
  })
}

/** Lấy hồ sơ của token hiện tại — dùng để khôi phục phiên đăng nhập khi tải lại trang. */
export function fetchProfile() {
  return apiFetch('/v1/profile')
}
