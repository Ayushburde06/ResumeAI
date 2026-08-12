import { Link, useLocation } from 'react-router-dom'
import { lazy, Suspense, useEffect, useState } from 'react'
import { motion, useReducedMotion, animate } from 'framer-motion'
import {
  ArrowRight,
  BadgeCheck,
  Brain,
  Check,
  FileText,
  Linkedin,
  Mail,
  PenTool,
  ShieldCheck,
  Sparkles,
  Upload,
  ClipboardCheck,
  Github,
  Zap,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { Button } from '@/components/ui/button'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Skeleton } from '@/components/ui/skeleton'
import { AnimatedFeatureCard } from '../components/AnimatedFeatureCard'
import { transitionBase, fadeUp, staggerContainer, scaleIn, easeOutExpo } from '../lib/motion'
import {
  AnimatedWords,
  AnimatedLine,
  HoverCTA,
  TiltCard,
  LiveDot,
  NavLinkMotion,
} from '../components/landing/LiveMotion'

const UnifiedWorkspace = lazy(() => import('../components/UnifiedWorkspace'))

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
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      className="max-w-2xl"
      initial={reduceMotion ? false : { opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.4 }}
      transition={transitionBase}
    >
      <p className="section-title mb-2">{kicker}</p>
      <h2 className="text-2xl md:text-3xl lg:text-4xl font-semibold tracking-tight text-slate-ink">{title}</h2>
      {text && <p className="mt-3 text-sm md:text-[15px] leading-7 text-zinc-600">{text}</p>}
    </motion.div>
  )
}

function GuestHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-zinc-200/70 bg-white/85 backdrop-blur-xl">
      <div className="page-shell h-16 flex items-center justify-between gap-4">
        <Link to="/" className="group flex items-center gap-3 min-w-0">
          <motion.div
            className="w-9 h-9 shrink-0 rounded-2xl bg-brand flex items-center justify-center shadow-[0_12px_24px_rgba(26,31,46,0.16)]"
            whileHover={{ scale: 1.06, rotate: -6 }}
            transition={{ type: 'spring', stiffness: 360, damping: 18 }}
          >
            <Sparkles className="w-4 h-4 text-white" />
          </motion.div>
          <span className="text-slate-ink text-[15px] font-semibold tracking-tight transition-colors group-hover:text-brand">
            ResumeAI
          </span>
        </Link>

        <nav className="hidden lg:flex items-center gap-6" aria-label="Page sections">
          {navLinks.map((item) => (
            <NavLinkMotion key={item.label} href={item.href}>
              {item.label}
            </NavLinkMotion>
          ))}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <Link to="/login" className="hidden sm:block">
            <HoverCTA>
              <Button variant="ghost" className="rounded-2xl px-4 text-zinc-600 hover:text-zinc-950 hover:bg-zinc-50">
                Sign In
              </Button>
            </HoverCTA>
          </Link>
          <Link to="/signup">
            <HoverCTA>
              <Button className="group rounded-2xl px-3 sm:px-4 text-sm">
                Get Started
                <ArrowRight className="ml-1.5 w-4 h-4 transition-transform duration-200 group-hover:translate-x-0.5" />
              </Button>
            </HoverCTA>
          </Link>
        </div>
      </div>
    </header>
  )
}

function AnimatedScore({ value, delay = 0.2 }: { value: number; delay?: number }) {
  const reduceMotion = useReducedMotion()
  const [display, setDisplay] = useState(reduceMotion ? value : 0)

  useEffect(() => {
    if (reduceMotion) {
      setDisplay(value)
      return
    }
    const controls = animate(0, value, {
      duration: 1.1,
      delay,
      ease: easeOutExpo,
      onUpdate: (v) => setDisplay(Math.round(v)),
    })
    return () => controls.stop()
  }, [value, delay, reduceMotion])

  return <>{display}%</>
}

