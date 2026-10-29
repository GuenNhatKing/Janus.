import { useEffect, useRef, useState } from 'react'

import Icon from '@/shared/components/Icon'
import { ErrorNote } from '@/shared/components/Feedback'
import { formatBytes } from '@/shared/lib/format'

const MAX_SIZE = 50 * 1024 * 1024

/** Vùng chọn tệp: kiểm tra định dạng/dung lượng phía client trước khi gửi lên backend. */
export default function UploadDropzone({ file, onSelect, disabled }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [previewUrl, setPreviewUrl] = useState('')

  // Tạo object URL cho xem trước và giải phóng khi đổi file hoặc khi gỡ component.
  useEffect(() => {
    if (!file) {
      setPreviewUrl('')
      return undefined
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  function accept(nextFile) {
    if (!nextFile) return
    if (!nextFile.name.toLowerCase().endsWith('.mp4') || (nextFile.type && nextFile.type !== 'video/mp4')) {
      setError('Chỉ chấp nhận video định dạng MP4.')
      return
    }
    if (nextFile.size > MAX_SIZE) {
      setError('Video vượt quá dung lượng tối đa 50 MB.')
      return
    }
    setError('')
    onSelect(nextFile)
  }

  return (
    <div className="dropzone-wrap">
      {!file ? (
        <div
          className={`dropzone ${dragging ? 'dragging' : ''} ${disabled ? 'disabled' : ''}`}
          role="button"
          tabIndex={0}
          onClick={() => !disabled && inputRef.current?.click()}
          onKeyDown={(event) => {
            if ((event.key === 'Enter' || event.key === ' ') && !disabled) {
              event.preventDefault()
              inputRef.current?.click()
            }
          }}
          onDragOver={(event) => {
            event.preventDefault()
            if (!disabled) setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            if (!disabled) accept(event.dataTransfer.files?.[0])
          }}
        >
          <span className="dropzone-icon">
            <Icon name="upload" size={22} />
          </span>
          <h3>Kéo video vào đây</h3>
          <p>
            hoặc{' '}
            <button type="button" onClick={(event) => { event.stopPropagation(); inputRef.current?.click() }}>
              chọn tệp từ thiết bị
            </button>
          </p>
          <span className="dropzone-rules">MP4 · Tối đa 50 MB</span>
        </div>
      ) : (
        <div className="selected-file">
          {previewUrl && <video src={previewUrl} controls playsInline />}
          <div className="selected-meta">
            <div>
              <strong>{file.name}</strong>
              <span>{formatBytes(file.size)} · MP4</span>
            </div>
            <button type="button" className="button ghost" onClick={() => inputRef.current?.click()} disabled={disabled}>
              Đổi video
            </button>
          </div>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="video/mp4,.mp4"
        hidden
        onChange={(event) => {
          accept(event.target.files?.[0])
          event.target.value = ''
        }}
      />
      <ErrorNote>{error}</ErrorNote>
    </div>
  )
}
