/**
 * API client dùng chung.
 *
 * - Đọc base URL từ VITE_API_BASE_URL (mặc định "/api" = Vite proxy sang backend).
 * - Tự gắn Bearer token nếu người dùng đã đăng nhập.
 * - Ném ApiError có status + detail để UI hiển thị đúng thông báo từ backend.
 */

const RAW_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
const BASE_URL = RAW_BASE.endsWith('/') ? RAW_BASE.slice(0, -1) : RAW_BASE

const TOKEN_KEY = 'janus.access_token'

export class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `Yêu cầu thất bại (${status})`)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail || `Yêu cầu thất bại (${status})`
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/** URL tuyệt đối cho các thẻ không qua fetch (vd: <video src={videoUrl(...)} />). */
export function apiUrl(path) {
  return `${BASE_URL}${path}`
}

/**
 * Gọi API backend.
 * @param {string} path    path tương đối, ví dụ "/v1/auth/login"
 * @param {object} options { method, body, auth, headers, signal }
 */
export async function apiFetch(path, options = {}) {
  const { method = 'GET', body, auth = true, headers = {}, signal } = options
  const token = getToken()

  const requestHeaders = { ...headers }
  const isFormData = body instanceof FormData
  if (body && !isFormData) requestHeaders['Content-Type'] = 'application/json'
  if (auth && token) requestHeaders.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: requestHeaders,
      body: body === undefined || body === null ? undefined : isFormData ? body : JSON.stringify(body),
      signal,
    })
  } catch {
    // Mất mạng / backend chưa chạy: trả về lỗi rõ ràng thay vì để Promise reject im lặng.
    throw new ApiError(0, 'Không kết nối được tới máy chủ. Hãy kiểm tra backend đang chạy.')
  }

  if (response.status === 204) return null

  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : null
    throw new ApiError(response.status, detail || `Yêu cầu thất bại (${response.status})`)
  }
  return payload
}
