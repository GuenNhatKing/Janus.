import { useState } from 'react'

import { useNavigate } from 'react-router-dom'

import Icon from '@/shared/components/Icon'

const MY_VIDEOS = [
  { id: 1, title: 'Video demo 1', thumb: null },
  { id: 2, title: 'Video demo 2', thumb: null },
]

export default function EditVideoPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState('list')
  const [selectedVideo, setSelectedVideo] = useState(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [cover, setCover] = useState(null)

  function selectVideo(video) {
    setSelectedVideo(video)
    setTitle(video.title)
    setDescription('')
    setCover(null)
    setStep('edit')
  }

  function handleCover(e) {
    const file = e.target.files?.[0]
    if (file) {
      setCover(URL.createObjectURL(file))
    }
  }

  function submit(e) {
    e.preventDefault()
    navigate('/profile')
  }

  if (step === 'list') {
    return (
      <div className="page">
        <div className="page-head">
          <div>
            <span className="overline">Chỉnh sửa video</span>
            <h1>Video của tôi</h1>
            <p className="page-sub">Chọn video bạn đã tải lên để chỉnh sửa thông tin.</p>
          </div>
        </div>

        <section className="card">
          <header className="card-head">
            <div>
              <h2>Danh sách video</h2>
              <p className="card-sub">Chọn một video để cập nhật</p>
            </div>
          </header>
          <div className="card-body">
            <div className="video-list">
              {MY_VIDEOS.map((video) => (
                <button key={video.id} type="button" className="video-list-item" onClick={() => selectVideo(video)}>
                  <div className="video-list-thumb">
                    <Icon name="play" size={18} />
                  </div>
                  <div className="video-list-info">
                    <strong>{video.title}</strong>
                    <span>Chỉnh sửa</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </section>
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <span className="overline">Chỉnh sửa video</span>
          <h1>Chỉnh sửa thông tin video</h1>
          <p className="page-sub">Cập nhật tiêu đề, mô tả và ảnh bìa cho "{selectedVideo?.title}".</p>
        </div>
      </div>

      <form className="edit-video-grid" onSubmit={submit}>
        <section className="card">
          <header className="card-head">
            <div>
              <h2>Thông tin cơ bản</h2>
              <p className="card-sub">Điền thông tin hiển thị trên video</p>
            </div>
          </header>
          <div className="card-body form-stack">
            <label className="field">
              <span>Tiêu đề video</span>
              <input className="text-input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Nhập tiêu đề video" />
            </label>
            <label className="field">
              <span>Mô tả</span>
              <textarea className="text-input textarea" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Thêm mô tả cho video..." />
            </label>
          </div>
        </section>

        <section className="card">
          <header className="card-head">
            <div>
              <h2>Ảnh bìa</h2>
              <p className="card-sub">Chọn ảnh bìa hiển thị cho video</p>
            </div>
          </header>
          <div className="card-body">
            <div className="cover-upload">
              {cover ? <img src={cover} alt="Ảnh bìa" /> : <div className="cover-placeholder"><Icon name="film" size={26} /></div>}
              <label className="button ghost">
                <input type="file" accept="image/*" hidden onChange={handleCover} />
                Chọn ảnh bìa
              </label>
            </div>
          </div>
        </section>

        <div className="edit-actions">
          <button type="button" className="button ghost" onClick={() => setStep('list')}>Quay lại danh sách</button>
          <button type="button" className="button ghost" onClick={() => navigate(-1)}>Hủy</button>
          <button type="submit" className="button primary">Lưu thay đổi</button>
        </div>
      </form>
    </div>
  )
}
