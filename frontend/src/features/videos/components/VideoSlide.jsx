import { useEffect, useRef, useState } from 'react'

import Icon from '@/shared/components/Icon'
import { StatusBadge } from '@/shared/components/Feedback'
import { VIDEO_STATUS_LABEL, formatBytes } from '@/shared/lib/format'
import { streamUrl } from '../api/videosApi'
import ReportDialog from './ReportDialog'

/** Một video trong feed: bấm để phát/tạm dừng, có nút báo cáo gửi vào hàng đợi kiểm duyệt. */
export default function VideoSlide({ video, onReported }) {
  const videoRef = useRef(null)
  const [playing, setPlaying] = useState(false)
  const [muted, setMuted] = useState(true)
  const [reporting, setReporting] = useState(false)

  useEffect(() => {
    setPlaying(false)
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
        <span className="slide-user">@{video.owner_name || 'janus'}</span>
        <p className="slide-caption">{video.caption || video.original_filename}</p>
        <div className="slide-tags">
          <StatusBadge status={video.status} label={VIDEO_STATUS_LABEL[video.status] || video.status} />
          <span className="slide-size">{formatBytes(video.size_bytes)}</span>
        </div>
      </div>

      <div className="slide-actions">
        <button
          type="button"
          className="rail-button"
          onClick={() => setMuted((value) => !value)}
          aria-label={muted ? 'Bật tiếng' : 'Tắt tiếng'}
        >
          <Icon name={muted ? 'mute' : 'volume'} size={20} />
          <span>{muted ? 'Bật tiếng' : 'Tắt tiếng'}</span>
        </button>
        <button type="button" className="rail-button" onClick={() => setReporting(true)}>
          <Icon name="flag" size={20} />
          <span>Báo cáo</span>
        </button>
      </div>

      {reporting && <ReportDialog video={video} onClose={() => setReporting(false)} onReported={onReported} />}
    </article>
  )
}
