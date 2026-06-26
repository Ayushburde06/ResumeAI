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
  LayoutGrid,
  Lock,
  PenTool,
  ShieldCheck,
  Sparkles,
  Upload,
  Wand2,
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

const trustCards = [
  {
    icon: ShieldCheck,
    title: 'ATS Optimized',
    text: 'Pass applicant tracking systems with cleaner structure and stronger keyword coverage.',
  },
  {
    icon: Wand2,
    title: 'AI Keyword Analysis',
    text: 'Find missing skills, role terms, and recruiter language from the job description.',
  },
  {
    icon: Lock,
    title: 'No Fake Experience',
    text: 'Only improves what is already on the resume. No invented jobs, metrics, or claims.',
  },
  {
    icon: BadgeCheck,
    title: 'Export Ready',
    text: 'Download a professional PDF resume with recruiter-friendly formatting instantly.',
  },
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
  { icon: FileText, title: 'Resume Parsing', text: 'Extract text from PDF and DOCX uploads.' },
  { icon: Brain, title: 'ATS Keyword Matching', text: 'Compare your resume to the job description.' },
  { icon: BookOpen, title: 'Job Description Analysis', text: 'Pull out required and preferred terms.' },
  { icon: PenTool, title: 'AI Resume Rewrite', text: 'Improve targeted sections without adding fluff.' },
  { icon: ClipboardCheck, title: 'Grammar Improvements', text: 'Clean up wording and readability.' },
  { icon: Check, title: 'Achievement Enhancement', text: 'Strengthen bullets with clear outcomes.' },
  { icon: LayoutGrid, title: 'Multiple Versions', text: 'Keep history and compare tailored versions.' },
  { icon: Sparkles, title: 'PDF Export', text: 'Export polished PDFs for applications.' },
  { icon: Zap, title: 'Resume Score', text: 'See ATS and readability signals at a glance.' },
  { icon: GitBranch, title: 'Gap Analysis', text: 'Understand missing skills before applying.' },
  { icon: ShieldCheck, title: 'No Hallucinations', text: 'Protect the facts that matter to recruiters.' },
  { icon: BadgeCheck, title: 'Recruiter Friendly Formatting', text: 'Keep the output clean and easy to scan.' },
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
  { label: 'GitHub', href: 'https://github.com/' },
  { label: 'LinkedIn', href: 'https://www.linkedin.com/' },
  { label: 'Mail', href: 'mailto:hello@resumeai.dev' },
]

