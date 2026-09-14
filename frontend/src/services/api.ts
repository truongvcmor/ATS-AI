import type { ApiErrorBody } from '../types'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api'
const TOKEN_KEY = 'ats_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function extractDetail(body: ApiErrorBody, fallback: string): string {
  if (!body) return fallback
  const detail = body.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === 'object' && d && 'msg' in d ? (d as { msg: string }).msg : String(d)))
      .join('; ')
  }
  return fallback
}

function redirectToLogin() {
  clearToken()
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  isForm?: boolean
  signal?: AbortSignal
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, isForm = false, signal } = options
  const token = getToken()

  const headers: Record<string, string> = {}
  if (!isForm && body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  let payload: BodyInit | undefined
  if (isForm) {
    payload = body as BodyInit
  } else if (body !== undefined) {
    payload = JSON.stringify(body)
  }

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: payload,
    signal,
  })

  if (res.status === 401) {
    redirectToLogin()
    throw new ApiError('Session expired. Please log in again.', 401)
  }

  if (res.status === 204) {
    return undefined as T
  }

  const contentType = res.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')

  if (!res.ok) {
    let message = `Request failed with status ${res.status}`
    if (isJson) {
      try {
        const errBody = (await res.json()) as ApiErrorBody
        message = extractDetail(errBody, message)
      } catch {
        // ignore parse error
      }
    }
    throw new ApiError(message, res.status)
  }

  if (isJson) {
    return (await res.json()) as T
  }
  return undefined as T
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { method: 'GET', signal }),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  postForm: <T>(path: string, form: FormData) => request<T>(path, { method: 'POST', body: form, isForm: true }),
}

export async function loginRequest(username: string, password: string) {
  const form = new URLSearchParams()
  form.set('username', username)
  form.set('password', password)

  const res = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form.toString(),
  })

  if (!res.ok) {
    let message = 'Login failed'
    try {
      const errBody = (await res.json()) as ApiErrorBody
      message = extractDetail(errBody, message)
    } catch {
      // ignore
    }
    throw new ApiError(message, res.status)
  }

  return res.json()
}

/** Downloads a file that requires auth headers (can't just use an <a href>). */
export async function downloadFile(path: string, fileName: string): Promise<void> {
  const token = getToken()
  const res = await fetch(`${API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) {
    throw new ApiError('Failed to download file', res.status)
  }
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export function buildQuery(params: Record<string, string | number | boolean | string[] | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) {
      for (const v of value) search.append(key, v)
    } else {
      search.append(key, String(value))
    }
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export { API_URL }
