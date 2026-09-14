import type { ReactNode } from 'react'

type Tone = 'slate' | 'indigo' | 'green' | 'red' | 'amber' | 'blue'

const toneClasses: Record<Tone, string> = {
  slate: 'bg-slate-100 text-slate-700',
  indigo: 'bg-brand-50 text-brand-700',
  green: 'bg-emerald-50 text-emerald-700',
  red: 'bg-red-50 text-red-700',
  amber: 'bg-amber-50 text-amber-700',
  blue: 'bg-sky-50 text-sky-700',
}

export function Badge({
  children,
  tone = 'slate',
  className = '',
  dot,
}: {
  children: ReactNode
  tone?: Tone
  className?: string
  dot?: string
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${toneClasses[tone]} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: dot }} />}
      {children}
    </span>
  )
}

export function ColorBadge({ name, color }: { name: string; color: string }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ backgroundColor: `${color}1a`, color }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {name}
    </span>
  )
}

export function scoreTone(score: number | null | undefined): Tone {
  if (score === null || score === undefined) return 'slate'
  if (score >= 80) return 'green'
  if (score >= 60) return 'blue'
  if (score >= 40) return 'amber'
  return 'red'
}

export function AiScoreBadge({ score }: { score: number | null | undefined }) {
  if (score === null || score === undefined) {
    return <Badge tone="slate">—</Badge>
  }
  return <Badge tone={scoreTone(score)}>{Math.round(score)}</Badge>
}

const statusTones: Record<string, Tone> = {
  NEW: 'blue',
  ACTIVE: 'indigo',
  IN_PROCESS: 'amber',
  HIRED: 'green',
  ARCHIVED: 'slate',
}

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={statusTones[status] ?? 'slate'}>{status.replace('_', ' ')}</Badge>
}

const recommendationTones: Record<string, Tone> = {
  STRONG_MATCH: 'green',
  MATCH: 'blue',
  POSSIBLE_MATCH: 'amber',
  WEAK_MATCH: 'red',
  STRONG_HIRE: 'green',
  HIRE: 'blue',
  MAYBE: 'amber',
  NO_HIRE: 'red',
}

export function RecommendationBadge({ recommendation }: { recommendation: string }) {
  return <Badge tone={recommendationTones[recommendation] ?? 'slate'}>{recommendation.replace(/_/g, ' ')}</Badge>
}
