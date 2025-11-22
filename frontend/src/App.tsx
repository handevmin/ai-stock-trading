import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import './App.css'

function App() {
  return (
    <Router>
      <div className="App">
        <header className="main-header">
          <div className="header-container">
            <div className="logo-section">
              <div className="logo-icon">
                <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="logoGradient" x1="0" y1="0" x2="40" y2="40">
                      <stop offset="0%" stopColor="#3b82f6"/>
                      <stop offset="50%" stopColor="#6366f1"/>
                      <stop offset="100%" stopColor="#8b5cf6"/>
                    </linearGradient>
                    <linearGradient id="logoGradient2" x1="0" y1="0" x2="40" y2="40">
                      <stop offset="0%" stopColor="#60a5fa"/>
                      <stop offset="100%" stopColor="#3b82f6"/>
                    </linearGradient>
                    <radialGradient id="logoGlow" cx="50%" cy="50%">
                      <stop offset="0%" stopColor="#ffffff" stopOpacity="1"/>
                      <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.3"/>
                    </radialGradient>
                  </defs>
                  {/* 배경 원형 글로우 */}
                  <circle cx="20" cy="20" r="18" fill="url(#logoGradient)" opacity="0.15"/>
                  {/* 메인 원형 */}
                  <circle cx="20" cy="20" r="14" fill="url(#logoGradient2)" opacity="0.8" stroke="url(#logoGradient)" strokeWidth="1.5"/>
                  {/* 내부 원형 */}
                  <circle cx="20" cy="20" r="10" fill="url(#logoGlow)" opacity="0.9"/>
                  {/* 번개/전기 모양 - 자동화 상징 */}
                  <path d="M18 12L14 20H18L16 28L22 20H18L20 12L18 12Z" fill="white" opacity="0.95"/>
                  {/* 작은 번개 */}
                  <path d="M20 14L18 18H20L19 22L22 18H20L21 14L20 14Z" fill="url(#logoGradient)" opacity="0.8"/>
                </svg>
              </div>
              <div className="logo-text">
                <span className="logo-title">AutoTrade</span>
                <span className="logo-subtitle">자동매매 플랫폼</span>
              </div>
            </div>
            <div className="header-actions">
              <div className="status-indicator">
                <span className="status-dot"></span>
                <span className="status-text">연결됨</span>
              </div>
            </div>
          </div>
        </header>
        <main className="App-main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App


