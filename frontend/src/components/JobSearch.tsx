import { useState } from 'react'
import {
  Briefcase,
  Building2,
  Calendar,
  ExternalLink,
  Loader2,
  MapPin,
  Search,
  Wifi,
} from 'lucide-react'
import { formatJobDescription, searchJobs } from '../lib/api'
import type { JobListing, JobSearchRequest } from '../types'

interface Props {
  onSelect: (jobDescription: string, job: JobListing) => void
  selectedJobId?: string | null
  resumeFile?: File | null
  modelId?: string
}

const JOB_SITES = [
  { id: 'indeed', label: 'Indeed' },
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'zip_recruiter', label: 'ZipRecruiter' },
  { id: 'google', label: 'Google Jobs' },
  { id: 'glassdoor', label: 'Glassdoor' },
] as const

const POSTED_WITHIN = [
  { label: 'Any time', value: null },
  { label: 'Last 24 hours', value: 24 },
  { label: 'Last 3 days', value: 72 },
  { label: 'Last 7 days', value: 168 },
  { label: 'Last 14 days', value: 336 },
  { label: 'Last 30 days', value: 720 },
] as const

const JOB_TYPES = [
  { label: 'Any type', value: '' },
  { label: 'Full-time', value: 'fulltime' },
  { label: 'Part-time', value: 'parttime' },
  { label: 'Internship', value: 'internship' },
  { label: 'Contract', value: 'contract' },
] as const

const COUNTRIES = ['USA', 'UK', 'Canada', 'Australia', 'India', 'Germany', 'France']