function HeroPreview() {
  const reduceMotion = useReducedMotion()

  return (
    <TiltCard>
      <motion.div
        className="relative overflow-hidden rounded-3xl border border-zinc-200/80 bg-white shadow-[0_24px_70px_rgba(15,23,42,0.08)]"
        variants={reduceMotion ? undefined : scaleIn}
        initial={reduceMotion ? false : 'hidden'}
        animate="show"
        whileHover={reduceMotion ? undefined : { boxShadow: '0 28px 80px rgba(15,23,42,0.12)' }}
      >
        <div className="p-5 space-y-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <LiveDot label="Live analysis" />
              <p className="text-sm font-semibold text-slate-ink mt-1">Recruiter-ready output</p>
            </div>
            <motion.span
              className="inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-zinc-50 px-3 py-1.5 text-xs font-semibold text-zinc-700"
              initial={reduceMotion ? false : { opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ ...transitionBase, delay: 0.25 }}
              whileHover={reduceMotion ? undefined : { scale: 1.04, backgroundColor: '#f4f4f5' }}
            >
              <Sparkles className="h-3.5 w-3.5 text-brand" />
              PDF ready
            </motion.span>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <motion.div
              className="rounded-2xl border border-zinc-200 bg-white p-4 cursor-default"
              initial={reduceMotion ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...transitionBase, delay: 0.15 }}
              whileHover={reduceMotion ? undefined : { y: -3, borderColor: 'rgba(26,31,46,0.2)' }}
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">ATS Score</p>
              <p className="mt-3 text-3xl font-semibold text-slate-ink tabular-nums">
                <AnimatedScore value={92} delay={0.35} />
              </p>
              <p className="text-xs text-emerald-700 mt-1">+18 from original</p>
            </motion.div>
            <motion.div
              className="rounded-2xl border border-zinc-200 bg-white p-4 cursor-default"
              initial={reduceMotion ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ ...transitionBase, delay: 0.22 }}
              whileHover={reduceMotion ? undefined : { y: -3, borderColor: 'rgba(26,31,46,0.2)' }}
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">Role match</p>
              <p className="mt-3 text-3xl font-semibold text-slate-ink tabular-nums">
                <AnimatedScore value={87} delay={0.45} />
              </p>
              <div className="mt-3 h-2 w-full rounded-full bg-zinc-100 overflow-hidden">
                <motion.div
                  className="h-2 rounded-full bg-brand"
                  initial={reduceMotion ? { width: '87%' } : { width: 0 }}
                  animate={{ width: '87%' }}
                  transition={{ duration: 0.9, ease: easeOutExpo, delay: 0.5 }}
                />
              </div>
            </motion.div>
          </div>

          <motion.div
            className="rounded-2xl border border-zinc-200 bg-white p-4"
            initial={reduceMotion ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...transitionBase, delay: 0.3 }}
          >
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500 mb-3">Missing keywords</p>
            <div className="flex flex-wrap gap-2">
              {['PostgreSQL', 'REST API', 'JWT', 'Docker'].map((item, i) => (
                <motion.span
                  key={item}
                  className="cursor-default rounded-full border border-amber-100 bg-amber-50 px-2.5 py-1 text-[11px] font-medium text-amber-700"
                  initial={reduceMotion ? false : { opacity: 0, scale: 0.85 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3, ease: easeOutExpo, delay: 0.45 + i * 0.06 }}
                  whileHover={reduceMotion ? undefined : { scale: 1.06, y: -2 }}
                >
                  {item}
                </motion.span>
              ))}
            </div>
          </motion.div>
        </div>
      </motion.div>
    </TiltCard>
  )
}

function AppForm() {
  const location = useLocation()
  const state = location.state as { result?: any; job_description?: string } | null

  
  return (
    <div className="h-[calc(100vh-3.5rem)] overflow-hidden flex flex-col">
      <Suspense
        fallback={
          <div className="flex flex-1 flex-col gap-4 p-6" aria-busy="true" aria-label="Loading workspace">
            <div className="grid flex-1 gap-6 lg:grid-cols-2">
              <div className="space-y-4">
                <Skeleton className="h-40 w-full rounded-3xl bg-zinc-200" />
                <Skeleton className="h-52 w-full rounded-3xl bg-zinc-200" />
                <Skeleton className="h-12 w-full rounded-2xl bg-zinc-200" />
              </div>
              <Skeleton className="min-h-[400px] w-full rounded-3xl bg-zinc-200" />
            </div>
          </div>
        }
      >
        <UnifiedWorkspace
          initialResult={state?.result}
          initialJd={state?.job_description ?? ''}
          initialInterviewPrep={state?.result?.interview_prep ?? null}
          
        />
      </Suspense>
    </div>
  )
}

