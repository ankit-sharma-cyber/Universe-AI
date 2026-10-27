import { Fragment, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import {
  Bot,
  GraduationCap,
  Briefcase,
  Calendar,
  Building2,
  BookOpen,
  ChevronRight,
} from 'lucide-react'
import * as api from '../api.js'
import Markdown from '../components/Markdown.jsx'
import Composer from '../components/Composer.jsx'
import logo from '../assets/universe-ai-logo.png'

const EXIT_MS = 160

// Roster mirrors the reference mockup: icon + name + status dot.
// Each entry maps to one or more backend trace nodes so statuses are live.
const ROSTER = [
  { key: 'orchestrator', label: 'Orchestrator', detail: 'Routing brain', icon: Bot },
  { key: 'academic', label: 'Academic', detail: 'Courses & policy', icon: GraduationCap },
  { key: 'placement', label: 'Placement', detail: 'Eligibility & drives', icon: Briefcase },
  { key: 'events', label: 'Events', detail: 'Lookup & registration', icon: Calendar },
  { key: 'student_services', label: 'Student Services', detail: 'Campus support', icon: Building2 },
  { key: 'knowledge', label: 'Knowledge RAG', detail: 'Policy retrieval', icon: BookOpen },
]

const SUGGESTIONS = [
  {
    label: 'Summarize attendance policy',
    hint: 'Academic agent + policy RAG',
    icon: GraduationCap,
  },
  {
    label: 'Find upcoming college events',
    hint: 'Events agent + mock lookup tool',
    icon: Calendar,
  },
  {
    label: 'Check placement eligibility',
    hint: 'Placement agent + student context',
    icon: Briefcase,
  },
  {
    label: 'Find student services help',
    hint: 'Student services agent + FAQs',
    icon: Building2,
  },
]

const NODE_TO_ROSTER = {
  planner: 'orchestrator',
  approval: 'orchestrator',
  merge: 'orchestrator',
  academic: 'academic',
  placement: 'placement',
  events: 'events',
  student_services: 'student_services',
  communication: 'communication',
  notification_calendar: 'events',
  knowledge: 'knowledge',
}

const NODE_LABEL = {
  planner: 'Orchestrator',
  approval: 'Orchestrator',
  merge: 'Orchestrator',
  academic: 'Academic',
  placement: 'Placement',
  events: 'Events',
  student_services: 'Student Svcs',
  communication: 'Student Services',
  notification_calendar: 'Events',
  knowledge: 'Knowledge Agent · RAG',
}

export default function Assistant({ onHistoryChange }) {
  const location = useLocation()
  const [conversationId, setConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [run, setRun] = useState(null)
  const [pending, setPending] = useState(null)
  const [pendingLeaving, setPendingLeaving] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [openTraces, setOpenTraces] = useState({})
  const scrollRef = useRef(null)
  const lastAgentRef = useRef(null)
  const composerRef = useRef(null)

  useEffect(() => {
    if (location.state?.newConversation) {
      setConversationId(null)
      setMessages([])
      setRun(null)
      window.history.replaceState({}, '')
    }
    if (location.state?.conversationId) {
      api.fetchConversation(location.state.conversationId).then((conversation) => {
        setConversationId(conversation.id)
        setMessages(conversation.messages.map((message) => ({
          role: message.role,
          content: message.content,
          intent: message.intent,
          trace: message.trace || [],
        })))
        window.history.replaceState({}, '')
      }).catch((e) => setError(e.message))
    }
  }, [location.state])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    if (!messages.length && !busy && !pending) {
      el.scrollTop = 0
      return
    }
    const last = messages[messages.length - 1]
    if (last?.role === 'assistant' && lastAgentRef.current) {
      el.scrollTop = lastAgentRef.current.offsetTop - 14
    } else {
      el.scrollTop = el.scrollHeight
    }
  }, [messages, pending, busy])

  const applyResult = (result) => {
    setConversationId(result.conversation_id)
    onHistoryChange?.()
    setRun({ intent: result.intent, plan: result.plan, trace: result.trace })
    if (result.pending_approval) {
      setPending(result.pending_approval)
      return
    }
    setPending(null)
    setMessages((prev) => [
      ...prev,
      {
        role: 'assistant',
        content: result.final,
        intent: result.intent,
        error: result.error,
        trace: result.trace,
      },
    ])
  }

  const send = async (text) => {
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setBusy(true)
    try {
      applyResult(await api.sendChat({ request: text, conversation_id: conversationId }))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const decide = async (approved) => {
    if (!pending || pendingLeaving) return
    setPendingLeaving(true)
    setTimeout(() => {
      setPending(null)
      setPendingLeaving(false)
    }, EXIT_MS)
    setBusy(true)
    try {
      applyResult(await api.sendApproval(conversationId, approved))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const toggleTrace = (i) =>
    setOpenTraces((prev) => ({ ...prev, [i]: !prev[i] }))

  // ---- live roster statuses ----------------------------------------
  const plan = run?.plan || []
  const trace = run?.trace || []
  const counts = trace.reduce((acc, t) => ({ ...acc, [t.node]: (acc[t.node] || 0) + 1 }), {})
  const executedNode = (node) => (counts[node] || 0) > (plan.includes(node) ? 1 : 0)
  const executedRoster = new Set(
    trace.filter((t) => executedNode(t.node)).map((t) => NODE_TO_ROSTER[t.node]),
  )
  const plannedRoster = new Set(plan.map((n) => NODE_TO_ROSTER[n]))
  const orchState = busy ? 'running' : run ? 'done' : 'idle'
  const orchText = busy ? 'Orchestrator working' : run ? 'Orchestrator done' : 'Orchestrator idle'

  const rosterStatus = (key) => {
    if (busy) return plannedRoster.has(key) || key === 'orchestrator' ? 'active' : 'idle'
    return executedRoster.has(key) ? 'done' : 'idle'
  }

  // tag above an assistant bubble = the agents that actually responded
  const agentsFor = (msg) => {
    if (!msg.trace?.length) return msg.intent || ''
    const keys = [
      ...new Set(
        msg.trace.filter((t) => executedNode(t.node)).map((t) => NODE_LABEL[t.node]),
      ),
    ]
    return keys.length ? keys.join(' · ') : ''
  }

  const route = ['planner', ...plan]

  return (
    <section className="assistant">
      <header className="assistant-head">
        <span className="head-mark">
          <img src={logo} alt="Universe AI" />
        </span>
        <div className={`orchestrator-state ${orchState}`}>
          <span className="dot" aria-hidden="true" />
          <span>{orchText}</span>
        </div>
      </header>

      <div className="assistant-body">
        {/* Agent crew — live status panel */}
        <aside className="a-side">
          <p className="side-title">Agent crew</p>
          <div className="crew">
            {ROSTER.map(({ key, label, detail, icon: Icon }) => {
              const st = rosterStatus(key)
              return (
                <div key={key} className={`crew-row ${st}`}>
                  <span className="crew-icon">
                    <Icon size={13} aria-hidden="true" />
                  </span>
                  <span className="crew-copy">
                    <span className="crew-name">{label}</span>
                    <span className="crew-detail">{detail}</span>
                  </span>
                  <span className="roster-dot" aria-hidden="true" />
                </div>
              )
            })}
          </div>

          {route.length > 1 && (
            <>
              <p className="side-title">Route</p>
              <div className="route">
                {route.map((n, i) => (
                  <Fragment key={i}>
                    {i > 0 && <ChevronRight size={10} className="route-arrow" aria-hidden="true" />}
                    <span className={`route-node ${i === 0 ? 'is-planner' : ''}`}>
                      {(NODE_LABEL[n] || n).split('·')[0].trim()}
                    </span>
                  </Fragment>
                ))}
              </div>
            </>
          )}
        </aside>

        {/* Conversation */}
        <div className="a-main">
          <div className="chat-scroll" ref={scrollRef}>
            {messages.length === 0 && !busy && !pending && (
              <div className="hero">
                <div className="hero-mark">
                  <img src={logo} alt="Universe AI" />
                </div>
                <h2 className="hero-title">Ask Universe AI</h2>
                <p className="hero-sub">
                  The orchestrator routes your request to academic, placement, events, or
                  student services agents, then combines tools, RAG, and memory into one answer.
                </p>
                <div className="hero-suggest">
                  {SUGGESTIONS.map(({ label, hint, icon: Icon }) => (
                    <button
                      key={label}
                      className="suggest"
                      onClick={() => composerRef.current?.fill(label)}
                    >
                      <span className="suggest-icon">
                        <Icon size={15} aria-hidden="true" />
                      </span>
                      <span className="suggest-main">
                        <span className="suggest-label">{label}</span>
                        <span className="suggest-hint">{hint}</span>
                      </span>
                      <ChevronRight size={14} className="suggest-arrow" aria-hidden="true" />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {error && <div className="banner">{error}</div>}

            {messages.map((msg, i) => (
              <div
                key={i}
                className={`msg ${msg.role === 'user' ? 'user' : 'agent'}`}
                ref={i === messages.length - 1 && msg.role === 'assistant' ? lastAgentRef : null}
              >
                {msg.role === 'agent' && (
                  <span className="msg-avatar">
                    <Bot size={14} aria-hidden="true" />
                  </span>
                )}
                <div className="msg-col">
                  {msg.role !== 'user' && agentsFor(msg) && (
                    <span className="msg-tag">{agentsFor(msg)}</span>
                  )}
                  <div className={`bubble ${msg.error ? 'error' : ''}`}>
                    {msg.role === 'user' ? msg.content : <Markdown text={msg.content} />}

                    {msg.role !== 'user' && msg.trace?.length > 0 && (
                      <div>
                        <button className="trace-toggle" onClick={() => toggleTrace(i)}>
                          <ChevronRight size={12} className={openTraces[i] ? 'open' : ''} aria-hidden="true" />
                          Show reasoning trace
                        </button>
                        {openTraces[i] && (
                          <div className="trace-body">
                            {msg.trace.map((t, ti) => (
                              <div key={ti}>
                                <span className="agent">{NODE_LABEL[t.node] || t.node}</span>
                                <span className="note"> — {t.detail}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {pending && (
              <div className={`approval ${pendingLeaving ? 'is-leaving' : ''}`}>
                <div className="approval-head">
                  <span className="pulse" />
                  <span className="label">Human approval required</span>
                </div>
                <div className="approval-body">
                  <p>{pending.message}</p>
                  <div className="approval-meta">
                    {pending.action && <code>{pending.action}</code>}
                    {pending.student_id && <code>{pending.student_id}</code>}
                  </div>
                  <div className="approval-actions">
                    <button className="btn primary" onClick={() => decide(true)}>Approve</button>
                    <button className="btn" onClick={() => decide(false)}>Decline</button>
                  </div>
                </div>
              </div>
            )}

            {busy && (
              <div className="thinking">
                <span className="spinner" />
                <span className="label">Orchestrating</span>
              </div>
            )}
          </div>

          <Composer ref={composerRef} onSend={send} disabled={busy || !!pending} />
        </div>
      </div>
    </section>
  )
}