function formatPostedDate(value?: string | null) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function JobSearch({ onSelect, selectedJobId, resumeFile, modelId }: Props) {
  const [searchTerm, setSearchTerm] = useState('')
  const [location, setLocation] = useState('')
  const [sites, setSites] = useState<string[]>(['indeed', 'linkedin'])
  const [hoursOld, setHoursOld] = useState<number | null>(72)
  const [jobType, setJobType] = useState('')
  const [isRemote, setIsRemote] = useState(false)
  const [country, setCountry] = useState('USA')
  const [resultsWanted, setResultsWanted] = useState(15)
  const [jobs, setJobs] = useState<JobListing[]>([])
  const [loading, setLoading] = useState(false)
  const [selectingId, setSelectingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [hasSearched, setHasSearched] = useState(false)
  const [autoFilling, setAutoFilling] = useState(false)

  function toggleSite(siteId: string) {
    setSites((prev) =>
      prev.includes(siteId) ? prev.filter((s) => s !== siteId) : [...prev, siteId]
    )
  }

  async function handleSearch() {
    if (searchTerm.trim().length < 2) {
      setError('Enter a job title or keywords to search.')
      return
    }
    if (sites.length === 0) {
      setError('Select at least one job board.')
      return
    }

    setLoading(true)
    setError(null)
    setHasSearched(true)

    const filters: JobSearchRequest = {
      search_term: searchTerm.trim(),
      location: location.trim() || null,
      site_name: sites,
      results_wanted: resultsWanted,
      hours_old: hoursOld,
      job_type: jobType || null,
      is_remote: isRemote || null,
      country_indeed: country,
      linkedin_fetch_description: true,
    }

    try {
      const result = await searchJobs(filters)
      setJobs(result.jobs)
      if (result.jobs.length === 0) {
        setError('No jobs found. Try broader keywords, another location, or a longer time window.')
      }
    } catch (err) {
      setJobs([])
      setError(err instanceof Error ? err.message : 'Job search failed.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSelect(job: JobListing) {
    setSelectingId(job.id)
    setError(null)
    try {
      const description = await formatJobDescription(job)
      onSelect(description, job)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not use this job listing.')
    } finally {
      setSelectingId(null)
    }
  }

  async function handleAutoFill() {
    if (!resumeFile) return
    setAutoFilling(true)
    setError(null)
    try {
      // @ts-ignore
      const { suggestJobSearch } = await import('../lib/api')
      const result = await suggestJobSearch(resumeFile, modelId)
      if (result.search_term) setSearchTerm(result.search_term)
      if (result.location) setLocation(result.location)
      
      // Auto trigger search if we got a term
      if (result.search_term) {
        // We can't directly call handleSearch here because state updates are async,
        // but we can pass the values directly to a local version of handleSearch
        setLoading(true)
        setHasSearched(true)
        
        const filters: JobSearchRequest = {
          search_term: result.search_term,
          location: result.location || null,
          site_name: sites,
          results_wanted: resultsWanted,
          hours_old: hoursOld,
          job_type: jobType || null,
          is_remote: isRemote || null,
          country_indeed: country,
          linkedin_fetch_description: true,
        }
        
        try {
          // @ts-ignore
          const { searchJobs: doSearch } = await import('../lib/api')
          const searchResult = await doSearch(filters)
          setJobs(searchResult.jobs)
          if (searchResult.jobs.length === 0) {
            setError('No jobs found using the suggested keywords. Try adjusting them.')
          }
        } catch (err) {
          setJobs([])
          setError(err instanceof Error ? err.message : 'Job search failed.')
        } finally {
          setLoading(false)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not analyze resume for job search.')
    } finally {
      setAutoFilling(false)
    }
  }

  return (
    <div className="space-y-4">
      {resumeFile && (
        <button
          type="button"
          onClick={handleAutoFill}
          disabled={autoFilling || loading}
          className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-xl border border-brand-200 bg-brand-50 text-sm font-medium text-brand-700 hover:bg-brand-100 transition-colors"
        >
          {autoFilling ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <span className="text-lg leading-none">✨</span>
          )}
          {autoFilling ? 'Analyzing resume...' : 'Auto-fill from Resume'}
        </button>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1.5 sm:col-span-2">
          <span className="text-xs font-medium text-gray-600">Keywords</span>
          <input
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="e.g. software engineer, data analyst"
            className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
          />
        </label>

        <label className="space-y-1.5">
          <span className="text-xs font-medium text-gray-600">Location</span>
          <input
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="City, state or remote area"
            className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400"
          />
        </label>

        <label className="space-y-1.5">
          <span className="text-xs font-medium text-gray-600">Posted within</span>
          <select
            value={hoursOld ?? ''}
            onChange={(e) => setHoursOld(e.target.value ? Number(e.target.value) : null)}
            className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-400"
          >
            {POSTED_WITHIN.map((option) => (
              <option key={option.label} value={option.value ?? ''}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1.5">
          <span className="text-xs font-medium text-gray-600">Job type</span>
          <select
            value={jobType}
            onChange={(e) => setJobType(e.target.value)}
            className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-400"
          >
            {JOB_TYPES.map((option) => (
              <option key={option.label} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1.5">
          <span className="text-xs font-medium text-gray-600">Country (Indeed / Glassdoor)</span>
          <select
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-400"
          >
            {COUNTRIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1.5">
          <span className="text-xs font-medium text-gray-600">Results per site</span>
          <select
            value={resultsWanted}
            onChange={(e) => setResultsWanted(Number(e.target.value))}
            className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-brand-400"
          >
            {[10, 15, 20, 30, 50].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="space-y-2">
        <span className="text-xs font-medium text-gray-600">Job boards</span>
        <div className="flex flex-wrap gap-2">
          {JOB_SITES.map((site) => {
            const active = sites.includes(site.id)
            return (
              <button
                key={site.id}
                type="button"
                onClick={() => toggleSite(site.id)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                  active
                    ? 'bg-brand-50 border-brand-200 text-brand-700'
                    : 'bg-white border-gray-200 text-gray-500 hover:border-gray-300'
                }`}
              >
                {site.label}
              </button>
            )
          })}
        </div>
      </div>

      <label className="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
        <input
          type="checkbox"
          checked={isRemote}
          onChange={(e) => setIsRemote(e.target.checked)}
          className="rounded border-gray-300 text-brand-600 focus:ring-brand-400"
        />
        Remote only
      </label>

      <button
        type="button"
        onClick={handleSearch}
        disabled={loading}
        className="btn-secondary w-full justify-center"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Searching job boards...
          </>
        ) : (
          <>
            <Search className="w-4 h-4" />
            Search jobs
          </>
        )}
      </button>

      {error && (
        <div className="p-3 rounded-xl bg-amber-50 border border-amber-100 text-sm text-amber-800">
          {error}
        </div>
      )}

      {jobs.length > 0 && (
        <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
          <p className="text-xs font-medium text-gray-500">
            {jobs.length} result{jobs.length === 1 ? '' : 's'} — select one to tailor your resume
          </p>
          {jobs.map((job) => {
            const selected = selectedJobId === job.id
            const posted = formatPostedDate(job.date_posted)
            return (
              <button
                key={job.id}
                type="button"
                onClick={() => handleSelect(job)}
                disabled={selectingId === job.id}
                className={`w-full text-left p-4 rounded-xl border transition-all ${
                  selected
                    ? 'border-brand-400 bg-brand-50 shadow-sm'
                    : 'border-gray-200 bg-white hover:border-brand-200 hover:bg-brand-50/40'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 space-y-1">
                    <div className="font-semibold text-sm text-gray-900 truncate">
                      {job.title || 'Untitled role'}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500">
                      {job.company && (
                        <span className="inline-flex items-center gap-1">
                          <Building2 className="w-3.5 h-3.5" />
                          {job.company}
                        </span>
                      )}
                      {job.location && (
                        <span className="inline-flex items-center gap-1">
                          <MapPin className="w-3.5 h-3.5" />
                          {job.location}
                        </span>
                      )}
                      {job.is_remote && (
                        <span className="inline-flex items-center gap-1 text-emerald-600">
                          <Wifi className="w-3.5 h-3.5" />
                          Remote
                        </span>
                      )}
                      {posted && (
                        <span className="inline-flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          {posted}
                        </span>
                      )}
                    </div>
                    {job.salary && (
                      <div className="text-xs text-gray-600">{job.salary}</div>
                    )}
                    {job.site && (
                      <span className="inline-block text-[10px] uppercase tracking-wide font-semibold text-brand-600 bg-brand-50 px-2 py-0.5 rounded-full">
                        {job.site}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    {job.job_url && (
                      <a
                        href={job.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-gray-400 hover:text-brand-600"
                        aria-label="Open job posting"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                    {selectingId === job.id ? (
                      <Loader2 className="w-4 h-4 animate-spin text-brand-600" />
                    ) : selected ? (
                      <span className="text-xs font-semibold text-brand-700">Selected</span>
                    ) : (
                      <span className="text-xs text-gray-400">Use this job</span>
                    )}
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      )}

      {hasSearched && !loading && jobs.length === 0 && !error && (
        <div className="text-center py-8 text-sm text-gray-400">
          <Briefcase className="w-8 h-8 mx-auto mb-2 opacity-40" />
          No listings to show yet.
        </div>
      )}
    </div>
  )
}
