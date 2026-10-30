import { useState } from 'react'
import { Link } from 'react-router-dom'

import Icon from '@/shared/components/Icon'
import { ErrorNote } from '@/shared/components/Feedback'
import AiResultPanel from '@/features/videos/components/AiResultPanel'
import UploadDropzone from '@/features/videos/components/UploadDropzone'
import { useVideoUpload } from '@/features/videos/hooks/useVideoUpload'

export default function UploadPage() {
  const [file, setFile] = useState(null)
  const [caption, setCaption] = useState('')
  const { status, progress, error, uploadedVideo, upload, reset } = useVideoUpload()

  const uploading = status === 'uploading'
  const done = status === 'done'

  function selectFile(nextFile) {
    reset()
    setFile(nextFile)
  }

  async function submit(event) {
    event.preventDefault()
    if (!file) return
    const captionValue = caption.trim()
    await upload(file, captionValue || null)
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <span className="overline">QUY TRÌNH KIỂM THỬ</span>
          <h1>Tải video lên</h1>
          <p className="page-sub">
            Video được backend kiểm tra định dạng, lưu trữ và chạy phân tích AI nền. Kết quả hiển thị ngay bên dưới.
          </p>
        </div>
        <span className="hint-chip">MP4 · tối đa 50 MB</span>
      </div>

      <div className="upload-grid">
        <form className="panel upload-panel" onSubmit={submit}>
          <UploadDropzone file={file} onSelect={selectFile} disabled={uploading} />

          <label className="field" htmlFor="caption">
            <span>
              Mô tả video <em>không bắt buộc</em>
            </span>
            <input
              id="caption"
              className="text-input"
              value={caption}
              maxLength={500}
              onChange={(event) => setCaption(event.target.value)}
              placeholder="Video này nói về điều gì?"
              disabled={uploading}
            />
          </label>

          <ErrorNote>{error}</ErrorNote>

          {uploading && (
            <div className="upload-progress" aria-live="polite">
              <div className="progress-track">
                <i style={{ width: `${progress}%` }} />
              </div>
              <span>Đang tải lên {progress}%</span>
            </div>
          )}

          <div className="panel-actions">
            {done ? (
              <>
                <button type="button" className="button ghost" onClick={reset}>
                  Tải video khác
                </button>
                <Link className="button primary" to="/">
                  Xem ở feed <Icon name="arrow" size={15} />
                </Link>
              </>
            ) : (
              <button type="submit" className="button primary" disabled={!file || uploading}>
                {uploading ? 'Đang tải lên…' : 'Tải lên và phân tích'}
              </button>
            )}
          </div>
        </form>

        <aside className="panel info-panel">
          <div className="info-title">
            <Icon name="shield" size={17} />
            <h2>Kiểm duyệt tự động</h2>
          </div>
          <ul className="info-list">
            <li>Hệ thống kiểm tra magic bytes và codec của tệp MP4 trước khi lưu.</li>
            <li>Job AI chạy nền bằng FastAPI BackgroundTasks, frontend poll tới khi kết thúc.</li>
            <li>Video chỉ xuất hiện ở feed sau khi phân tích xong.</li>
            <li>Mọi người đều có thể báo cáo video để đưa vào hàng đợi kiểm duyệt.</li>
          </ul>
        </aside>
      </div>

      {uploadedVideo && <AiResultPanel videoId={uploadedVideo.id} />}
    </div>
  )
}
