import { useCallback, useEffect, useState } from 'react'

import Icon from '@/shared/components/Icon'
import { EmptyState, ErrorNote, Spinner, StatusBadge } from '@/shared/components/Feedback'
import { VIDEO_STATUS_LABEL, formatBytes, formatDateTime } from '@/shared/lib/format'
import { useAuth } from '@/features/auth/AuthContext'
import AiResultPanel from '@/features/videos/components/AiResultPanel'
import { deleteVideo, fetchMyVideos, streamUrl } from '@/features/videos/api/videosApi'

export default function ProfilePage() {
  const { user } = useAuth()
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    setError('')
    try {
      const items = await fetchMyVideos()
      setVideos(items)
      setSelectedId((current) => (current && items.some((item) => item.id === current) ? current : items[0]?.id ?? null))
    } catch (requestError) {
      setError(requestError.detail || requestError.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function remove(video) {
    setBusyId(video.id)
    try {
      await deleteVideo(video.id)
      await load()
    } catch (requestError) {
      setError(requestError.detail || requestError.message)
    } finally {
      setBusyId(null)
    }
  }

  if (loading) {
    return (
      <div className="page-center">
        <Spinner label="Đang tải danh sách video" />
      </div>
    )
  }

  return (
    <div className="page">
      <div className="profile-head">
        <span className="avatar avatar-lg">{user.display_name.slice(0, 2).toUpperCase()}</span>
        <div>
          <h1>{user.display_name}</h1>
          <p className="page-sub">
            {user.email} · vai trò <strong>{user.role}</strong>
          </p>
        </div>
        <div className="stat-row">
          <div className="stat">
            <strong>{videos.length}</strong>
            <span>Video</span>
          </div>
          <div className="stat">
            <strong>{videos.filter((item) => item.status === 'published').length}</strong>
            <span>Đã phát</span>
          </div>
          <div className="stat">
            <strong>{videos.filter((item) => item.status === 'pending_review').length}</strong>
            <span>Chờ duyệt</span>
          </div>
        </div>
      </div>

      <ErrorNote>{error}</ErrorNote>

      {videos.length === 0 ? (
        <EmptyState
          icon="upload"
          title="Bạn chưa tải video nào"
          hint="Video tải lên sẽ hiển thị tại đây cùng kết quả phân tích AI."
          action={
            <a className="button primary" href="/upload">
              Tải video đầu tiên
            </a>
          }
        />
      ) : (
        <div className="profile-grid">
          <ul className="video-list">
            {videos.map((video) => (
              <li key={video.id} className={video.id === selectedId ? 'video-row active' : 'video-row'}>
                <button type="button" className="video-row-main" onClick={() => setSelectedId(video.id)}>
                  <span className="video-row-thumb">
                    <video src={streamUrl(video.id)} muted playsInline preload="metadata" />
                  </span>
                  <span className="video-row-copy">
                    <strong>{video.caption || video.original_filename}</strong>
                    <span>
                      {formatDateTime(video.created_at)} · {formatBytes(video.size_bytes)}
                    </span>
                  </span>
                  <StatusBadge status={video.status} label={VIDEO_STATUS_LABEL[video.status] || video.status} />
                </button>
                <button
                  type="button"
                  className="icon-button danger"
                  onClick={() => remove(video)}
                  disabled={busyId === video.id}
                  aria-label="Xóa video"
                  title="Xóa video"
                >
                  <Icon name="trash" size={16} />
                </button>
              </li>
            ))}
          </ul>

          {selectedId && <AiResultPanel videoId={selectedId} />}
        </div>
      )}
    </div>
  )
}
