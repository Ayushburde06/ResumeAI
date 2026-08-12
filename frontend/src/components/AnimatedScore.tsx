import { useEffect, useState } from 'react'
import { animate } from 'framer-motion'

export function AnimatedScore({
  score,
  className,
}: {
  score: number
  className?: string
}) {
  const [displayScore, setDisplayScore] = useState(0)

  useEffect(() => {
    const controls = animate(displayScore, score, {
      duration: 1.5,
      ease: 'easeOut',
      onUpdate(value) {
        setDisplayScore(Math.round(value))
      },
    })
    return () => controls.stop()
  }, [score])

  return <span className={className}>{displayScore}</span>
}
