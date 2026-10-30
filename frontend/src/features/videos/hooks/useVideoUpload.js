import { useCallback, useRef, useState } from 'react'

import { uploadVideo } from '../api/videosApi'

/**
 * Tải video lên backend: idle → uploading (có tiến độ) → done | error.
 * Giữ lại video vừa tải để trang hiển thị panel kết quả AI ngay sau đó.
 */
export function useVideoUpload() {
  const [status, setStatus] = useState('idle')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const [uploadedVideo, setUploadedVideo] = useState(null)
  const abortRef = useRef(null)

  const upload = useCallback(async (file, caption) => {
    setStatus('uploading')
    setProgress(0)
    setError('')
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const video = await uploadVideo({ file, caption, onProgress: setProgress, signal: controller.signal })
      setUploadedVideo(video)
      setStatus('done')
      return video
    } catch (requestError) {
      setError(requestError.name === 'AbortError' ? 'Đã hủy tải lên.' : requestError.message)
      setStatus('error')
      return null
    } finally {
      abortRef.current = null
    }
  }, [])

  const cancel = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const reset = useCallback(() => {
    setStatus('idle')
    setProgress(0)
    setError('')
    setUploadedVideo(null)
  }, [])

  return { status, progress, error, uploadedVideo, upload, cancel, reset }
}
