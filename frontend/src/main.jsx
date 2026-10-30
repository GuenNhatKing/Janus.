<<<<<<< HEAD
import React, { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

function Icon({ name, size = 18 }) {
  const shared = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true }
  if (name === 'play') return <svg {...shared} fill="currentColor" stroke="none"><path d="M8 5.8c0-.8.9-1.3 1.6-.9l9.1 5.2a2.2 2.2 0 0 1 0 3.8l-9.1 5.2c-.7.4-1.6-.1-1.6-.9V5.8Z"/></svg>
  if (name === 'upload') return <svg {...shared}><path d="M12 16V4m0 0L7 9m5-5 5 5"/><path d="M20 16v3a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-3"/></svg>
  if (name === 'film') return <svg {...shared}><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4m-4 6h4m10-6h4m-4 6h4"/></svg>
  if (name === 'check') return <svg {...shared}><path d="m5 12 4 4L19 6"/></svg>
  if (name === 'clock') return <svg {...shared}><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
  if (name === 'arrow') return <svg {...shared}><path d="M5 12h14m-6-6 6 6-6 6"/></svg>
  if (name === 'spark') return <svg {...shared}><path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z"/><path d="m19 15 .9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15Z"/></svg>
  return null
}

const pipeline = [
  { title: 'Tải video', detail: 'Kiểm tra tệp và thông tin video' },
  { title: 'Phân tích hình ảnh', detail: 'Quét khung hình đại diện' },
  { title: 'Phân tích âm thanh', detail: 'Kiểm tra tín hiệu âm thanh' },
  { title: 'Nhận dạng lời nói', detail: 'Tạo bản chép lời mẫu' },
  { title: 'Phân loại nội dung', detail: 'Gợi ý nhãn và điểm tin cậy' },
]

function AuthScreen({ onLogin }) {
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [success, setSuccess] = useState(false)
  const isRegister = mode === 'register'

  function switchMode(next) {
    setMode(next)
    setFeedback('')
    setSuccess(false)
    setUsername('')
    setEmail('')
    setPassword('')
  }

  function submit(event) {
    event.preventDefault()
    setFeedback('')
    setSuccess(false)
    if (isRegister) {
      const valid = username.trim() && /^[^\s@]+@gmail\.com$/i.test(email.trim()) && password
      if (!valid) { setFeedback('Vui lòng điền đủ thông tin và sử dụng địa chỉ Gmail hợp lệ.'); return }
      setSuccess(true)
      return
    }
    if (username.trim() === 'admin' && password === '123') { onLogin(); return }
    setFeedback('Thông tin chưa chính xác. Bạn thử lại nhé.')
  }

  return <main className="auth-page"><header className="auth-topbar"><a className="brand" href="#home"><span className="brand-icon"><Icon name="play" size={15}/></span>Janus</a><span>Chia sẻ điều bạn yêu.</span></header><section className="auth-box"><div className="auth-mark"><Icon name="play" size={18}/></div><p className="auth-eyebrow">{isRegister?'TẠO TÀI KHOẢN JANUS':'CHÀO MỪNG BẠN ĐẾN VỚI JANUS'}</p><h1>{isRegister?'Tham gia Janus':'Đăng nhập'}</h1><p className="auth-subtitle">{isRegister?'Tạo tài khoản để bắt đầu chia sẻ video.':'Tiếp tục khám phá những video bạn yêu thích.'}</p><form className="auth-form" onSubmit={submit} noValidate><label className="auth-field"><span>{isRegister?'Tên người dùng':'Email hoặc tên người dùng'}</span><input autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} placeholder={isRegister?'Nhập tên người dùng':'Nhập email hoặc tên người dùng'}/></label>{isRegister&&<label className="auth-field"><span>Địa chỉ Gmail</span><input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="ban@gmail.com"/></label>}<label className="auth-field"><span>Mật khẩu</span><div className="auth-password"><input type={showPassword?'text':'password'} autoComplete={isRegister?'new-password':'current-password'} value={password} onChange={e=>setPassword(e.target.value)} placeholder={isRegister?'Tạo mật khẩu':'Nhập mật khẩu'}/><button type="button" onClick={()=>setShowPassword(v=>!v)} aria-label={showPassword?'Ẩn mật khẩu':'Hiện mật khẩu'}>{showPassword?'Ẩn':'Hiện'}</button></div></label>{feedback&&<p className="auth-feedback" role="alert">{feedback}</p>}{success&&<p className="auth-success" role="status">Đăng ký thành công trên bản demo. Bạn có thể đăng nhập.</p>}<button className="auth-submit" type="submit">{isRegister?'Tạo tài khoản':'Đăng nhập'}<Icon name="arrow" size={16}/></button></form><div className="auth-toggle">{isRegister?'Đã có tài khoản?':'Bạn mới đến Janus?'}<button onClick={()=>switchMode(isRegister?'login':'register')}>{isRegister?'Đăng nhập':'Tạo tài khoản'}</button></div>{!isRegister&&<p className="demo-login-hint">Tài khoản demo: <strong>admin</strong> · Mật khẩu: <strong>123</strong></p>}</section><footer className="auth-footer">© 2026 Janus <span>Giao diện demo</span></footer></main>
}

