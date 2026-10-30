import { useState } from 'react'

import { Modal, ErrorNote } from '@/shared/components/Feedback'
import { reportVideo } from '../api/videosApi'

/** Hộp thoại báo cáo video — lý do tối thiểu 3 ký tự theo schema backend. */
export default function ReportDialog({ video, onClose, onReported }) {
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)

  async function submit(event) {
    event.preventDefault()
    const trimmed = reason.trim()
    if (trimmed.length < 3) {
      setError('Lý do cần ít nhất 3 ký tự.')
      return
    }
    setSending(true)
    setError('')
    try {
      await reportVideo(video.id, trimmed)
      onReported?.()
      onClose()
    } catch (requestError) {
      setError(requestError.detail || requestError.message)
      setSending(false)
    }
  }

  return (
    <Modal title="Báo cáo video" onClose={onClose}>
      <form className="modal-body" onSubmit={submit}>
        <p className="modal-text">
          Báo cáo video <strong>{video.caption || video.original_filename}</strong> để đưa vào hàng đợi kiểm duyệt.
        </p>
        <label className="field-label" htmlFor="report-reason">
          Lý do
        </label>
        <textarea
          id="report-reason"
          className="text-input"
          rows={3}
          maxLength={1000}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          placeholder="Ví dụ: nội dung bạo lực, không phù hợp…"
        />
        <ErrorNote>{error}</ErrorNote>
        <div className="modal-actions">
          <button type="button" className="button ghost" onClick={onClose}>
            Hủy
          </button>
          <button type="submit" className="button primary" disabled={sending}>
            {sending ? 'Đang gửi…' : 'Gửi báo cáo'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
