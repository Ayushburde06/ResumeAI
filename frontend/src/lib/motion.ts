import type { Transition, Variants } from 'framer-motion'

export const easeOutExpo: [number, number, number, number] = [0.16, 1, 0.3, 1]

export const transitionBase: Transition = {
  duration: 0.45,
  ease: easeOutExpo,
}

export const transitionFast: Transition = {
  duration: 0.28,
  ease: easeOutExpo,
}

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: {
    opacity: 1,
    y: 0,
    transition: transitionBase,
  },
}

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: transitionBase,
  },
}

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.96, y: 12 },
  show: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: transitionBase,
  },
}

export const staggerContainer: Variants = {
  hidden: { opacity: 1 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.06,
    },
  },
}

export const staggerFast: Variants = {
  hidden: { opacity: 1 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.04,
    },
  },
}
