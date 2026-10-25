import React, { useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

function Icon({ name, size = 18, ...props }) {
  const shared = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', ...props }
  if (name === 'eye') return <svg {...shared}><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></svg>
  if (name === 'eyeOff') return <svg {...shared}><path d="m3 3 18 18M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 5.2A10.7 10.7 0 0 1 12 5c6.4 0 10 7 10 7a15.7 15.7 0 0 1-3 3.9M6.2 6.2C3.5 8.1 2 12 2 12s3.6 7 10 7c1 0 2-.2 2.9-.5"/></svg>
  if (name === 'arrow') return <svg {...shared}><path d="M5 12h14M13 6l6 6-6 6"/></svg>
  if (name === 'play') return <svg {...shared} fill="currentColor" stroke="none"><path d="M8 5.8c0-.8.9-1.3 1.6-.9l9.1 5.2a2.2 2.2 0 0 1 0 3.8l-9.1 5.2c-.7.4-1.6-.1-1.6-.9V5.8Z"/></svg>
  return null
}

function App() {
  const [frame, setFrame] = useState('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loginState, setLoginState] = useState(null)
  const [registrationSuccess, setRegistrationSuccess] = useState(null)
  const [toast, setToast] = useState(false)
  const isRegister = frame === 'register'

  function switchFrame(next) {
    setFrame(next)
    setLoginState(null)
    setRegistrationSuccess(null)
    setUsername('')
    setEmail('')
    setPassword('')
  }

  function handleLogin(event) {
    event.preventDefault()
    setLoginState(username.trim() === 'admin' && password === '123')
  }

  function handleRegister(event) {
    event.preventDefault()
    setToast(false)
    const emailIsValid = /^[^\s@]+@gmail\.com$/i.test(email.trim())
    const valid = Boolean(username.trim() && email.trim() && password && emailIsValid)
    setRegistrationSuccess(valid)
    if (valid) {
      window.setTimeout(() => setToast(true), 80)
      window.setTimeout(() => setToast(false), 3600)
    }
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="#home" aria-label="DutTok — trang chủ"><span className="brand-icon"><Icon name="play" size={15} /></span><span>Dut<span className="brand-accent">Tok</span></span></a>
        <span className="topbar-note">Câu chuyện của bạn, bắt đầu từ đây.</span>
      </header>

      <section className="auth-area">
        <div className="auth-heading">
          <span className="heading-kicker"><i />{isRegister ? 'TẠO TÀI KHOẢN DUTTOK' : 'CHÀO MỪNG BẠN ĐẾN VỚI DUTTOK'}</span>
          <h1>{isRegister ? 'Tham gia cùng DutTok.' : 'Đăng nhập'}</h1>
          <p>{isRegister ? 'Tạo tài khoản để chia sẻ những khoảnh khắc của bạn.' : 'Tiếp tục khám phá những video bạn yêu thích.'}</p>
        </div>

        <form className="auth-form" onSubmit={isRegister ? handleRegister : handleLogin} noValidate>
          <div className="fields">
            <label className="field"><span>{isRegister ? 'Tên người dùng' : 'Email hoặc tên người dùng'}</span><input autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} placeholder={isRegister ? 'Nhập tên người dùng' : 'Nhập email hoặc tên người dùng'} /></label>
            {isRegister && <label className="field"><span>Địa chỉ Gmail</span><input type="email" autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="ban@gmail.com" /></label>}
            <label className="field"><span>Mật khẩu</span><div className="password-wrap"><input type={showPassword ? 'text' : 'password'} autoComplete={isRegister ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} placeholder={isRegister ? 'Tạo mật khẩu' : 'Nhập mật khẩu'} /><button className="visibility-toggle" type="button" onClick={() => setShowPassword(v => !v)} aria-label={showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}><Icon name={showPassword ? 'eyeOff' : 'eye'} size={18} /></button></div></label>
          </div>

          {!isRegister && <div className="forgot-row"><span /></div>}
          {!isRegister && loginState === false && <p className="feedback" role="alert">Thông tin chưa chính xác. Bạn thử lại nhé.</p>}
          {!isRegister && loginState === true && <p className="success-note" role="status">Đăng nhập thành công. Chào mừng bạn trở lại DutTok!</p>}
          {isRegister && registrationSuccess === false && <p className="feedback" role="alert">Vui lòng điền đủ thông tin và sử dụng địa chỉ Gmail hợp lệ.</p>}
          {isRegister && registrationSuccess === true && <p className="success-note" role="status">Thông tin đã sẵn sàng — chào mừng bạn đến với DutTok.</p>}

          <button className="submit-button" type="submit">{isRegister ? 'Tạo tài khoản' : 'Đăng nhập'}<Icon name="arrow" size={17} /></button>
        </form>

        <div className="auth-switch">{isRegister ? 'Đã có tài khoản?' : 'Bạn mới đến DutTok?'}<button type="button" onClick={() => switchFrame(isRegister ? 'login' : 'register')}>{isRegister ? 'Đăng nhập' : 'Tạo tài khoản'}</button></div>
      </section>

      <footer className="page-footer"><span>© 2025 DutTok</span><span>Chia sẻ điều bạn yêu.</span></footer>
      <div className={`toast ${toast ? 'toast-visible' : ''}`} role="status" aria-live="polite"><span className="toast-check">✓</span><span><strong>Tài khoản đã được tạo</strong><small>Bạn đã sẵn sàng cho video đầu tiên.</small></span><button type="button" aria-label="Đóng thông báo" onClick={() => setToast(false)}>×</button></div>
    </main>
  )
}

createRoot(document.getElementById('root')).render(<App />)
