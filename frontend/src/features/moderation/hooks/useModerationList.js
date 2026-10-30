import { useCallback, useEffect, useState } from 'react'

/**
 * Gọi một hàm API lấy danh sách, trả về dữ liệu + trạng thái tải + lỗi
 * + hàm nạp lại. Dùng cho hàng đợi kiểm duyệt và danh sách báo cáo.
 */
export function useModerationList(fetcher) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    setError('')
    try {
      setItems(await fetcher())
    } catch (requestError) {
      setError(requestError.detail || requestError.message)
    } finally {
      setLoading(false)
    }
  }, [fetcher])

  useEffect(() => {
    refresh()
  }, [refresh])

  return { items, loading, error, refresh }
}
