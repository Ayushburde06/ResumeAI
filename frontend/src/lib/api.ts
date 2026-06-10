import axios, { isAxiosError } from 'axios'
import type {
  AnalyzeResponse,
  AuthResponse,
  HistoryEntry,
  HistoryListItem,
  ImproveATSResponse,
  JobAnalysis,
  JobSearchRequest,
  JobSearchResponse,
  JobListing,
  ModelInfo,
  RescoreATSResponse,
  TailoredResume,
} from '../types'

const BASE = '/api'

// Attach stored token on every request automatically
const stored = localStorage.getItem('auth_token')
if (stored) {
  axios.defaults.headers.common['Authorization'] = `Bearer ${stored}`
}

// Intercept responses to catch HTML pages (e.g. from Vercel proxy fallback)
axios.interceptors.response.use((response) => {
  if (typeof response.data === 'string' && response.data.trim().startsWith('<!DOCTYPE html>')) {
    throw new Error('API Error: Received an HTML page instead of JSON. The backend proxy might be failing or the backend is unreachable.');
  }
  return response;
});

async function parseApiError(err: unknown): Promise<string> {
  if (isAxiosError(err) && err.response?.data) {
    const data = err.response.data
    if (data instanceof Blob) {
      try {
        const text = await data.text()
        const json = JSON.parse(text) as { detail?: string }
        if (json.detail) return json.detail
      } catch {
        /* use default */
      }
    } else if (typeof data === 'object' && data !== null && 'detail' in data) {
      return String((data as { detail: unknown }).detail)
    }
  }
  return 'Something went wrong. Please try again.'
}

export async function fetchModels(): Promise<ModelInfo[]> {
  const { data } = await axios.get<ModelInfo[]>(`${BASE}/models`)
  return data
}

export async function analyzeResume(
  resumeFile: File,
  jobDescription: string,
  modelId?: string,
  onUploadProgress?: (pct: number) => void
): Promise<AnalyzeResponse> {
  const form = new FormData()
  form.append('resume_file', resumeFile)
  form.append('job_description', jobDescription)
  if (modelId) {
    form.append('model', modelId)
  }

  const { data } = await axios.post<AnalyzeResponse>(`${BASE}/analyze`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onUploadProgress) {
        onUploadProgress(Math.round((e.loaded / e.total) * 100))
      }
    },
  })
  return data
}

export async function suggestJobSearch(
  resumeFile: File,
  modelId?: string
): Promise<{ search_term: string; location: string }> {
  const form = new FormData()
  form.append('resume_file', resumeFile)
  if (modelId) {
    form.append('model', modelId)
  }

  const { data } = await axios.post<{ search_term: string; location: string }>(
    `${BASE}/suggest-job-search`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
  return data
}

export async function exportPdf(
  resume: TailoredResume,
  template: 'modern' | 'classic' | 'minimal' = 'modern'
): Promise<void> {
  let response
  try {
    response = await axios.post(
      `${BASE}/export-pdf`,
      { resume, template },
      { responseType: 'blob', validateStatus: (s) => s >= 200 && s < 300 }
    )
  } catch (err) {
    throw new Error(await parseApiError(err))
  }

  const blob = response.data as Blob
  if (!blob.type.includes('pdf') && blob.size < 5000) {
    const text = await blob.text()
    try {
      const json = JSON.parse(text) as { detail?: string }
      if (json.detail) throw new Error(json.detail)
    } catch (e) {
      if (e instanceof Error && e.message !== text) throw e
    }
  }

  const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }))
  const link = document.createElement('a')
  link.href = url
  const name = resume.personal_info?.name?.replace(/\s+/g, '_') ?? 'resume'
  link.download = `${name}_${template}.pdf`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export async function improveAtsScore(params: {
  tailoredResume: TailoredResume
  jobDescription: string
  jobAnalysis: JobAnalysis
  missingKeywords: string[]
  modelId?: string
}): Promise<ImproveATSResponse> {
  const { data } = await axios.post<ImproveATSResponse>(`${BASE}/improve-ats`, {
    tailored_resume: params.tailoredResume,
    job_description: params.jobDescription,
    job_analysis: params.jobAnalysis,
    missing_keywords: params.missingKeywords,
    model: params.modelId || '',
  })
  return data
}

export async function rescoreAts(
  tailoredResume: TailoredResume,
  jobDescription: string
): Promise<RescoreATSResponse> {
  const { data } = await axios.post<RescoreATSResponse>(`${BASE}/rescore-ats`, {
    tailored_resume: tailoredResume,
    job_description: jobDescription,
  })
  return data
}

export async function searchJobs(filters: JobSearchRequest): Promise<JobSearchResponse> {
  try {
    const { data } = await axios.post<JobSearchResponse>(`${BASE}/jobs/search`, filters, {
      timeout: 120000,
    })
    return data
  } catch (err) {
    throw new Error(await parseApiError(err))
  }
}

