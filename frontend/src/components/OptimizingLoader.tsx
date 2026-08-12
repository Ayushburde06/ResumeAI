import { useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { Brain, CheckCircle2, FileSearch, Sparkles } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import { easeOutExpo, transitionFast } from '@/lib/motion'

const STAGES = [
  { label: 'Parsing resume structure', icon: FileSearch },
  { label: 'Matching JD keywords', icon: Brain },
  { label: 'Rewriting weak sections', icon: Sparkles },
  { label: 'Checking ATS fit', icon: CheckCircle2 },
] as const

interface Props {
  className?: string
  title?: string
}

export default function OptimizingLoader({
  className,
  title = 'Optimizing your resume',
}: Props) {
  const reduceMotion = useReducedMotion()
  const [stage, setStage] = useState(0)
  const [progress, setProgress] = useState(12)

  useEffect(() => {
    if (reduceMotion) {
      setStage(STAGES.length - 1)
      setProgress(72)
      return
    }

    const stageTimer = window.setInterval(() => {
      setStage((prev) => (prev + 1) % STAGES.length)
    }, 2200)

    const progressTimer = window.setInterval(() => {
      setProgress((prev) => {
        if (prev >= 92) return 18
        return prev + Math.floor(Math.random() * 7) + 3
      })
    }, 700)

    return () => {
      window.clearInterval(stageTimer)
      window.clearInterval(progressTimer)
    }
  }, [reduceMotion])

  const ActiveIcon = STAGES[stage].icon

  return (
    <div
      className={cn(
        'panel flex flex-1 flex-col gap-6 p-6 min-h-[400px]',
        className,
      )}
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label={title}
    >
      <div className="flex items-start gap-4">
        <motion.div
          className="relative flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-brand-100 bg-brand-50 text-brand"
          animate={reduceMotion ? undefined : { scale: [1, 1.05, 1] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
        >
          {!reduceMotion && (
            <span className="absolute inset-0 rounded-2xl bg-brand/10 animate-ping opacity-40" />
          )}
          <ActiveIcon className="relative h-5 w-5" />
        </motion.div>

        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              {!reduceMotion && (
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
              )}
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
              Live optimization
            </p>
          </div>
          <h3 className="text-base font-semibold text-zinc-950">{title}</h3>
          <div className="h-5 overflow-hidden">
            <AnimatePresence mode="wait">
              <motion.p
                key={STAGES[stage].label}
                className="text-sm text-zinc-600"
                initial={reduceMotion ? false : { opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduceMotion ? undefined : { opacity: 0, y: -8 }}
                transition={transitionFast}
              >
                {STAGES[stage].label}…
              </motion.p>
            </AnimatePresence>
          </div>
        </div>
      </div>

      <Progress value={progress} className="w-full">
        <span className="sr-only">Optimization progress {progress}%</span>
      </Progress>

      <ul className="grid gap-2 sm:grid-cols-2">
        {STAGES.map((item, index) => {
          const done = index < stage
          const active = index === stage
          const Icon = item.icon
          return (
            <motion.li
              key={item.label}
              className={cn(
                'flex items-center gap-2.5 rounded-xl border px-3 py-2.5 text-sm transition-colors',
                active && 'border-brand-200 bg-brand-50/50 text-zinc-900',
                done && 'border-emerald-100 bg-emerald-50/40 text-emerald-800',
                !active && !done && 'border-zinc-200 bg-white text-zinc-400',
              )}
              animate={
                reduceMotion || !active
                  ? undefined
                  : { borderColor: ['rgba(26,31,46,0.12)', 'rgba(26,31,46,0.28)', 'rgba(26,31,46,0.12)'] }
              }
              transition={{ duration: 1.4, repeat: Infinity, ease: 'easeInOut' }}
            >
              <Icon className={cn('h-3.5 w-3.5 shrink-0', active && 'text-brand', done && 'text-emerald-600')} />
              <span className="truncate">{item.label}</span>
              {done && <CheckCircle2 className="ml-auto h-3.5 w-3.5 text-emerald-600" />}
            </motion.li>
          )
        })}
      </ul>

      <div className="mt-auto space-y-3 rounded-2xl border border-zinc-200 bg-zinc-50/70 p-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-3 w-24 bg-zinc-200" />
          <Skeleton className="h-3 w-12 bg-zinc-200" />
        </div>
        <Skeleton className="h-3 w-full bg-zinc-200" />
        <Skeleton className="h-3 w-[92%] bg-zinc-200" />
        <Skeleton className="h-3 w-[78%] bg-zinc-200" />
        <div className="grid grid-cols-3 gap-2 pt-1">
          <Skeleton className="h-16 rounded-xl bg-zinc-200" />
          <Skeleton className="h-16 rounded-xl bg-zinc-200" />
          <Skeleton className="h-16 rounded-xl bg-zinc-200" />
        </div>
        {!reduceMotion && (
          <motion.div
            className="h-px w-full origin-left bg-gradient-to-r from-transparent via-brand/40 to-transparent"
            initial={{ scaleX: 0, opacity: 0 }}
            animate={{ scaleX: [0, 1, 0], opacity: [0, 1, 0] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: easeOutExpo }}
          />
        )}
      </div>
    </div>
  )
}
