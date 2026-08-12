import { cn } from '@/lib/utils'

function Shimmer({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'rounded-md bg-zinc-200/80 animate-pulse',
        className,
      )}
    />
  )
}

/** 21st-inspired dashboard stats skeleton — ResumeAI charcoal panels */
export function DashboardStatsSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('grid grid-cols-1 sm:grid-cols-3 gap-4', className)}>
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="stat-card space-y-3">
          <Shimmer className="h-8 w-16" />
          <Shimmer className="h-3 w-28" />
        </div>
      ))}
    </div>
  )
}

export function DashboardListSkeleton({ className }: { className?: string }) {
  return (
    <div className={cn('space-y-4', className)}>
      {Array.from({ length: 3 }).map((_, i) => (
        <div
          key={i}
          className="panel p-5 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="flex items-start gap-3 min-w-0 flex-1">
            <Shimmer className="h-10 w-10 rounded-2xl shrink-0" />
            <div className="space-y-2 flex-1 min-w-0">
              <Shimmer className="h-4 w-40 max-w-full" />
              <Shimmer className="h-3 w-56 max-w-full" />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <Shimmer className="h-9 w-28 rounded-xl" />
            <Shimmer className="h-9 w-9 rounded-xl" />
          </div>
        </div>
      ))}
    </div>
  )
}
