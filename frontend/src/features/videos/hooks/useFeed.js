import { useCallback, useEffect, useState } from 'react'

import { fetchFeed } from '../api/videosApi'

/** Lấy feed công khai + hàm làm mới (dùng lại sau khi tải video hoặc báo cáo). */
export function useFeed() {
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setError('')
    try {
      setVideos(await fetchFeed())
    } catch (requestError) {
      setError(requestError.detail || requestError.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { videos, loading, error, refresh }
}
