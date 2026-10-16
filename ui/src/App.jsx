import { useEffect, useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import { Hexagon } from 'lucide-react'
import * as api from './api.js'

import Assistant from './views/Assistant.jsx'

// The demo boots straight into a local session without a login page.
const DEMO = { student_id: 'S2023001', email: 'arjun.mehta@campus.edu' }

export default function App() {
  const [student, setStudent] = useState(null)
  const [bootError, setBootError] = useState(null)
  useEffect(() => {
    const signIn = () =>
      api
        .login(DEMO.student_id, DEMO.email)
        .then(({ token, student }) => {
          api.setToken(token)
          setStudent(student)
        })
        .catch((e) => setBootError(e.message))

    if (api.getToken()) {
      api
        .fetchMe()
        .then(setStudent)
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
      <header className="masthead">
          <div className="mark">
            <Hexagon size={18} />
          </div>
          <div className="masthead-lines">
            <span className="wordmark">Universe AI</span>
            <span className="kicker">Multi-agent operations assistant</span>
          </div>

          <div className="masthead-spacer" />
          <span className="local-badge">Local agent workspace</span>
        </header>

        <main className="main is-assistant">
          <Routes>
            <Route path="/" element={<Assistant />} />
            <Route path="/assistant" element={<Assistant />} />
          </Routes>
        </main>
      </div>
  )
}
