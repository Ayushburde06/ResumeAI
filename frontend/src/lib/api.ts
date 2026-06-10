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

function toText(value: unknown, fallback = ''): string {
  if (typeof value === 'string') return value
  if (value === null || value === undefined) return fallback
  return String(value)
}

function toStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => toText(item).trim())
    .filter(Boolean)
}

function normalizePersonalInfo(value: unknown): TailoredResume['personal_info'] {
  const info = typeof value === 'object' && value !== null ? value as Record<string, unknown> : {}
  return {
    name: toText(info.name),
    email: toText(info.email),
    phone: toText(info.phone),
    location: toText(info.location),
    linkedin: toText(info.linkedin),
    github: toText(info.github),
    website: toText(info.website),
  }
}

function normalizeTailoredResume(value: unknown): TailoredResume {
  const resume = typeof value === 'object' && value !== null ? value as Record<string, unknown> : {}
  const experience = Array.isArray(resume.experience)
    ? resume.experience.map((entry) => {
        const exp = typeof entry === 'object' && entry !== null ? entry as Record<string, unknown> : {}
        return {
          title: toText(exp.title),
          company: toText(exp.company),
          location: toText(exp.location),
          start_date: toText(exp.start_date),
          end_date: toText(exp.end_date),
          bullets: toStringArray(exp.bullets),
        }
      })
    : []

  const education = Array.isArray(resume.education)
    ? resume.education.map((entry) => {
        const edu = typeof entry === 'object' && entry !== null ? entry as Record<string, unknown> : {}
        return {
          degree: toText(edu.degree),
          institution: toText(edu.institution),
          location: toText(edu.location),
          graduation_year: toText(edu.graduation_year),
          gpa: toText(edu.gpa),
          honors: toText(edu.honors),
        }
      })
    : []

  const skillsValue = typeof resume.skills === 'object' && resume.skills !== null ? resume.skills as Record<string, unknown> : {}
  const projects = Array.isArray(resume.projects)
    ? resume.projects.map((entry) => {
        const project = typeof entry === 'object' && entry !== null ? entry as Record<string, unknown> : {}
        return {
          name: toText(project.name),
          description: toText(project.description),
          tech_stack: toStringArray(project.tech_stack),
          link: toText(project.link),
          live_link: toText(project.live_link),
        }
      })
    : []

  const certifications = Array.isArray(resume.certifications)
    ? resume.certifications.map((entry) => {
        const cert = typeof entry === 'object' && entry !== null ? entry as Record<string, unknown> : {}
        return {
          name: toText(cert.name),
          issuer: toText(cert.issuer),
          year: toText(cert.year),
        }
      })
    : []

  return {
    personal_info: normalizePersonalInfo(resume.personal_info),
    summary: toText(resume.summary),
    experience,
    education,
    skills: {
      languages: toStringArray(skillsValue.languages),
      frameworks: toStringArray(skillsValue.frameworks),
      databases: toStringArray(skillsValue.databases),
      tools: toStringArray(skillsValue.tools),
      concepts: toStringArray(skillsValue.concepts),
    },
    certifications,
    projects,
  }
}

function normalizeJobAnalysis(value: unknown): JobAnalysis {
  const analysis = typeof value === 'object' && value !== null ? value as Record<string, unknown> : {}
  return {
    job_title: toText(analysis.job_title),
    company_type: toText(analysis.company_type),
    seniority: toText(analysis.seniority),
    required_skills: toStringArray(analysis.required_skills),
    preferred_skills: toStringArray(analysis.preferred_skills),
    key_responsibilities: toStringArray(analysis.key_responsibilities),
    industry_keywords: toStringArray(analysis.industry_keywords),
    tone: toText(analysis.tone),
    must_have: toStringArray(analysis.must_have),
  }
}

function normalizeAnalyzeResponse(value: unknown): AnalyzeResponse {
  const response = typeof value === 'object' && value !== null ? value as Record<string, unknown> : {}
  return {
    tailored_resume: normalizeTailoredResume(response.tailored_resume),
    ats_score: typeof response.ats_score === 'number' ? response.ats_score : Number(response.ats_score ?? 0) || 0,
    matched_keywords: toStringArray(response.matched_keywords),
    missing_keywords: toStringArray(response.missing_keywords),
    total_keywords: typeof response.total_keywords === 'number' ? response.total_keywords : Number(response.total_keywords ?? 0) || 0,
    cover_letter: {
      subject_line: toText((response.cover_letter as { subject_line?: unknown } | undefined)?.subject_line),
      body: toText((response.cover_letter as { body?: unknown } | undefined)?.body),
    },
    application_email: {
      subject_line: toText((response.application_email as { subject_line?: unknown } | undefined)?.subject_line),
      body: toText((response.application_email as { body?: unknown } | undefined)?.body),
    },
    job_analysis: normalizeJobAnalysis(response.job_analysis),
    auto_improved: Boolean(response.auto_improved),
    model_used: response.model_used === undefined ? undefined : toText(response.model_used),
    analyses_used: typeof response.analyses_used === 'number' ? response.analyses_used : undefined,
    analyses_limit: typeof response.analyses_limit === 'number' ? response.analyses_limit : undefined,
    is_premium: typeof response.is_premium === 'boolean' ? response.is_premium : undefined,
  }
}

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
  return normalizeAnalyzeResponse(data)
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
  return {
    ...data,
    tailored_resume: normalizeTailoredResume(data.tailored_resume),
    matched_keywords: toStringArray(data.matched_keywords),
    missing_keywords: toStringArray(data.missing_keywords),
    ats_score: typeof data.ats_score === 'number' ? data.ats_score : Number(data.ats_score ?? 0) || 0,
    total_keywords: typeof data.total_keywords === 'number' ? data.total_keywords : Number(data.total_keywords ?? 0) || 0,
  }
}

export async function rescoreAts(
  tailoredResume: TailoredResume,
  jobDescription: string
): Promise<RescoreATSResponse> {
  const { data } = await axios.post<RescoreATSResponse>(`${BASE}/rescore-ats`, {
    tailored_resume: tailoredResume,
    job_description: jobDescription,
  })
  return {
    ...data,
    matched_keywords: toStringArray(data.matched_keywords),
    missing_keywords: toStringArray(data.missing_keywords),
    ats_score: typeof data.ats_score === 'number' ? data.ats_score : Number(data.ats_score ?? 0) || 0,
    total_keywords: typeof data.total_keywords === 'number' ? data.total_keywords : Number(data.total_keywords ?? 0) || 0,
  }
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
  return Array.isArray(data) ? data : []
}

export async function getHistoryEntry(id: number): Promise<HistoryEntry> {
  const { data } = await axios.get<HistoryEntry>(`${BASE}/history/${id}`)
  return {
    ...data,
    tailored_resume: normalizeTailoredResume(data.tailored_resume),
    cover_letter: data.cover_letter
      ? {
          subject_line: toText(data.cover_letter.subject_line),
          body: toText(data.cover_letter.body),
        }
      : null,
    application_email: data.application_email
      ? {
          subject_line: toText(data.application_email.subject_line),
          body: toText(data.application_email.body),
        }
      : null,
    job_analysis: data.job_analysis ? normalizeJobAnalysis(data.job_analysis) : null,
    job_description: data.job_description ?? null,
  }
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
