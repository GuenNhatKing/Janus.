import { useState } from 'react'

import { ErrorNote } from '@/shared/components/Feedback'
import { reportVideo } from '../api/videosApi'

const REASONS = [
  { value: 'spam', label: 'Spam / Quảng cáo' },
  { value: 'inappropriate', label: 'Nội dung không phù hợp' },
  { value: 'violent', label: 'Bạo lực / Hình ảnh gây sốc' },
  { value: 'harassment', label: 'Quấy rối / Xúc phạm' },
  { value: 'misinformation', label: 'Thông tin sai lệch' },
  { value: 'copyright', label: 'Bản quyền' },
  { value: 'scam', label: 'Lừa đảo' },
  { value: 'shocking', label: 'Video gây sốc' },
  { value: 'other', label: 'Lý do khác' },
]

export default function ReportDialog({ video, onClose, onReported }) {
  const [reasonType, setReasonType] = useState('')
  const [reason, setReason] = useState('')
  const [blockVideo, setBlockVideo] = useState(false)
  const [blockUser, setBlockUser] = useState(false)
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  async function submit(event) {
    event.preventDefault()
    const reasonText = reasonType === 'other' ? reason.trim() : (REASONS.find((r) => r.value === reasonType)?.label || reason.trim())
    if (!reasonType) {
      setError('Vui lòng chọn lý do báo cáo.')
      return
    }
    if (reasonType === 'other' && reasonText.length < 3) {
      setError('Vui lòng nhập lý do cụ thể (ít nhất 3 ký tự).')
      return
    }
    setSending(true)
    setError('')
    try {
      await reportVideo(video.id, reasonText)
      if (blockVideo) {
        localStorage.setItem('blocked_video_' + video.id, '1')
      }
      if (blockUser && video.owner_id) {
        localStorage.setItem('blocked_user_' + video.owner_id, '1')
      }
      onReported?.()
      onClose()
    } catch (requestError) {
      setError(requestError.detail || requestError.message)
      setSending(false)
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal">
        <header className="modal-head">
          <div>
            <p className="overline">Báo cáo</p>
            <h2>Báo cáo video này</h2>
          </div>
          <button type="button" className="icon-button" onClick={onClose}>Đóng</button>
        </header>
        <form className="modal-body" onSubmit={submit}>
          <label className="field">
            <span>Lý do báo cáo</span>
            <select className="text-input" value={reasonType} onChange={(e) => setReasonType(e.target.value)}>
              <option value="">Chọn lý do</option>
              {REASONS.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          {reasonType === 'other' && (
            <label className="field">
              <span>Nhập lý do</span>
              <textarea className="text-input textarea" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Mô tả cụ thể lý do báo cáo..." />
            </label>
          )}
          <div className="field">
            <span>Tùy chọn bổ sung</span>
            <label className="checkbox-row">
              <input type="checkbox" checked={blockVideo} onChange={(e) => setBlockVideo(e.target.checked)} />
              <span>Không xem video này nữa</span>
            </label>
            <label className="checkbox-row">
              <input type="checkbox" checked={blockUser} onChange={(e) => setBlockUser(e.target.checked)} />
              <span>Chặn luôn người đăng video</span>
            </label>
          </div>
          <ErrorNote>{error}</ErrorNote>
          <footer className="modal-foot">
            <button type="button" className="button ghost" onClick={onClose}>Hủy</button>
            <button type="submit" className="button primary" disabled={sending}>{sending ? 'Đang gửi...' : 'Gửi báo cáo'}</button>
          </footer>
        </form>
      </div>
    </div>
  )
}