function SectionHeading({
  kicker,
  title,
  text,
}: {
  kicker: string
  title: string
  text: string
}) {
  return (
    <div className="max-w-2xl">
      <p className="section-title mb-2">{kicker}</p>
      <h2 className="text-2xl md:text-3xl font-semibold tracking-tight text-slate-ink">{title}</h2>
      <p className="mt-3 text-sm md:text-[15px] leading-7 text-zinc-600">{text}</p>
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
          <div className="leading-tight min-w-0">
            <span className="block text-slate-ink text-[15px] font-semibold tracking-tight">ResumeAI</span>
            <span className="hidden sm:block text-[10px] uppercase tracking-[0.24em] text-zinc-500">Resume optimization workspace</span>
          </div>
        </Link>

        <nav className="hidden lg:flex items-center gap-6">
          {navLinks.map((item) => (
            <a key={item.label} href={item.href} className="text-sm text-zinc-600 hover:text-zinc-950 transition-colors">
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <Link to="/login">
            <Button variant="ghost" className="rounded-2xl px-4 text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50">
              Sign In
            </Button>
          </Link>
          <Link to="/signup">
            <Button className="rounded-2xl bg-brand px-4 text-white shadow-[0_14px_28px_rgba(26,31,46,0.14)] hover:bg-brand-hover">
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
        <section className="page-shell py-10 md:py-14 lg:py-16">
          <div className="grid grid-cols-1 lg:grid-cols-[1.08fr_0.92fr] gap-8 lg:gap-10 items-center">
            <motion.div {...motionProps()} className="space-y-7">
              <div className="inline-flex items-center gap-2 rounded-full border border-zinc-200/80 bg-white/80 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-zinc-600 shadow-sm">
                <span className="h-2 w-2 rounded-full bg-brand" />
                Production-ready resume optimization
              </div>

              <div className="space-y-4">
                <h1 className="max-w-3xl text-4xl md:text-5xl lg:text-[62px] font-semibold tracking-tight leading-[1.02] text-slate-ink">
                  Optimize Your Resume for ATS & Recruiters in Minutes
                </h1>
                <p className="max-w-2xl text-[17px] md:text-lg leading-8 text-zinc-600">
                  Upload your resume and a job description. ResumeAI analyzes both, finds missing keywords, rewrites only the necessary sections, and generates a recruiter-ready resume without inventing experience.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Link to="/signup">
                  <Button className="rounded-2xl bg-brand px-6 py-3 text-white shadow-[0_18px_42px_rgba(26,31,46,0.16)] hover:bg-brand-hover">
                    Optimize My Resume
                    <ArrowRight className="ml-1.5 w-4 h-4" />
                  </Button>
                </Link>
                <a href="#product-preview">
                  <Button variant="outline" className="rounded-2xl border-zinc-200 bg-white px-6 py-3 text-zinc-800 hover:bg-zinc-50">
                    View Demo
                  </Button>
                </a>
              </div>

              <div className="flex flex-wrap gap-3 text-xs text-zinc-500">
                <span className="rounded-full border border-zinc-200 bg-white px-3 py-1.5">No fake experience</span>
                <span className="rounded-full border border-zinc-200 bg-white px-3 py-1.5">ATS-friendly output</span>
                <span className="rounded-full border border-zinc-200 bg-white px-3 py-1.5">PDF export ready</span>
              </div>
            </motion.div>

            <motion.div {...motionProps(0.08)} className="lg:pl-4">
              <HeroDashboard />
            </motion.div>
          </div>
        </section>

        <section className="page-shell pb-10 md:pb-14">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            {trustCards.map((item, index) => {
              const Icon = item.icon
              return (
                <motion.div
                  key={item.title}
                  {...motionProps(0.03 * index)}
                  className="panel p-5"
                >
                  <div className="flex items-start gap-3">
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-700">
                      <Icon className="h-4.5 w-4.5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-semibold text-slate-ink">{item.title}</h3>
                      <p className="mt-1 text-sm leading-6 text-zinc-600">{item.text}</p>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </section>

        <section id="how-it-works" className="page-shell pb-10 md:pb-14">
          <div className="panel p-6 md:p-7">
            <SectionHeading
              kicker="How it works"
              title="Three simple steps. No noisy workflow jargon."
              text="Keep the experience obvious: upload the resume, paste the job description, then download the optimized version."
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

        <section id="product-preview" className="page-shell pb-10 md:pb-14">
          <div className="panel p-6 md:p-7">
            <SectionHeading
              kicker="Product preview"
              title="A product dashboard that proves the output, not the buzzwords."
              text="Show the recruiter-facing artifacts directly: score, match, missing keywords, gap analysis, rewrite, and the final resume."
            />

            <div className="mt-8 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {[
                { title: 'Resume Analysis', detail: 'Source resume parsed and structured', accent: 'bg-slate-950' },
                { title: 'ATS Score', detail: '92% match for the target role', accent: 'bg-brand' },
                { title: 'Keyword Match', detail: 'Important terms highlighted for review', accent: 'bg-emerald-600' },
                { title: 'Skill Gap Analysis', detail: 'Missing keywords grouped by priority', accent: 'bg-amber-500' },
                { title: 'Resume Rewrite', detail: 'Only the necessary sections improved', accent: 'bg-indigo-600' },
                { title: 'Final Resume', detail: 'Download-ready recruiter format', accent: 'bg-zinc-900' },
              ].map((item) => (
                <div key={item.title} className="rounded-2xl border border-zinc-200 bg-white p-4 shadow-[0_10px_24px_rgba(15,23,42,0.04)]">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-slate-ink">{item.title}</p>
                    <div className={`h-2.5 w-2.5 rounded-full ${item.accent}`} />
                  </div>
                  <div className="mt-4 space-y-2">
                    <div className="h-2 w-11/12 rounded-full bg-zinc-100" />
                    <div className="h-2 w-3/4 rounded-full bg-zinc-100" />
                    <div className="h-2 w-5/6 rounded-full bg-zinc-100" />
                  </div>
                  <p className="mt-4 text-xs leading-5 text-zinc-500">{item.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="features" className="page-shell pb-10 md:pb-14">
          <div className="panel p-6 md:p-7">
            <SectionHeading
              kicker="Features"
              title="Everything needed for a serious resume optimization workflow."
              text="The page should make it clear why someone would actually use the product, not just admire the interface."
            />

            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {features.map((item) => {
                const Icon = item.icon
                return (
                  <div key={item.title} className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-zinc-50 text-zinc-700">
                        <Icon className="h-4.5 w-4.5" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-slate-ink">{item.title}</h3>
                        <p className="mt-1 text-sm leading-6 text-zinc-600">{item.text}</p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <section id="pricing" className="page-shell pb-10 md:pb-14">
          <div className="grid grid-cols-1 lg:grid-cols-[0.95fr_1.05fr] gap-4">
            <div className="panel p-6 md:p-7">
              <SectionHeading
                kicker="Why choose ResumeAI"
                title="Manual editing is slow, generic, and easy to get wrong."
                text="This comparison should help a visitor understand the value in one glance."
              />
            </div>
            <div className="grid gap-4">
              <div className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4">
                    <p className="text-sm font-semibold text-slate-ink">Manual Resume</p>
                    <ul className="mt-3 space-y-2 text-sm text-zinc-600">
                      <li>Time-consuming</li>
                      <li>Misses ATS keywords</li>
                      <li>Generic resume</li>
                      <li>Hard to customize</li>
                    </ul>
                  </div>
                  <div className="rounded-2xl border border-brand-100 bg-brand-50/50 p-4">
                    <p className="text-sm font-semibold text-slate-ink">ResumeAI</p>
                    <ul className="mt-3 space-y-2 text-sm text-zinc-700">
                      <li>AI powered</li>
                      <li>ATS optimized</li>
                      <li>Role specific</li>
                      <li>Recruiter friendly</li>
                    </ul>
                  </div>
                </div>
              </div>
              <div className="panel p-5">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">Pricing</p>
                    <p className="mt-1 text-base font-semibold text-slate-ink">Build the product story first, monetize later.</p>
                  </div>
                  <span className="rounded-full border border-zinc-200 bg-white px-3 py-1.5 text-xs font-semibold text-zinc-600">Coming soon</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="faq" className="page-shell pb-12 md:pb-16">
          <div className="panel p-6 md:p-7">
            <SectionHeading
              kicker="FAQ"
              title="Answer the trust questions before they become objections."
              text="Keep the answers short, factual, and reassuring."
            />

            <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-4">
              {faqItems.map((item) => (
                <details key={item.q} className="group rounded-2xl border border-zinc-200 bg-white p-5">
                  <summary className="cursor-pointer list-none text-sm font-semibold text-slate-ink flex items-center justify-between gap-4">
                    <span>{item.q}</span>
                    <span className="text-zinc-400 transition-transform group-open:rotate-45">+</span>
                  </summary>
                  <p className="mt-3 text-sm leading-6 text-zinc-600">{item.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-zinc-200 bg-white/80">
        <div className="page-shell py-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-ink">ResumeAI</p>
              <p className="mt-1 text-sm text-zinc-500">A premium resume optimization workspace for recruiter-ready output.</p>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-zinc-600">
              {footerLinks.map((item) => (
                <a
                  key={item.label}
                  href={item.href}
                  className="hover:text-zinc-950 transition-colors"
                >
                  {item.label}
                </a>
              ))}
            </div>
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
