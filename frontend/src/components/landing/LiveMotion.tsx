import { useRef, type ReactNode, type MouseEvent } from 'react'
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useReducedMotion,
  type HTMLMotionProps,
} from 'framer-motion'
import { easeOutExpo, transitionFast } from '@/lib/motion'
import { cn } from '@/lib/utils'

/** Word-by-word hero title reveal */
export function AnimatedWords({
  text,
  className,
  as: Tag = 'h1',
}: {
  text: string
  className?: string
  as?: 'h1' | 'h2' | 'p'
}) {
  const reduceMotion = useReducedMotion()
  const words = text.split(' ')

  if (reduceMotion) {
    return <Tag className={className}>{text}</Tag>
  }

  return (
    <Tag className={cn(className, 'flex flex-wrap')}>
      {words.map((word, i) => (
        <span key={`${word}-${i}`} className="inline-block overflow-hidden mr-[0.28em] last:mr-0">
          <motion.span
            className="inline-block"
            initial={{ y: '110%', opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.55, ease: easeOutExpo, delay: 0.08 + i * 0.045 }}
          >
            {word}
          </motion.span>
        </span>
      ))}
    </Tag>
  )
}

/** Line fade-up for supporting copy */
export function AnimatedLine({
  children,
  className,
  delay = 0.35,
}: {
  children: ReactNode
  className?: string
  delay?: number
}) {
  const reduceMotion = useReducedMotion()
  return (
    <motion.p
      className={className}
      initial={reduceMotion ? false : { opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: easeOutExpo, delay }}
    >
      {children}
    </motion.p>
  )
}

/** CTA with arrow slide + press feedback */
export function HoverCTA({
  children,
  className,
  ...props
}: HTMLMotionProps<'div'>) {
  const reduceMotion = useReducedMotion()
  return (
    <motion.div
      className={cn('inline-flex', className)}
      whileHover={reduceMotion ? undefined : { y: -2 }}
      whileTap={reduceMotion ? undefined : { scale: 0.98 }}
      transition={transitionFast}
      {...props}
    >
      {children}
    </motion.div>
  )
}

/** Soft 3D tilt that follows the cursor */
export function TiltCard({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  const reduceMotion = useReducedMotion()
  const ref = useRef<HTMLDivElement>(null)
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const springX = useSpring(x, { stiffness: 160, damping: 18 })
  const springY = useSpring(y, { stiffness: 160, damping: 18 })
  const rotateX = useTransform(springY, [-0.5, 0.5], [7, -7])
  const rotateY = useTransform(springX, [-0.5, 0.5], [-9, 9])

  function onMove(e: MouseEvent) {
    if (reduceMotion || !ref.current) return
    const rect = ref.current.getBoundingClientRect()
    x.set((e.clientX - rect.left) / rect.width - 0.5)
    y.set((e.clientY - rect.top) / rect.height - 0.5)
  }

  function onLeave() {
    x.set(0)
    y.set(0)
  }

  if (reduceMotion) {
    return <div className={className}>{children}</div>
  }

  return (
    <motion.div
      ref={ref}
      className={cn('will-change-transform', className)}
      style={{ rotateX, rotateY, transformPerspective: 900 }}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
    >
      {children}
    </motion.div>
  )
}

/** Pulsing live indicator */
export function LiveDot({ label = 'Live' }: { label?: string }) {
  const reduceMotion = useReducedMotion()
  return (
    <span className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-zinc-500">
      <span className="relative flex h-2 w-2">
        {!reduceMotion && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
        )}
        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
      </span>
      {label}
    </span>
  )
}

/** Nav link with underline draw */
export function NavLinkMotion({
  href,
  children,
}: {
  href: string
  children: ReactNode
}) {
  return (
    <a
      href={href}
      className="group relative text-sm text-zinc-600 transition-colors hover:text-zinc-950"
    >
      {children}
      <span className="absolute -bottom-1 left-0 h-px w-0 bg-brand transition-all duration-300 ease-out group-hover:w-full" />
    </a>
  )
}
