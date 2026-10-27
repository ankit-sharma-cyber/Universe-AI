const TOKEN_KEY = 'campus_token'

export class AuthError extends Error {
  constructor(message) {
    super(message)
    this.name = 'AuthError'
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`/api${path}`, { ...options, headers })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401) throw new AuthError(body.detail || 'Session expired — please sign in again.')
    throw new Error(body.detail || `Request failed (${response.status})`)
  }
  return body
}

export const login = (studentId, email) =>
  request('/auth/login', { method: 'POST', body: JSON.stringify({ student_id: studentId, email }) })

export const logout = () => request('/auth/logout', { method: 'POST' })

export const fetchMe = () => request('/auth/me')

export const sendChat = (payload) => request('/chat', { method: 'POST', body: JSON.stringify(payload) })

export const sendApproval = (conversationId, approved) =>
  request('/approve', { method: 'POST', body: JSON.stringify({ conversation_id: conversationId, approved }) })

export const fetchDashboard = () => request('/me/dashboard')
export const fetchTimetable = () => request('/timetable')
export const fetchCourses = () => request('/courses')
export const fetchAttendance = () => request('/me/attendance')
export const fetchAssignments = () => request('/me/assignments')
export const fetchEvents = (scope = 'upcoming') => request(`/events?scope=${scope}`)
export const fetchPlacements = () => request('/placements')
export const fetchFaqs = () => request('/faqs')
export const fetchPolicies = () => request('/policies')
export const fetchHostels = () => request('/hostels')
export const fetchLostFound = () => request('/lostfound')
export const fetchConversations = () => request('/conversations')
export const fetchConversation = (conversationId) => request(`/conversations/${conversationId}`)
