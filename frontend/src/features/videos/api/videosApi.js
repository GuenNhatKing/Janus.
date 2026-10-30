import { apiFetch, apiUrl, getToken } from '@/shared/api/client'

/** URL phát video (thẻ <video src=...> không đi qua fetch). */
export function streamUrl(videoId) {
  return apiUrl(`/v1/videos/${videoId}/stream`)
}

export function fetchFeed() {
  return apiFetch('/v1/feed', { auth: false })
}

export function fetchMyVideos() {
  return apiFetch('/v1/videos')
}

export function fetchAiResult(videoId) {
  return apiFetch(`/v1/videos/${videoId}/ai`)
}

export function deleteVideo(videoId) {
  return apiFetch(`/v1/videos/${videoId}`, { method: 'DELETE' })
}

export function reportVideo(videoId, reason) {
  return apiFetch(`/v1/videos/${videoId}/reports`, { method: 'POST', body: { reason } })
}

/**
 * Tải video lên bằng XMLHttpRequest để có tiến độ thực tế.
 * Lưu ý theo API guide: `caption` truyền dưới dạng query parameter,
 * chỉ phần tệp nằm trong multipart form-data.
 * @returns {Promise<object>} response 201 của backend (hồ sơ video).
 */
export function uploadVideo({ file, caption, onProgress, signal }) {
  return new Promise((resolve, reject) => {
    const body = new FormData()
    body.append('file', file)
    const query = caption ? `?caption=${encodeURIComponent(caption)}` : ''

    const request = new XMLHttpRequest()
    const token = getToken()
    request.open('POST', apiUrl(`/v1/videos${query}`))
    if (token) request.setRequestHeader('Authorization', `Bearer ${token}`)

    request.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) onProgress(Math.round((event.loaded / event.total) * 100))
    }
    request.onload = () => {
      let payload = null
      try {
        payload = JSON.parse(request.responseText)
      } catch {
        payload = null
      }
      if (request.status >= 200 && request.status < 300) {
        resolve(payload)
      } else {
        const detail = typeof payload?.detail === 'string' ? payload.detail : null
        reject(new Error(detail || `Tải video thất bại (${request.status})`))
      }
    }
    request.onerror = () => reject(new Error('Không kết nối được tới máy chủ. Hãy kiểm tra backend đang chạy.'))
    if (signal) signal.addEventListener('abort', () => request.abort(), { once: true })
    request.send(body)
  })
}
