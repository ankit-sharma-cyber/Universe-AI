import { useEffect, useState } from 'react'
import { Calendar, CheckCircle2, GraduationCap, LoaderCircle, Search, Users } from 'lucide-react'
import * as api from '../api.js'

const CONFIG = {
  academics: { title: 'Academics', subtitle: 'Your timetable, attendance, courses, and assignments.', icon: GraduationCap, endpoints: [['Attendance', api.fetchAttendance], ['Timetable', api.fetchTimetable], ['Courses', api.fetchCourses], ['Assignments', api.fetchAssignments]] },
  events: { title: 'Events', subtitle: 'Discover and register for eligible campus events.', icon: Calendar, endpoints: [['Upcoming events', () => api.fetchEvents('upcoming')]] },
  placements: { title: 'Placements', subtitle: 'Review drives and your eligibility in one place.', icon: Users, endpoints: [['Placement drives', api.fetchPlacements]] },
  services: { title: 'Student Services', subtitle: 'Find verified campus support, FAQs, policies, and facilities.', icon: Search, endpoints: [['FAQs', api.fetchFaqs], ['Policies', api.fetchPolicies], ['Hostels', api.fetchHostels], ['Lost and found', api.fetchLostFound]] },
}

function summarize(value) {
  if (Array.isArray(value)) return `${value.length} records available`
  if (!value || typeof value !== 'object') return String(value ?? 'No data')
  if ('pct' in value) return `${value.pct}% attendance · ${value.status.replace('_', ' ')}`
  if ('days' in value) return `${value.days.reduce((total, day) => total + day.classes.length, 0)} classes across the week`
  return Object.entries(value).slice(0, 3).map(([key, item]) => `${key}: ${typeof item === 'object' ? 'available' : item}`).join(' · ')
}

export default function PortalView({ section }) {
  const config = CONFIG[section] || CONFIG.academics
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const Icon = config.icon

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.all(config.endpoints.map(async ([label, loader]) => [label, await loader()]))
      .then((items) => active && setResults(items))
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false))
    return () => { active = false }
  }, [section])

  return (
    <section className="portal-view">
      <header className="portal-head">
        <div className="portal-title"><span className="portal-icon"><Icon size={20} /></span><div><h1>{config.title}</h1><p>{config.subtitle}</p></div></div>
        <span className="data-badge">LIVE LOCAL DATA</span>
      </header>
      {loading && <div className="portal-state"><LoaderCircle className="spin" size={18} /> Loading verified student data…</div>}
      {error && <div className="banner">{error}</div>}
      {!loading && !error && <div className="portal-grid">
        {results.map(([label, data]) => (
          <article className="portal-card" key={label}>
            <div className="portal-card-head"><h2>{label}</h2><CheckCircle2 size={16} /></div>
            <strong>{summarize(data)}</strong>
            {Array.isArray(data) && data.slice(0, 4).map((item, index) => (
              <div className="data-row" key={item.id || item.code || index}>
                <span>{item.title || item.name || item.company || item.code || item.question || `Record ${index + 1}`}</span>
                <small>{item.date || item.application_deadline || item.state || item.status || ''}</small>
              </div>
            ))}
          </article>
        ))}
      </div>}
    </section>
  )
}
