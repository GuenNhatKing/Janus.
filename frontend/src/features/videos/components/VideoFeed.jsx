import { EmptyState, ErrorNote, Spinner } from '@/shared/components/Feedback'
import { useFeed } from '../hooks/useFeed'
import VideoSlide from './VideoSlide'

/** Feed dọc kiểu TikTok: mỗi video chiếm trọn khung, cuộn snap giữa các video. */
export default function VideoFeed() {
  const { videos, loading, error, refresh } = useFeed()

  if (loading) {
    return (
      <div className="feed-center">
        <Spinner label="Đang tải feed" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="feed-center">
        <ErrorNote>{error}</ErrorNote>
        <button type="button" className="button ghost" onClick={refresh}>
          Thử lại
        </button>
      </div>
    )
  }

  if (videos.length === 0) {
    return (
      <div className="feed-center">
        <EmptyState
          icon="film"
          title="Chưa có video nào được phát"
          hint="Hãy tải video đầu tiên lên Janus để xem kết quả kiểm duyệt tại đây."
          action={
            <a className="button primary" href="/upload">
              Tải video lên
            </a>
          }
        />
      </div>
    )
  }

  return (
    <div className="feed">
      {videos.map((video) => (
        <VideoSlide key={video.id} video={video} onReported={refresh} />
      ))}
    </div>
  )
}