export async function formatJobDescription(job: JobListing): Promise<string> {
  try {
    const { data } = await axios.post<{ job_description: string }>(
      `${BASE}/jobs/format-description`,
      job
    )
    return data.job_description
  } catch (err) {
    throw new Error(await parseApiError(err))
  }
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export async function registerUser(
  name: string,
  email: string,
  password: string
): Promise<AuthResponse> {
  try {
    const { data } = await axios.post<AuthResponse>(`${BASE}/auth/register`, {
      name,
      email,
      password,
    })
    return data
  } catch (err) {
    throw new Error(await parseApiError(err))
  }
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  try {
    const { data } = await axios.post<AuthResponse>(`${BASE}/auth/login`, { email, password })
    return data
  } catch (err) {
    throw new Error(await parseApiError(err))
  }
}

// ── History ──────────────────────────────────────────────────────────────────

export async function saveHistory(payload: {
  tailored_resume: TailoredResume
  cover_letter?: object | null
  job_analysis?: object | null
  job_description?: string
  ats_score?: number
}): Promise<{ id: number }> {
  const { data } = await axios.post<{ id: number }>(`${BASE}/history/save`, payload)
  return data
}

export async function listHistory(): Promise<HistoryListItem[]> {
  const { data } = await axios.get<HistoryListItem[]>(`${BASE}/history`)
  return data
}

export async function getHistoryEntry(id: number): Promise<HistoryEntry> {
  const { data } = await axios.get<HistoryEntry>(`${BASE}/history/${id}`)
  return data
}

export async function deleteHistory(id: number): Promise<void> {
  await axios.delete(`${BASE}/history/${id}`)
}

export async function exportLatex(resume: TailoredResume): Promise<void> {
  let response
  try {
    response = await axios.post(
      `${BASE}/export-latex`,
      { resume, template: 'modern' },
      { responseType: 'blob', validateStatus: (s) => s >= 200 && s < 300 }
    )
  } catch (err) {
    throw new Error(await parseApiError(err))
  }

  const blob = response.data as Blob
  const url = URL.createObjectURL(new Blob([blob], { type: 'text/plain' }))
  const link = document.createElement('a')
  link.href = url
  const name = resume.personal_info?.name?.replace(/\s+/g, '_') ?? 'resume'
  link.download = `${name}_resume.tex`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

// ── Agentic AI + RAG ──────────────────────────────────────────────────────────

import type { AgentStep, AgentAnalyzeResult } from '../types'

export function agentAnalyze(
  resumeFile: File,
  jobDescription: string,
  modelId: string | undefined,
  onStep: (step: AgentStep) => void,
  onComplete: (result: AgentAnalyzeResult) => void,
  onError: (message: string) => void,
): () => void {
  /**
   * Opens a streaming POST request (XHR with streaming) to /api/agent-analyze.
   * Parses SSE `data:` lines in real-time and calls the appropriate callbacks.
   * Returns a cleanup function that aborts the request.
   *
   * We use XHR instead of EventSource because EventSource doesn't support
   * POST requests or custom headers (needed for Bearer token auth).
   */
  const token = localStorage.getItem('auth_token') ?? ''
  const form = new FormData()
  form.append('resume_file', resumeFile)
  form.append('job_description', jobDescription)
  if (modelId) form.append('model', modelId)

  const xhr = new XMLHttpRequest()
  xhr.open('POST', `${BASE}/agent-analyze`, true)
  xhr.setRequestHeader('Authorization', `Bearer ${token}`)
  xhr.setRequestHeader('Accept', 'text/event-stream')

  let buffer = ''

  xhr.onprogress = () => {
    // Append new chunk to buffer
    const newChunk = xhr.responseText.slice(buffer.length)
    buffer = xhr.responseText

    // Split on SSE line separator and process each line
    const lines = newChunk.split('\n')
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue
      const jsonStr = trimmed.slice(5).trim()
      if (!jsonStr) continue

      let parsed: AgentStep & { result?: AgentAnalyzeResult }
      try {
        parsed = JSON.parse(jsonStr)
      } catch {
        continue
      }

      if (parsed.step === 'complete' && parsed.result) {
        onComplete(parsed.result)
      } else if (parsed.step === 'error') {
        onError(parsed.message ?? 'Agent encountered an error.')
      } else {
        onStep(parsed as AgentStep)
      }
    }
  }

  xhr.onerror = () => onError('Network error. Please check your connection and try again.')
  xhr.ontimeout = () => onError('Request timed out. The agent took too long.')
  xhr.timeout = 300_000 // 5 minutes max

  xhr.send(form)

  // Return cleanup function
  return () => xhr.abort()
}

