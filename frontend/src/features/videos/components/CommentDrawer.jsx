import { useEffect, useState } from 'react'

import Icon from '@/shared/components/Icon'
import { useAuth } from '@/features/auth/AuthContext'

export default function CommentDrawer({ video, onClose }) {
  const { user, isAuthenticated } = useAuth()
  const [text, setText] = useState('')
  const [comments, setComments] = useState([
    { id: 1, user: 'user_demo', content: 'Video hay quá!', time: '2h' },
    { id: 2, user: 'moderator', content: 'Đã kiểm duyệt nội dung hợp lệ.', time: '1h' },
  ])

  useEffect(() => {
    setComments([
      { id: 1, user: 'user_demo', content: 'Video hay quá!', time: '2h' },
      { id: 2, user: 'moderator', content: 'Đã kiểm duyệt nội dung hợp lệ.', time: '1h' },
    ])
    setText('')
  }, [video.id])

  function handleSubmit(e) {
    e.preventDefault()
    const content = text.trim()
    if (!content) return
    const newComment = {
      id: Date.now(),
      user: user?.display_name || user?.email?.split('@')[0] || 'bạn',
      content,
      time: 'vừa xong',
      local: true,
    }
    setComments((prev) => [newComment, ...prev])
    setText('')
  }

  return (
    <div className="comment-overlay" onClick={onClose}>
      <div className="comment-drawer" onClick={(e) => e.stopPropagation()}>
        <header className="comment-header">
          <div className="comment-header-title">
            <strong>{comments.length} bình luận</strong>
          </div>
          <button type="button" className="comment-close" onClick={onClose} aria-label="Đóng">
            <Icon name="x" size={18} />
          </button>
        </header>

        <div className="comment-list">
          {comments.length === 0 ? (
            <div className="comment-empty">
              <p>Chưa có bình luận nào</p>
              <span>Hãy là người đầu tiên bình luận</span>
            </div>
          ) : (
            comments.map((comment) => (
              <div key={comment.id} className="comment-item">
                <div className="comment-avatar">{(comment.user || 'u').slice(0, 2).toUpperCase()}</div>
                <div className="comment-body">
                  <div className="comment-meta">
                    <span className="comment-user">@{comment.user}</span>
                    <span className="comment-time">{comment.time}</span>
                  </div>
                  <p className="comment-text">{comment.content}</p>
                </div>
              </div>
            ))
          )}
        </div>

        <form className="comment-form" onSubmit={handleSubmit}>
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={isAuthenticated ? 'Thêm bình luận...' : 'Đăng nhập để bình luận...'}
            className="comment-input"
            disabled={!isAuthenticated}
          />
          <button type="submit" className="comment-send" disabled={!isAuthenticated || !text.trim()}>
            Gửi
          </button>
        </form>
      </div>
    </div>
  )
}
