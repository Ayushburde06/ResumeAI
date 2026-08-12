import type { LucideIcon } from 'lucide-react'
import { motion, useReducedMotion } from 'framer-motion'
import { cn } from '@/lib/utils'
import { easeOutExpo } from '@/lib/motion'

interface AnimatedFeatureCardProps {
  title: string
  description: string
  icon: LucideIcon
  step?: string
  className?: string
  delay?: number
}

export function AnimatedFeatureCard({
  title,
  description,
  icon: Icon,
  step,
  className,
  delay = 0,
}: AnimatedFeatureCardProps) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      className={cn(
        'group relative flex w-full flex-col overflow-hidden rounded-2xl border border-zinc-200/80 bg-white p-5 shadow-[0_10px_30px_rgba(15,23,42,0.04)]',
        className,
      )}
      initial={reduceMotion ? false : { opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ duration: 0.45, ease: easeOutExpo, delay }}
      whileHover={
        reduceMotion
          ? undefined
          : {
              y: -6,
              borderColor: 'rgba(26, 31, 46, 0.18)',
              boxShadow: '0 18px 40px rgba(15,23,42,0.10)',
              transition: { duration: 0.22 },
            }
      }
    >
      <motion.div
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background:
            'radial-gradient(circle at 20% 0%, rgba(26,31,46,0.06), transparent 55%)',
        }}
      />

      <div className="relative flex items-center gap-3">
        <motion.div
          className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-50 text-brand-700"
          whileHover={reduceMotion ? undefined : { scale: 1.08, rotate: -4 }}
          transition={{ type: 'spring', stiffness: 320, damping: 18 }}
        >
          <Icon className="h-5 w-5" />
        </motion.div>
        {step && (
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-400">
            {step}
          </span>
        )}
      </div>
      <h3 className="relative mt-4 text-base font-semibold text-slate-ink transition-colors group-hover:text-brand">
        {title}
      </h3>
      <p className="relative mt-2 text-sm leading-6 text-zinc-600">{description}</p>
    </motion.div>
  )
}
