import { apiFetch } from '@/shared/api/client'

export function fetchQueue() {
  return apiFetch('/v1/moderation/queue')
}

export function decideVideo(videoId, action, reason) {
  return apiFetch(`/v1/moderation/videos/${videoId}/decision`, {
    method: 'POST',
    body: { action, reason: reason || null },
  })
}

export function fetchReports() {
  return apiFetch('/v1/moderation/reports')
}

export function decideReport(reportId, action, reason) {
  return apiFetch(`/v1/moderation/reports/${reportId}/decision`, {
    method: 'POST',
    body: { action, reason: reason || null },
  })
}
