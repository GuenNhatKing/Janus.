import { useState } from 'react'

import { useNavigate } from 'react-router-dom'

import Icon from '@/shared/components/Icon'

export default function EditVideoPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [cover, setCover] = useState(null)

  function handleFile(e) {
    const file = e.target.files?.[0]
    if (file) {
      setCover(URL.createObjectURL(file))
    }
  }

  function submit(e) {
    e.preventDefault()
    navigate('/profile')
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <span className="overline">Chỉnh sửa video</span>
          <h1>Chỉnh sửa thông tin video</h1>
          <p className="page-sub">Cập nhật tiêu đề, mô tả và ảnh bìa cho video của bạn.</p>
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
                <input type="file" accept="image/*" hidden onChange={handleFile} />
                Chọn ảnh bìa
              </label>
            </div>
          </div>
        </section>

        <div className="edit-actions">
          <button type="button" className="button ghost" onClick={() => navigate(-1)}>Hủy</button>
          <button type="submit" className="button primary">Lưu thay đổi</button>
        </div>
      </form>
    </div>
  )
}