function App() {
  const [screen, setScreen] = useState('upload')
  const [authenticated, setAuthenticated] = useState(false)
  const [file, setFile] = useState(null)
  const [videoUrl, setVideoUrl] = useState('')
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [step, setStep] = useState(-1)
  const [finished, setFinished] = useState(false)
  const inputRef = useRef(null)

  useEffect(() => {
    if (!file) { setVideoUrl(''); return }
    const url = URL.createObjectURL(file)
    setVideoUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  useEffect(() => {
    if (screen !== 'testing' || finished) return
    if (step >= pipeline.length - 1) {
      const timer = window.setTimeout(() => setFinished(true), 800)
      return () => window.clearTimeout(timer)
    }
    const timer = window.setTimeout(() => setStep(current => current + 1), step < 0 ? 350 : 1050)
    return () => window.clearTimeout(timer)
  }, [screen, step, finished])

  function acceptFile(nextFile) {
    if (!nextFile) return
    setError('')
    if (!nextFile.name.toLowerCase().endsWith('.mp4') || (nextFile.type && nextFile.type !== 'video/mp4')) {
      setFile(null)
      setError('Vui lòng chọn video định dạng MP4.')
      return
    }
    if (nextFile.size > 50 * 1024 * 1024) {
      setFile(null)
      setError('Video vượt quá dung lượng tối đa 50 MB.')
      return
    }
    setFile(nextFile)
  }

  function startTest() {
    if (!file) return
    setStep(-1)
    setFinished(false)
    setScreen('testing')
  }

  function resetUpload() {
    setFile(null)
    setError('')
    setScreen('upload')
    setStep(-1)
    setFinished(false)
  }

  const completedSteps = finished ? pipeline.length : Math.max(step, 0)

  if (!authenticated) return <AuthScreen onLogin={() => setAuthenticated(true)} />

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a href="#home" className="brand"><span className="brand-icon"><Icon name="play" size={15}/></span>Dut<span>Tok</span></a>
        <div className="side-label">KHÔNG GIAN LÀM VIỆC</div>
        <nav className="side-nav" aria-label="Điều hướng chính">
          <button className={screen === 'upload' ? 'nav-item active' : 'nav-item'} onClick={resetUpload}><Icon name="upload"/><span>Tải video</span></button>
          <button className={screen === 'testing' ? 'nav-item active' : 'nav-item'} onClick={() => file && setScreen('testing')}><Icon name="film"/><span>Kiểm thử</span>{file && <span className="nav-indicator"/>}</button>
        </nav>
        <div className="sidebar-bottom"><span className="online-dot"/>Chế độ mô phỏng <span className="version">v0.1</span></div>
      </aside>

      <main className="main-area">
        <header className="topbar"><div className="breadcrumb">Janus <span>/</span> <strong>{screen === 'upload' ? 'Tải video' : 'Kiểm thử mô hình'}</strong></div><div className="topbar-right"><span className="demo-pill"><i/>Bản demo</span><div className="avatar">JA</div></div></header>

        {screen === 'upload' ? <section className="workspace upload-workspace">
          <div className="page-title-row"><div><p className="overline">QUY TRÌNH KIỂM THỬ</p><h1>Tải video lên</h1><p className="page-subtitle">Chọn video để xem thử luồng phân tích nội dung của Janus.</p></div><span className="step-chip">Bước 01 <span>/ 02</span></span></div>
          <div className="upload-layout">
            <div className="upload-main">
              <div className="section-caption"><span>01</span><h2>Tệp video</h2></div>
              {!file ? <div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={e => {e.preventDefault();setDragging(true)}} onDragLeave={() => setDragging(false)} onDrop={e => {e.preventDefault();setDragging(false);acceptFile(e.dataTransfer.files?.[0])}} onClick={() => inputRef.current?.click()} role="button" tabIndex={0} onKeyDown={e => {if(e.key==='Enter'||e.key===' '){e.preventDefault();inputRef.current?.click()}}}>
                <input ref={inputRef} type="file" accept="video/mp4,.mp4" hidden onChange={e => acceptFile(e.target.files?.[0])}/>
                <div className="upload-icon"><Icon name="upload" size={22}/></div><h3>Kéo video vào đây</h3><p>hoặc <button type="button" onClick={e => {e.stopPropagation();inputRef.current?.click()}}>chọn tệp từ thiết bị</button></p><span className="file-rules">MP4 · Tối đa 50 MB</span>
              </div> : <div className="selected-file"><div className="file-preview"><video src={videoUrl} controls playsInline/><button className="replace-file" onClick={() => inputRef.current?.click()}>Đổi video</button><input ref={inputRef} type="file" accept="video/mp4,.mp4" hidden onChange={e => acceptFile(e.target.files?.[0])}/></div><div className="file-meta"><div><strong>{file.name}</strong><span>{(file.size / (1024 * 1024)).toFixed(1)} MB · MP4</span></div><span className="valid-badge"><Icon name="check" size={14}/> Hợp lệ</span></div></div>}
              {error && <p className="upload-error" role="alert">{error}</p>}
              <div className="caption-field"><label htmlFor="caption">Mô tả video <span>Không bắt buộc</span></label><input id="caption" placeholder="Video này nói về điều gì?" /></div>
              <div className="upload-actions"><span><Icon name="clock" size={15}/> Kết quả mô phỏng trong vài giây</span><button className="primary-button" disabled={!file} onClick={startTest}>Bắt đầu kiểm thử <Icon name="arrow" size={16}/></button></div>
            </div>
            <aside className="info-panel"><div className="info-icon"><Icon name="spark" size={19}/></div><h3>Kiểm thử an toàn</h3><p>Video được xem trước ngay trên thiết bị. Luồng phân tích phía dưới là dữ liệu mô phỏng để minh họa giao diện.</p><div className="info-divider"/><div className="info-detail"><span>Định dạng</span><strong>MP4</strong></div><div className="info-detail"><span>Dung lượng tối đa</span><strong>50 MB</strong></div><div className="info-detail"><span>Xử lý</span><strong>Trên trình duyệt</strong></div></aside>
          </div>
        </section> : <section className="workspace test-workspace">
          <div className="page-title-row test-title-row"><div><p className="overline">QUY TRÌNH KIỂM THỬ <span className="mock-label">MÔ PHỎNG</span></p><h1>Phân tích video</h1><p className="page-subtitle">Theo dõi từng bước xử lý và kết quả các mô hình minh họa.</p></div><button className="back-button" onClick={resetUpload}>← <span>Chọn video khác</span></button></div>
          <div className="test-grid">
            <div className="test-primary"><div className="video-stage">{videoUrl ? <video src={videoUrl} controls playsInline/> : <div className="video-placeholder"><Icon name="film" size={32}/><span>Chưa có video</span></div>}<div className="stage-tag"><i/>{finished ? 'Đã hoàn tất' : 'Đang chạy kiểm thử'}</div></div><div className="video-details"><div><strong>{file?.name || 'Video kiểm thử'}</strong><span>{file ? `${(file.size / (1024 * 1024)).toFixed(1)} MB · MP4` : 'Video minh họa'}</span></div><span className="mock-tag"><Icon name="spark" size={13}/> Kết quả giả lập</span></div>
              <div className="model-results"><div className="section-caption"><span>02</span><h2>Độ tin cậy mô hình</h2><span className="section-hint">Điểm minh họa · 0–100%</span></div><div className="model-cards">
                {[{name:'Hình ảnh',value:92,color:'coral',state:finished||step>=1},{name:'Âm thanh',value:78,color:'blue',state:finished||step>=2},{name:'Lời nói',value:86,color:'purple',state:finished||step>=3}].map(model=><div className={`model-card ${model.state?'':'pending'}`} key={model.name}><div className="model-card-top"><span>{model.name}</span><span className={`level ${model.value>=85?'high':'medium'}`}>{model.value>=85?'CAO':'TRUNG BÌNH'}</span></div><div className="confidence-number">{model.state?model.value:'—'}<small>{model.state?'%':'đang chờ'}</small></div><div className="confidence-track"><i className={model.color} style={{width:model.state?`${model.value}%`:'0%'}}/></div></div>)}
              </div><div className="label-result"><div><span className="result-label-caption">NHÃN ĐỀ XUẤT</span><strong>{finished ? 'An toàn' : step >= 4 ? 'Đang tổng hợp kết quả…' : 'Chờ phân loại'}</strong></div><span className={`label-chip ${finished?'safe':''}`}>{finished?'Safe':'—'}</span></div></div>
            </div>
            <aside className="log-panel"><div className="log-heading"><div><span className="log-live"><i/>{finished?'HOÀN TẤT':'NHẬT KÝ TRỰC TIẾP'}</span><h2>Tiến trình xử lý</h2></div><span className="log-count">{finished?pipeline.length:completedSteps}/{pipeline.length}</span></div><div className="progress-line"><i style={{width:`${(completedSteps/pipeline.length)*100}%`}}/></div><div className="log-list">{pipeline.map((item,index)=>{const done=finished||index<step;const active=!finished&&index===step;return <div className={`log-row ${done?'done':''} ${active?'current':''}`} key={item.title}><span className="log-node">{done?<Icon name="check" size={12}/>:active?<span className="pulse-dot"/>:<span>{String(index+1).padStart(2,'0')}</span>}</span><div className="log-copy"><strong>{item.title}</strong><span>{active?'Đang xử lý…':done?item.detail:'Đang chờ'}</span></div><time>{done?'✓':active?'…':'—'}</time></div>})}</div><div className="log-notice"><span>i</span><p>Nhật ký và điểm số này là dữ liệu mô phỏng. Chưa có mô hình AI thật trong luồng kiểm thử.</p></div><div className="transcript"><div className="transcript-title"><span>BẢN CHÉP LỜI</span><span className="mock-label">MẪU</span></div><p>{finished?'Bản chép lời minh họa sẽ xuất hiện tại đây.':'Xuất hiện sau bước nhận dạng lời nói.'}</p></div></aside>
          </div>
          {finished && <div className="complete-banner"><span className="complete-check"><Icon name="check" size={17}/></span><span><strong>Kiểm thử hoàn tất</strong><small>Kết quả trên màn hình chỉ dùng để minh họa trải nghiệm.</small></span><button onClick={resetUpload}>Tải video khác <Icon name="arrow" size={15}/></button></div>}
        </section>}
        <footer className="app-footer"><span>Janus · Không gian kiểm thử nội dung</span><span>Dữ liệu demo, không phải kết quả kiểm duyệt</span></footer>
      </main>
    </div>
  )
}

createRoot(document.getElementById('root')).render(<App />)
=======
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './app/App'
import './styles/base.css'
import './styles/layout.css'
import './styles/components.css'
import './styles/feed.css'
import './styles/upload.css'
import './styles/auth.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
>>>>>>> 2721562fb5885c2c0682273df534f5a8031c685a
