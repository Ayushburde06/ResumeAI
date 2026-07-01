import { Link, useLocation } from 'react-router-dom'
import { motion, useReducedMotion, type HTMLMotionProps } from 'framer-motion'
import {
  ArrowRight,
  BadgeCheck,
  BookOpen,
  Brain,
  Check,
  ChevronRight,
  ClipboardCheck,
  FileText,
  GitBranch,
  Github,
  Linkedin,
  Mail,
  PenTool,
  ShieldCheck,
  Sparkles,
  Upload,
  Zap,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { analyzeResume } from '../lib/api'
import UnifiedWorkspace from '../components/UnifiedWorkspace'
import { Button } from '@/components/ui/button'

const navLinks = [
  { label: 'Features', href: '#features' },
  { label: 'How it Works', href: '#how-it-works' },
  { label: 'FAQ', href: '#faq' },
]

const howItWorks = [
  {
    icon: Upload,
    title: 'Upload Resume',
    text: 'Drop in a PDF or DOCX and let ResumeAI extract the content cleanly.',
  },
  {
    icon: ClipboardCheck,
    title: 'Paste Job Description',
    text: 'The app compares your resume against the role and highlights what matters most.',
  },
  {
    icon: Sparkles,
    title: 'Download Optimized Resume',
    text: 'Review the rewrite, keep what you want, and export the final PDF in seconds.',
  },
]

const features = [
  { icon: Brain, title: 'ATS Keyword Matching', text: 'Compare your resume to the job description and surface missing terms.' },
  { icon: PenTool, title: 'AI Resume Rewrite', text: 'Improve targeted sections without inventing experience or adding fluff.' },
  { icon: FileText, title: 'Resume Parsing', text: 'Extract and structure content cleanly from PDF and DOCX uploads.' },
  { icon: BookOpen, title: 'Job Description Analysis', text: 'Pull out required and preferred skills from any job posting.' },
  { icon: GitBranch, title: 'Gap Analysis', text: 'Understand missing skills before you apply, prioritized by importance.' },
  { icon: Zap, title: 'ATS Score', text: 'See your score before and after optimization in real time.' },
  { icon: BadgeCheck, title: 'PDF Export', text: 'Download a polished, recruiter-ready PDF with professional formatting.' },
  { icon: ShieldCheck, title: 'No Hallucinations', text: 'Only rewrites based on your existing experience. No invented claims.' },
]

const faqItems = [
  {
    q: 'Does ResumeAI invent experience?',
    a: 'No. It rewrites the resume using the evidence already present in your file and the job description.',
  },
  {
    q: 'How accurate is ATS optimization?',
    a: 'It is designed to improve keyword coverage and structure, but the final score depends on the role and the source resume.',
  },
  {
    q: 'Can I use it for multiple jobs?',
    a: 'Yes. Tailor one resume for each job description and keep the versions in your history.',
  },
  {
    q: 'Is my resume private?',
    a: 'The app processes your upload server-side and keeps the workflow focused on your saved account history.',
  },
]

const footerLinks = [
  { label: 'GitHub', href: 'https://github.com/Ayushburde06', icon: Github },
  { label: 'LinkedIn', href: 'https://www.linkedin.com/in/ayushkumar6', icon: Linkedin },
  { label: 'Mail', href: 'mailto:ayushburde156@gmail.com', icon: Mail },
]

function SectionHeading({
  kicker,
  title,
  text,
}: {
  kicker: string
  title: string
  text?: string
}) {
  return (
    <div className="max-w-2xl">
      <p className="section-title mb-2">{kicker}</p>
      <h2 className="text-2xl md:text-3xl font-semibold tracking-tight text-slate-ink">{title}</h2>
      {text && <p className="mt-3 text-sm md:text-[15px] leading-7 text-zinc-600">{text}</p>}
    </div>
  )
}

function GuestHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-zinc-200/70 bg-white/85 backdrop-blur-xl">
      <div className="page-shell h-16 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 shrink-0 rounded-2xl bg-brand flex items-center justify-center shadow-[0_12px_24px_rgba(26,31,46,0.16)]">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="text-slate-ink text-[15px] font-semibold tracking-tight">ResumeAI</span>
        </Link>

        <nav className="hidden lg:flex items-center gap-6">
          {navLinks.map((item) => (
            <a key={item.label} href={item.href} className="text-sm text-zinc-600 hover:text-zinc-950 transition-colors">
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <Link to="/login" className="hidden sm:block">
            <Button variant="ghost" className="rounded-2xl px-4 text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50">
              Sign In
            </Button>
          </Link>
          <Link to="/signup">
            <Button className="rounded-2xl bg-brand px-3 sm:px-4 text-white shadow-[0_14px_28px_rgba(26,31,46,0.14)] hover:bg-brand-hover text-sm">
              Get Started
              <ArrowRight className="ml-1.5 w-4 h-4" />
            </Button>
          </Link>
        </div>
      </div>
    </header>
  )
}

function HeroDashboard() {
  return (
    <div className="relative overflow-hidden rounded-[28px] border border-white/70 bg-white/90 shadow-[0_24px_70px_rgba(15,23,42,0.10)]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(59,130,246,0.12),transparent_28%),radial-gradient(circle_at_bottom_left,rgba(17,24,39,0.08),transparent_26%)]" />
      <div className="relative z-10 p-4 sm:p-5 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-zinc-500">Live resume analysis</p>
            <p className="text-sm font-semibold text-slate-ink mt-1">Recruiter-ready output</p>
          </div>
          <button className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-700 shadow-sm">
            <Sparkles className="h-3.5 w-3.5 text-brand" />
            Download PDF
          </button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">ATS Score</p>
            <div className="mt-3 flex items-end justify-between">
              <div>
                <p className="text-3xl font-semibold text-slate-ink">92%</p>
                <p className="text-xs text-emerald-700 mt-1">+18 from original resume</p>
              </div>
              <div className="h-12 w-12 rounded-full border-4 border-emerald-100 border-t-emerald-500" />
            </div>
          </div>
          <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">Resume Match</p>
            <div className="mt-3 flex items-end justify-between">
              <div>
                <p className="text-3xl font-semibold text-slate-ink">87%</p>
                <p className="text-xs text-zinc-500 mt-1">Role alignment</p>
              </div>
              <div className="space-y-1.5">
                <div className="h-2 w-14 rounded-full bg-zinc-100">
                  <div className="h-2 w-[87%] rounded-full bg-brand" />
                </div>
                <div className="h-2 w-14 rounded-full bg-zinc-100">
                  <div className="h-2 w-[72%] rounded-full bg-zinc-300" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">Missing Keywords</p>
              <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">4 left</span>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              {['PostgreSQL', 'REST API', 'JWT', 'Docker'].map((item) => (
                <span key={item} className="rounded-full border border-amber-100 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700">
                  {item}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">Suggested Improvements</p>
            <ul className="mt-3 space-y-2 text-sm text-zinc-700">
              <li className="flex gap-2"><ChevronRight className="mt-0.5 h-4 w-4 text-brand shrink-0" />Strengthen the internship bullet about backend APIs.</li>
              <li className="flex gap-2"><ChevronRight className="mt-0.5 h-4 w-4 text-brand shrink-0" />Move SQL terms into the skills section more clearly.</li>
              <li className="flex gap-2"><ChevronRight className="mt-0.5 h-4 w-4 text-brand shrink-0" />Trim repeated wording in the project descriptions.</li>
            </ul>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-[1.08fr_0.92fr]">
          <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">Resume Preview</p>
              <span className="text-[10px] font-semibold text-zinc-400">Recruiter scan</span>
            </div>
            <div className="mt-3 space-y-2">
              <div className="h-2.5 w-36 rounded-full bg-zinc-900" />
              <div className="h-2 w-full rounded-full bg-zinc-100" />
              <div className="h-2 w-11/12 rounded-full bg-zinc-100" />
              <div className="h-2 w-5/6 rounded-full bg-zinc-100" />
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2">
              {['Summary', 'Experience', 'Projects'].map((item) => (
                <div key={item} className="rounded-xl bg-zinc-50 px-2.5 py-2 text-[11px] font-semibold text-zinc-600 text-center">
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">Export</p>
            <button className="mt-3 w-full rounded-2xl bg-brand px-4 py-3 text-sm font-semibold text-white shadow-[0_14px_28px_rgba(26,31,46,0.16)]">
              Download PDF
            </button>
            <div className="mt-3 rounded-2xl border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
              Generate a polished, recruiter-ready PDF in one click.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function AppForm() {
  const location = useLocation()
  const state = location.state as { result?: any; job_description?: string } | null

  const handleAnalyze = async (file: File, jd: string, modelId?: string) => {
    return analyzeResume(file, jd, modelId)
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] overflow-hidden flex flex-col">
      <UnifiedWorkspace
        initialResult={state?.result}
        initialJd={state?.job_description ?? ''}
        initialInterviewPrep={state?.result?.interview_prep ?? null}
        onAnalyze={handleAnalyze}
      />
    </div>
  )
}

function GuestWorkspace() {
  const reduceMotion = useReducedMotion()

  const motionProps = (delay = 0): Partial<HTMLMotionProps<'div'>> => {
    if (reduceMotion) return {}
    return {
      initial: { opacity: 0, y: 16 },
      whileInView: { opacity: 1, y: 0 },
      viewport: { once: true, amount: 0.35 },
      transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1], delay },
    }
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-[linear-gradient(180deg,#fbfbfd_0%,#f6f7fb_50%,#ffffff_100%)] text-slate-ink">
      <GuestHeader />

      <main>
        {/* Hero */}
        <section className="page-shell py-10 md:py-16 lg:py-20">
          <div className="grid grid-cols-1 lg:grid-cols-[1.08fr_0.92fr] gap-8 lg:gap-10 items-center">
            <motion.div {...motionProps()} className="space-y-6">
              <div className="space-y-4">
                <h1 className="text-[32px] sm:text-4xl md:text-5xl lg:text-[58px] font-semibold tracking-tight leading-[1.05] text-slate-ink">
                  Optimize Your Resume for ATS & Recruiters
                </h1>
                <p className="max-w-xl text-base md:text-[17px] leading-7 md:leading-8 text-zinc-600">
                  Upload your resume and a job description. ResumeAI finds missing keywords, rewrites the necessary sections, and exports a recruiter-ready PDF — without inventing experience.
                </p>
              </div>

              <div className="flex flex-col sm:flex-row flex-wrap gap-3">
                <Link to="/signup" className="sm:inline-flex">
                  <Button className="w-full sm:w-auto rounded-2xl bg-brand px-6 py-3 text-white shadow-[0_18px_42px_rgba(26,31,46,0.16)] hover:bg-brand-hover">
                    Optimize My Resume
                    <ArrowRight className="ml-1.5 w-4 h-4" />
                  </Button>
                </Link>
                <a href="#product-preview" className="sm:inline-flex">
                  <Button variant="outline" className="w-full sm:w-auto rounded-2xl border-zinc-200 bg-white px-6 py-3 text-zinc-800 hover:bg-zinc-50">
                    See How It Works
                  </Button>
                </a>
              </div>

              <div className="flex flex-wrap gap-2 text-xs text-zinc-500">
                <span className="rounded-full border border-zinc-200 bg-white px-3 py-1.5">No fake experience</span>
                <span className="rounded-full border border-zinc-200 bg-white px-3 py-1.5">ATS-friendly output</span>
                <span className="rounded-full border border-zinc-200 bg-white px-3 py-1.5">PDF export ready</span>
              </div>
            </motion.div>

            {/* Dashboard widget — only visible from lg up to avoid overwhelming mobile */}
            <motion.div {...motionProps(0.08)} className="hidden lg:block lg:pl-4">
              <HeroDashboard />
            </motion.div>
          </div>
        </section>

        {/* How it Works */}
        <section id="how-it-works" className="page-shell pb-10 md:pb-14">
          <div className="panel p-6 md:p-7">
            <SectionHeading
              kicker="How it works"
              title="Three steps from upload to optimized resume."
            />

            <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-5">
              {howItWorks.map((item, index) => {
                const Icon = item.icon
                return (
                  <div key={item.title} className="relative rounded-2xl border border-zinc-200 bg-white p-5">
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                        <Icon className="h-5 w-5" />
                      </div>
                      <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-400">
                        0{index + 1}
                      </div>
                    </div>
                    <h3 className="mt-4 text-base font-semibold text-slate-ink">{item.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-zinc-600">{item.text}</p>
                    {index < howItWorks.length - 1 && (
                      <div className="hidden lg:block absolute -right-3 top-1/2 h-px w-6 bg-zinc-200" />
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        {/* Product Preview */}
        <section id="product-preview" className="page-shell pb-10 md:pb-14">
          <div className="panel p-6 md:p-7">
            <SectionHeading
              kicker="Product preview"
              title="Everything you see is real output from the tool."
              text="ATS score, keyword gaps, rewrite suggestions, and a recruiter-ready final resume — all generated from a single upload."
            />

            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {[
                {
                  title: 'Resume Analysis',
                  detail: 'Source resume parsed and structured',
                  accent: 'bg-slate-950',
                  render: () => (
                    <div className="mt-3 space-y-2">
                      <div className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50/60 border border-emerald-100/50 rounded-xl px-3 py-1.5">
                        <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                        <span className="font-medium">Resume parsed successfully (2 pages)</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50/60 border border-emerald-100/50 rounded-xl px-3 py-1.5">
                        <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                        <span className="font-medium">14 core skills detected & classified</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-emerald-700 bg-emerald-50/60 border border-emerald-100/50 rounded-xl px-3 py-1.5">
                        <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0" />
                        <span className="font-medium">3 professional experiences validated</span>
                      </div>
                    </div>
                  )
                },
                {
                  title: 'ATS Score',
                  detail: '92% match for the target role',
                  accent: 'bg-brand',
                  render: () => (
                    <div className="mt-3 flex items-center justify-between">
                      <div>
                        <span className="text-4xl font-bold tracking-tight text-slate-ink">92%</span>
                        <div className="mt-1.5">
                          <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 border border-emerald-100">
                            Excellent Match
                          </span>
                        </div>
                      </div>
                      <div className="relative h-14 w-14 flex items-center justify-center mr-2">
                        <svg className="absolute inset-0 w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                          <circle cx="18" cy="18" r="14" fill="none" stroke="#f4f4f5" strokeWidth="3" />
                          <circle
                            cx="18"
                            cy="18"
                            r="14"
                            fill="none"
                            stroke="#10b981"
                            strokeWidth="3"
                            strokeDasharray="88"
                            strokeDashoffset={88 - (88 * 92) / 100}
                            strokeLinecap="round"
                          />
                        </svg>
                        <span className="text-[10px] font-bold text-zinc-500 mt-0.5">+18%</span>
                      </div>
                    </div>
                  )
                },
                {
                  title: 'Keyword Match',
                  detail: 'Important terms highlighted for review',
                  accent: 'bg-emerald-600',
                  render: () => (
                    <div className="mt-3 space-y-2.5">
                      <div>
                        <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-400">Matched Keywords</p>
                        <div className="mt-1 flex flex-wrap gap-1.5">
                          {['React', 'TypeScript', 'Node.js', 'PostgreSQL'].map((kw) => (
                            <span key={kw} className="inline-flex items-center rounded-lg bg-emerald-50 border border-emerald-100 px-2 py-0.5 text-[10px] font-medium text-emerald-700">
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-400">Missing Keywords</p>
                        <div className="mt-1 flex flex-wrap gap-1.5">
                          {['AWS', 'Docker', 'CI/CD'].map((kw) => (
                            <span key={kw} className="inline-flex items-center rounded-lg bg-amber-50 border border-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  )
                },
                {
                  title: 'Skill Gap Analysis',
                  detail: 'Missing keywords grouped by priority',
                  accent: 'bg-amber-500',
                  render: () => (
                    <div className="mt-3 space-y-2">
                      <div className="flex items-start gap-2 text-xs">
                        <span className="mt-1.5 inline-flex h-1.5 w-1.5 shrink-0 rounded-full bg-red-500" />
                        <span className="text-zinc-600 leading-tight">
                          <span className="font-semibold text-slate-ink">High:</span> Add cloud infrastructure terms (AWS, Docker) to matches.
                        </span>
                      </div>
                      <div className="flex items-start gap-2 text-xs">
                        <span className="mt-1.5 inline-flex h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
                        <span className="text-zinc-600 leading-tight">
                          <span className="font-semibold text-slate-ink">Medium:</span> Quantify achievements under backend engineer roles.
                        </span>
                      </div>
                      <div className="flex items-start gap-2 text-xs">
                        <span className="mt-1.5 inline-flex h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                        <span className="text-zinc-600 leading-tight">
                          <span className="font-semibold text-slate-ink">Low:</span> Group tools into a distinct, clean skills section.
                        </span>
                      </div>
                    </div>
                  )
                },
                {
                  title: 'Resume Rewrite',
                  detail: 'Only the necessary sections improved',
                  accent: 'bg-indigo-600',
                  render: () => (
                    <div className="mt-3 space-y-2 text-[11px] leading-relaxed">
                      <div className="rounded-lg border border-red-100 bg-red-50/50 p-2">
                        <span className="font-bold text-red-700">Before:</span>
                        <p className="text-zinc-500 italic mt-0.5">"Responsible for coding and backend APIs."</p>
                      </div>
                      <div className="rounded-lg border border-emerald-100 bg-emerald-50/50 p-2">
                        <span className="font-bold text-emerald-700">After:</span>
                        <p className="text-slate-ink font-medium mt-0.5">
                          "Designed and built robust RESTful APIs in Node.js, improving load time by 24%."
                        </p>
                      </div>
                    </div>
                  )
                },
                {
                  title: 'Final Resume',
                  detail: 'Download-ready recruiter format',
                  accent: 'bg-zinc-900',
                  render: () => (
                    <div className="mt-3 rounded-lg border border-zinc-200 bg-zinc-50/50 p-2.5 shadow-inner">
                      <div className="flex items-center justify-between border-b border-zinc-200 pb-1.5 mb-1.5">
                        <div>
                          <p className="text-[10px] font-bold text-slate-ink">John Doe</p>
                          <p className="text-[8px] text-zinc-400">Software Engineer</p>
                        </div>
                        <span className="rounded bg-brand px-1.5 py-0.5 text-[8px] font-semibold text-white">
                          PDF
                        </span>
                      </div>
                      <div className="space-y-1">
                        <div>
                          <p className="text-[7px] font-bold uppercase tracking-wider text-brand">Experience</p>
                          <div className="h-1 w-full rounded bg-zinc-200 mt-0.5" />
                          <div className="h-1 w-5/6 rounded bg-zinc-200 mt-0.5" />
                        </div>
                        <div>
                          <p className="text-[7px] font-bold uppercase tracking-wider text-brand">Projects</p>
                          <div className="h-1 w-11/12 rounded bg-zinc-200 mt-0.5" />
                          <div className="h-1 w-4/5 rounded bg-zinc-200 mt-0.5" />
                        </div>
                      </div>
                    </div>
                  )
                },
              ].map((item) => (
                <div key={item.title} className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)] flex flex-col justify-between min-h-0 sm:min-h-[200px]">
                  <div>
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-slate-ink">{item.title}</p>
                      <div className={`h-2.5 w-2.5 rounded-full ${item.accent}`} />
                    </div>
                    {item.render()}
                  </div>
                  <p className="mt-4 text-xs leading-5 text-zinc-500">{item.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Features */}
        <section id="features" className="page-shell pb-10 md:pb-14">
          <div className="panel p-6 md:p-7">
            <SectionHeading
              kicker="Features"
              title="Everything you need to land the interview."
              text="From parsing to rewriting to exporting — the full workflow in one focused tool."
            />

            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {features.map((item) => {
                const Icon = item.icon
                return (
                  <div key={item.title} className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700 mb-3">
                      <Icon className="h-4.5 w-4.5" />
                    </div>
                    <h3 className="text-sm font-semibold text-slate-ink">{item.title}</h3>
                    <p className="mt-1 text-sm leading-6 text-zinc-600">{item.text}</p>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        {/* Why ResumeAI vs Manual */}
        <section className="page-shell pb-10 md:pb-14">
          <div className="panel p-6 md:p-7">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              <SectionHeading
                kicker="Why ResumeAI"
                title="Manual editing is slow, generic, and misses what recruiters scan for."
                text="Most candidates spend hours tailoring resumes without knowing what ATS systems actually look for. ResumeAI does this analysis in seconds."
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4">
                  <p className="text-sm font-semibold text-slate-ink mb-3">Manual Resume</p>
                  <ul className="space-y-2 text-sm text-zinc-600">
                    <li className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-zinc-400 shrink-0" />Time-consuming</li>
                    <li className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-zinc-400 shrink-0" />Misses ATS keywords</li>
                    <li className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-zinc-400 shrink-0" />Generic for every role</li>
                    <li className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-zinc-400 shrink-0" />Hard to customize at scale</li>
                  </ul>
                </div>
                <div className="rounded-2xl border border-brand-200 bg-brand-50/40 p-4">
                  <p className="text-sm font-semibold text-slate-ink mb-3">With ResumeAI</p>
                  <ul className="space-y-2 text-sm text-zinc-700">
                    <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-brand-700 shrink-0" />Done in minutes</li>
                    <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-brand-700 shrink-0" />ATS keyword optimized</li>
                    <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-brand-700 shrink-0" />Role-specific every time</li>
                    <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-brand-700 shrink-0" />Export-ready in one click</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" className="page-shell pb-8 md:pb-10">
          <div className="panel p-6 md:p-7">
            <SectionHeading
              kicker="FAQ"
              title="Common questions, honest answers."
            />

            <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-4">
              {faqItems.map((item) => (
                <details key={item.q} className="group rounded-2xl border border-zinc-200 bg-white p-5">
                  <summary className="cursor-pointer list-none text-sm font-semibold text-slate-ink flex items-center justify-between gap-4 min-h-[44px]">
                    <span>{item.q}</span>
                    <span className="flex-shrink-0 text-zinc-400 transition-transform duration-200 group-open:rotate-45">+</span>
                  </summary>
                  <p className="mt-3 text-sm leading-6 text-zinc-600">{item.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="bg-black">
        <div className="page-shell py-6">

          {/* Main row — constrained so columns don't spread too far apart */}
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">

            {/* Left — brand */}
            <div className="max-w-[220px]">
              <p className="text-sm font-semibold text-white">ResumeAI</p>
              <p className="mt-1 text-sm leading-6 text-white/45">
                Tailor your resume to any job description in minutes.
              </p>
            </div>

            {/* Center — page nav */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/30 mb-3">Product</p>
              <div className="flex flex-col gap-2">
                {[
                  { label: 'Features', href: '#features' },
                  { label: 'How it Works', href: '#how-it-works' },
                  { label: 'FAQ', href: '#faq' },
                ].map((item) => (
                  <a key={item.label} href={item.href} className="text-sm text-white/50 transition-colors hover:text-white">
                    {item.label}
                  </a>
                ))}
              </div>
            </div>

            {/* Right — connect */}
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-white/30 mb-3">Connect</p>
              <div className="flex flex-col gap-2">
                {footerLinks.map((item) => {
                  const Icon = item.icon
                  return (
                    <a
                      key={item.label}
                      href={item.href}
                      target={item.href.startsWith('http') ? '_blank' : undefined}
                      rel={item.href.startsWith('http') ? 'noreferrer' : undefined}
                      className="flex items-center gap-2 text-sm text-white/50 transition-colors hover:text-white"
                    >
                      <Icon className="w-3.5 h-3.5 shrink-0" />
                      {item.label}
                    </a>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Bottom bar — copyright inline, not orphaned */}
          <div className="mt-6 pt-5 border-t border-white/10 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-white/40">© {new Date().getFullYear()} Ayush Burde. All rights reserved.</p>
            <p className="text-xs text-white/20">Built with React · FastAPI · AI</p>
          </div>

        </div>
      </footer>
    </div>
  )
}

export default function Landing() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Sparkles className="w-6 h-6 text-brand animate-pulse" />
      </div>
    )
  }

  return <>{user ? <AppForm /> : <GuestWorkspace />}</>
}
