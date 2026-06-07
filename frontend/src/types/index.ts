export interface JobListing {
  id: string
  site?: string | null
  title?: string | null
  company?: string | null
  location?: string | null
  is_remote?: boolean | null
  job_type?: string | null
  date_posted?: string | null
  salary?: string | null
  job_url?: string | null
  description: string
}

export interface JobSearchRequest {
  search_term: string
  location?: string | null
  site_name?: string[] | null
  results_wanted?: number
  hours_old?: number | null
  job_type?: string | null
  is_remote?: boolean | null
  country_indeed?: string
  distance?: number
  linkedin_fetch_description?: boolean
  google_search_term?: string | null
}

export interface JobSearchResponse {
  jobs: JobListing[]
  total: number
}

export interface PersonalInfo {
  name: string
  email: string
  phone: string
  location: string
  linkedin: string
  github: string
  website: string
}

export interface ExperienceItem {
  title: string
  company: string
  location: string
  start_date: string
  end_date: string
  bullets: string[]
}

export interface EducationItem {
  degree: string
  institution: string
  location: string
  graduation_year: string
  gpa: string
  honors: string
}

export interface Skills {
  languages: string[]
  frameworks: string[]
  databases: string[]
  tools: string[]
  concepts: string[]
}

export interface Certification {
  name: string
  issuer: string
  year: string
}

export interface Project {
  name: string
  description: string
  tech_stack: string[]
  link: string
  live_link?: string
}

export interface TailoredResume {
  personal_info: PersonalInfo
  summary: string
  experience: ExperienceItem[]
  education: EducationItem[]
  skills: Skills
  certifications: Certification[]
  projects: Project[]
}

export interface CoverLetter {
  subject_line: string
  body: string
}

export interface ApplicationEmail {
  subject_line: string
  body: string
}

export interface JobAnalysis {
  job_title: string
  company_type: string
  seniority: string
  required_skills: string[]
  preferred_skills: string[]
  key_responsibilities: string[]
  industry_keywords: string[]
  tone: string
  must_have: string[]
}

export interface ModelInfo {
  id: string
  display_name: string
  is_default: boolean
}

export interface AnalyzeResponse {
  tailored_resume: TailoredResume
  ats_score: number
  matched_keywords: string[]
  missing_keywords: string[]
  total_keywords: number
  cover_letter: CoverLetter
  application_email: ApplicationEmail
  job_analysis: JobAnalysis
  auto_improved?: boolean
  model_used?: string
  analyses_used?: number
  analyses_limit?: number
  is_premium?: boolean
}

export interface ImproveATSResponse {
  tailored_resume: TailoredResume
  ats_score: number
  matched_keywords: string[]
  missing_keywords: string[]
  total_keywords: number
}

export interface RescoreATSResponse {
  ats_score: number
  matched_keywords: string[]
  missing_keywords: string[]
  total_keywords: number
}

export interface ResultsState {
  result: AnalyzeResponse
  job_description: string
  model_id?: string
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: number
  name: string
  email: string
  analyses_used?: number
  analyses_limit?: number
  is_premium?: boolean
}

export interface AuthResponse {
  token: string
  user: AuthUser
}

// ── History ──────────────────────────────────────────────────────────────────

export interface HistoryListItem {
  id: number
  job_title: string
  candidate_name: string
  ats_score: number | null
  created_at: string
}

export interface HistoryEntry {
  id: number
  job_title: string
  ats_score: number | null
  tailored_resume: TailoredResume
  cover_letter: CoverLetter | null
  application_email: ApplicationEmail | null
  job_analysis: JobAnalysis | null
  job_description: string | null
  created_at: string
}

// ── Agentic AI + RAG ──────────────────────────────────────────────────────────

export interface AgentTrace {
  iterations_run: number
  ats_progression: number[]
  best_ats_score: number
  rag_context_used: boolean
  total_time_ms: number
}

export interface TechnicalQuestion {
  question: string
  why_asked: string
  tip: string
}

export interface BehavioralQuestion {
  question: string
  star_prompt: string
}

export interface InterviewPrep {
  likely_technical_questions: TechnicalQuestion[]
  likely_behavioral_questions: BehavioralQuestion[]
  strengths_to_highlight: string[]
  gaps_to_prepare_for: string[]
  questions_to_ask_interviewer: string[]
}

export interface AgentStep {
  step: string
  status: 'running' | 'done' | 'error'
  iteration?: number
  max_iterations?: number
  ats_score?: number
  target_reached?: boolean
  matched_count?: number
  missing_count?: number
  diagnosis?: string
  priority_fixes?: string[]
  strategy?: string
  job_title?: string
  message?: string
  chunks_retrieved?: boolean
}

export interface AgentAnalyzeResult extends AnalyzeResponse {
  interview_prep?: InterviewPrep
  agent_trace?: AgentTrace
}

