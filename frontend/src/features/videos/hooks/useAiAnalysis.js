import { useEffect, useRef, useState } from 'react'

import { fetchAiResult } from '../api/videosApi'

const TERMINAL_STATUSES = ['succeeded', 'failed']
const POLL_INTERVAL_MS = 1500
const MAX_ATTEMPTS = 40

/**
 * Poll kết quả AI cho một video cho tới khi job kết thúc.
 * Backend chạy job bằng BackgroundTasks nên frontend phải hỏi thăm,
 * không có sự kiện push nào.
 */
export function useAiAnalysis(videoId) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const attemptsRef = useRef(0)

  useEffect(() => {
    if (!videoId) {
      setResult(null)
      return undefined
    }
    let active = true
    let timer = null
    attemptsRef.current = 0
    setResult(null)
    setError('')
    setLoading(true)

    async function poll() {
      try {
        const data = await fetchAiResult(videoId)
        if (!active) return
        setResult(data)
        if (TERMINAL_STATUSES.includes(data.job_status)) {
          setLoading(false)
          return
        }
      } catch (requestError) {
        if (!active) return
        setError(requestError.detail || requestError.message)
        setLoading(false)
        return
      }
      attemptsRef.current += 1
      if (attemptsRef.current >= MAX_ATTEMPTS) {
        if (active) {
          setError('Đã chờ quá lâu cho kết quả phân tích. Thử lại sau.')
          setLoading(false)
        }
        return
      }
      timer = window.setTimeout(poll, POLL_INTERVAL_MS)
    }

    poll()
    return () => {
      active = false
      if (timer) window.clearTimeout(timer)
    }
  }, [videoId])

  return { result, loading, error }
}