function GuestWorkspace() {
  const reduceMotion = useReducedMotion()

  return (
    <div className="min-h-[calc(100vh-4rem)] text-slate-ink">
      <GuestHeader />

      <main>
        <section className="page-shell py-10 md:py-16 lg:py-20">
          <div className="grid grid-cols-1 lg:grid-cols-[1.08fr_0.92fr] gap-8 lg:gap-10 items-center">
            <motion.div
              className="space-y-6"
              variants={reduceMotion ? undefined : staggerContainer}
              initial={reduceMotion ? false : 'hidden'}
              animate="show"
            >
              <div className="space-y-4">
                <AnimatedWords
                  text="Optimize Your Resume for ATS & Recruiters"
                  className="hero-title leading-[1.05]"
                />
                <AnimatedLine className="hero-copy max-w-xl" delay={0.42}>
                  Upload your resume and a job description. ResumeAI finds missing keywords, rewrites the necessary sections, and exports a recruiter-ready PDF — without inventing experience.
                </AnimatedLine>
              </div>

              <motion.div
                className="flex flex-col sm:flex-row flex-wrap gap-3"
                variants={reduceMotion ? undefined : fadeUp}
              >
                <HoverCTA className="sm:inline-flex w-full sm:w-auto">
                  <Link to="/signup" className="w-full sm:w-auto">
                    <Button size="lg" className="group w-full sm:w-auto px-6">
                      Optimize My Resume
                      <ArrowRight className="ml-1.5 w-4 h-4 transition-transform duration-200 group-hover:translate-x-1" />
                    </Button>
                  </Link>
                </HoverCTA>
                <HoverCTA className="sm:inline-flex w-full sm:w-auto">
                  <a href="#how-it-works" className="w-full sm:w-auto">
                    <Button variant="outline" size="lg" className="w-full sm:w-auto px-6">
                      See How It Works
                    </Button>
                  </a>
                </HoverCTA>
              </motion.div>

              <motion.div
                className="flex flex-wrap gap-2 text-xs text-zinc-500"
                variants={reduceMotion ? undefined : fadeUp}
              >
                {['No fake experience', 'ATS-friendly output', 'PDF export ready'].map((label) => (
                  <motion.span
                    key={label}
                    className="cursor-default rounded-full border border-zinc-200 bg-white px-3 py-1.5"
                    whileHover={
                      reduceMotion
                        ? undefined
                        : { y: -3, scale: 1.03, borderColor: '#a1a1aa', backgroundColor: '#fafafa' }
                    }
                    transition={{ type: 'spring', stiffness: 400, damping: 22 }}
                  >
                    {label}
                  </motion.span>
                ))}
              </motion.div>
            </motion.div>

            <div className="hidden lg:block lg:pl-4">
              <HeroPreview />
            </div>
          </div>
        </section>

        <section id="how-it-works" className="page-shell pb-10 md:pb-14">
          <motion.div
            className="panel p-6 md:p-7"
            initial={reduceMotion ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={transitionBase}
          >
            <SectionHeading
              kicker="How it works"
              title="Three steps from upload to optimized resume."
            />

            <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-5">
              {howItWorks.map((item, index) => (
                <AnimatedFeatureCard
                  key={item.title}
                  title={item.title}
                  description={item.text}
                  icon={item.icon}
                  step={`0${index + 1}`}
                  delay={index * 0.08}
                />
              ))}
            </div>
          </motion.div>
        </section>

        <section id="features" className="page-shell pb-10 md:pb-14">
          <motion.div
            className="panel p-6 md:p-7"
            initial={reduceMotion ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.15 }}
            transition={transitionBase}
          >
            <SectionHeading
              kicker="Features"
              title="Everything you need to land the interview."
              text="From parsing to rewriting to exporting — the full workflow in one focused tool."
            />

            <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {features.map((item, index) => (
                <AnimatedFeatureCard
                  key={item.title}
                  title={item.title}
                  description={item.text}
                  icon={item.icon}
                  delay={(index % 3) * 0.06}
                />
              ))}
            </div>
          </motion.div>
        </section>

        <section className="page-shell pb-10 md:pb-14">
          <motion.div
            className="panel p-6 md:p-7"
            initial={reduceMotion ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.2 }}
            transition={transitionBase}
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
              <SectionHeading
                kicker="Why ResumeAI"
                title="Manual editing is slow and misses what ATS systems scan for."
                text="Most candidates spend hours tailoring resumes without knowing what recruiters actually look for. ResumeAI does this analysis in seconds."
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <motion.div
                  className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4 cursor-default"
                  initial={reduceMotion ? false : { opacity: 0, x: -12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ ...transitionBase, delay: 0.1 }}
                  whileHover={reduceMotion ? undefined : { y: -4, borderColor: '#d4d4d8' }}
                >
                  <p className="text-sm font-semibold text-slate-ink mb-3">Manual Resume</p>
                  <ul className="space-y-2 text-sm text-zinc-600">
                    <li className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-zinc-400 shrink-0" />Time-consuming</li>
                    <li className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-zinc-400 shrink-0" />Misses ATS keywords</li>
                    <li className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-zinc-400 shrink-0" />Generic for every role</li>
                  </ul>
                </motion.div>
                <motion.div
                  className="rounded-2xl border border-brand-200 bg-brand-50/40 p-4 cursor-default"
                  initial={reduceMotion ? false : { opacity: 0, x: 12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ ...transitionBase, delay: 0.18 }}
                  whileHover={reduceMotion ? undefined : { y: -4, borderColor: 'rgba(66,84,113,0.45)' }}
                >
                  <p className="text-sm font-semibold text-slate-ink mb-3">With ResumeAI</p>
                  <ul className="space-y-2 text-sm text-zinc-700">
                    <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-brand-700 shrink-0" />Done in minutes</li>
                    <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-brand-700 shrink-0" />ATS keyword optimized</li>
                    <li className="flex items-center gap-2"><Check className="h-3.5 w-3.5 text-brand-700 shrink-0" />Export-ready in one click</li>
                  </ul>
                </motion.div>
              </div>
            </div>
          </motion.div>
        </section>

        <section id="faq" className="page-shell pb-8 md:pb-10">
          <motion.div
            className="panel p-6 md:p-7"
            initial={reduceMotion ? false : { opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.15 }}
            transition={transitionBase}
          >
            <SectionHeading
              kicker="FAQ"
              title="Common questions, honest answers."
            />

            <Accordion className="mt-8 w-full gap-0 rounded-2xl border border-zinc-200 bg-white px-2 sm:px-4">
              {faqItems.map((item) => (
                <AccordionItem
                  key={item.q}
                  value={item.q}
                  className="border-zinc-100 px-2 not-last:border-b"
                >
                  <AccordionTrigger className="py-4 text-sm font-semibold text-slate-ink hover:no-underline hover:text-brand">
                    {item.q}
                  </AccordionTrigger>
                  <AccordionContent className="pb-4 text-sm leading-6 text-zinc-600">
                    <p>{item.a}</p>
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </motion.div>
        </section>
      </main>

      <footer className="bg-black">
        <div className="page-shell py-6">
          <div className="flex flex-col gap-6 sm:flex-row sm:items-start sm:justify-between">
            <div className="max-w-[220px]">
              <p className="text-sm font-semibold text-white">ResumeAI</p>
              <p className="mt-1 text-sm leading-6 text-white/45">
                Tailor your resume to any job description in minutes.
              </p>
            </div>

            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/30 mb-3">Product</p>
              <div className="flex flex-col gap-2">
                {navLinks.map((item) => (
                  <a key={item.label} href={item.href} className="text-sm text-white/50 transition-colors hover:text-white">
                    {item.label}
                  </a>
                ))}
              </div>
            </div>

            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/30 mb-3">Connect</p>
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
      <div className="min-h-screen flex items-center justify-center" aria-busy="true" aria-label="Loading">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-300 border-t-brand" />
      </div>
    )
  }

  return <>{user ? <AppForm /> : <GuestWorkspace />}</>
}
