import { useEffect, useState } from 'react'
import { Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import {
  ChevronDown,
  FileText,
  MessageSquare,
  Plus,
  Settings,
} from 'lucide-react'
import * as api from './api.js'
import logo from './assets/universe-ai-logo.png'

import Assistant from './views/Assistant.jsx'
import PortalView from './views/PortalView.jsx'

// The demo boots straight into a local session without a login page.
const DEMO = { student_id: 'S2023001', email: 'arjun.mehta@campus.edu' }

export default function App() {
  const navigate = useNavigate()
  const location = useLocation()
  const [student, setStudent] = useState(null)
  const [bootError, setBootError] = useState(null)
  const [history, setHistory] = useState([])
  useEffect(() => {
    const signIn = () =>
      api
        .login(DEMO.student_id, DEMO.email)
        .then(({ token, student }) => {
          api.setToken(token)
          setStudent(student)
          return api.fetchConversations().then(setHistory)
        })
        .catch((e) => setBootError(e.message))

    if (api.getToken()) {
      api
        .fetchMe()
        .then((me) => {
          setStudent(me)
          return api.fetchConversations().then(setHistory)
        })
        .catch(() => {
          api.clearToken()
          return signIn()
        })
    } else {
      signIn()
    }
  }, [])

  useEffect(() => {
    const onRejection = (e) => {
      if (e.reason instanceof api.AuthError) {
        api.clearToken()
        api
          .login(DEMO.student_id, DEMO.email)
          .then(({ token, student }) => {
            api.setToken(token)
            setStudent(student)
            return api.fetchConversations().then(setHistory)
          })
          .catch((err) => setBootError(err.message))
      }
    }
    window.addEventListener('unhandledrejection', onRejection)
    return () => window.removeEventListener('unhandledrejection', onRejection)
  }, [])

  if (!student) {
    return (
      <div className="boot">
        {bootError ? (
          <p className="banner" style={{ margin: 0 }}>{bootError}</p>
        ) : (
          <span className="label">Loading…</span>
        )}
      </div>
    )
  }

  return (
    <div className="app">
      <aside className="workspace-sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark">
            <img src={logo} alt="Universe AI" />
          </div>
          <div className="brand-lines">
            <span className="wordmark">Universe AI</span>
            <span className="kicker">Local Multi-Agent</span>
          </div>
        </div>

        <button className="new-chat" type="button" onClick={() => navigate('/assistant', { state: { newConversation: true } })}>
          <span><Plus size={14} /> New Chat</span>
          <kbd>⌘K</kbd>
        </button>

        <div className="sidebar-section">
          <span className="sidebar-label">Conversation History</span>
          {history.length === 0 && <span className="history-empty">No conversations yet</span>}
          {history.map((item) => (
            <button className="history-item" key={item.id} onClick={() => navigate('/assistant', { state: { conversationId: item.id } })}>
              <MessageSquare size={13} /><span>{item.title}</span><small>{item.message_count} msg</small>
            </button>
          ))}
        </div>

        <div className="sidebar-section portals">
          <span className="sidebar-label">Academic Portals</span>
          <button className={`portal-item ${location.pathname === '/academics' ? 'selected' : ''}`} onClick={() => navigate('/academics')}><FileText size={13} /> Academics <ChevronDown size={12} /></button>
          <button className={`portal-item ${location.pathname === '/events' ? 'selected' : ''}`} onClick={() => navigate('/events')}><FileText size={13} /> Events <ChevronDown size={12} /></button>
          <button className={`portal-item ${location.pathname === '/placements' ? 'selected' : ''}`} onClick={() => navigate('/placements')}><FileText size={13} /> Placement Cell <ChevronDown size={12} /></button>
          <button className={`portal-item ${location.pathname === '/services' ? 'selected' : ''}`} onClick={() => navigate('/services')}><FileText size={13} /> Student Services <ChevronDown size={12} /></button>
        </div>

        <div className="sidebar-footer">
          <div className="student-chip">
            <span className="student-avatar">{student.name?.slice(0, 1) || 'A'}</span>
            <span className="student-copy">
              <strong>{student.name || 'Student'}</strong>
              <small>{student.department || 'Student workspace'}</small>
            </span>
            <Settings size={14} />
          </div>
          <span className="privacy-note">Enterprise Local Sandbox · Private</span>
        </div>
      </aside>

      <div className="workspace">
        <header className="command-header">
          <div className="crumb"><span className="header-mark"><img src={logo} alt="Universe AI" /></span><strong>Universe AI<br /><small>Assistant workspace</small></strong></div>
          <button className="new-conversation" onClick={() => navigate('/assistant', { state: { newConversation: true } })}><Plus size={15} /> <span>New conversation</span></button>
        </header>
        <main className="main is-assistant">
          <Routes>
            <Route path="/" element={<Assistant />} />
            <Route path="/assistant" element={<Assistant onHistoryChange={() => api.fetchConversations().then(setHistory)} />} />
            <Route path="/academics" element={<PortalView section="academics" />} />
            <Route path="/events" element={<PortalView section="events" />} />
            <Route path="/placements" element={<PortalView section="placements" />} />
            <Route path="/services" element={<PortalView section="services" />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
