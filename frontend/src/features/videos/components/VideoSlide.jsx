import { useEffect, useRef, useState } from 'react'

import Icon from '@/shared/components/Icon'
import { formatBytes } from '@/shared/lib/format'
import { streamUrl } from '../api/videosApi'
import ReportDialog from './ReportDialog'

/** Một video trong feed: bấm để phát/tạm dừng, có các hành động bên phải. */
export default function VideoSlide({ video, onReported }) {
  const videoRef = useRef(null)
  const [playing, setPlaying] = useState(false)
  const [muted, setMuted] = useState(true)
  const [reporting, setReporting] = useState(false)
  const [liked, setLiked] = useState(false)
  const [followed, setFollowed] = useState(false)

  useEffect(() => {
    setPlaying(false)
    setLiked(false)
    setFollowed(false)
  }, [video.id])

  async function togglePlayback() {
    const element = videoRef.current
    if (!element) return
    if (element.paused) {
      try {
        await element.play()
        setPlaying(true)
      } catch {
        setPlaying(false)
      }
    } else {
      element.pause()
      setPlaying(false)
    }
  }

  const viewCount = video.views || video.view_count || video.play_count || 0
  const likeCount = video.likes || video.like_count || 0

  return (
    <article className="slide">
      <button type="button" className="slide-stage" onClick={togglePlayback} aria-label="Phát hoặc tạm dừng video">
        <video
          ref={videoRef}
          src={streamUrl(video.id)}
          loop
          playsInline
          muted={muted}
          preload="metadata"
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
        />
        {!playing && (
          <span className="slide-play">
            <Icon name="play" size={26} />
          </span>
        )}
      </button>

      <div className="slide-meta">
        <div className="slide-user-row">
          <span className="slide-user">@{video.owner_name || 'janus'}</span>
          <button type="button" className={`slide-follow ${followed ? 'active' : ''}`} onClick={() => setFollowed((v) => !v)}>
            {followed ? 'Đang theo dõi' : 'Theo dõi'}
          </button>
        </div>
        <p className="slide-caption">{video.caption || video.original_filename}</p>
        <div className="slide-view">
          <Icon name="play" size={12} />
          <span>{viewCount.toLocaleString('vi-VN')} lượt xem</span>
        </div>
      </div>

      <div className="slide-actions">
        <button type="button" className={`rail-button ${liked ? 'active' : ''}`} onClick={() => setLiked((v) => !v)}>
          <Icon name="heart" size={22} />
          <span>{likeCount + (liked ? 1 : 0)}</span>
        </button>
        <button type="button" className="rail-button">
          <Icon name="message" size={22} />
          <span>Bình luận</span>
        </button>
        <button
          type="button"
          className="rail-button"
          onClick={() => setMuted((value) => !value)}
          aria-label={muted ? 'Bật tiếng' : 'Tắt tiếng'}
        >
          <Icon name={muted ? 'mute' : 'volume'} size={22} />
          <span>{muted ? 'Bật tiếng' : 'Tắt tiếng'}</span>
        </button>
        <button type="button" className="rail-button" onClick={() => setReporting(true)}>
          <Icon name="flag" size={22} />
          <span>Báo cáo</span>
        </button>
      </div>

      {reporting && <ReportDialog video={video} onClose={() => setReporting(false)} onReported={onReported} />}
    </article>
  )
}
