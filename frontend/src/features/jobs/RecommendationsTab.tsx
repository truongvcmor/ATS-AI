import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useRecommendations } from '../../services/hooks/useJobs'
import { useCreateApplication } from '../../services/hooks/useApplications'
import { Button } from '../../components/ui/Button'
import { AiScoreBadge } from '../../components/ui/Badge'
import { EmptyState } from '../../components/ui/EmptyState'
import { Skeleton } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'
import type { CandidateRecommendation } from '../../types'

function ScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(100, value))
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-500">
        <span>{label}</span>
        <span>{Math.round(pct)}</span>
      </div>
      <div className="mt-0.5 h-1.5 rounded-full bg-slate-100">
        <div className="h-1.5 rounded-full bg-brand-500" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function RecommendationRow({
  rec,
  jobId,
  onApplied,
}: {
  rec: CandidateRecommendation
  jobId: string
  onApplied: (candidateId: string) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const navigate = useNavigate()
  const createApplication = useCreateApplication(jobId)
  const toast = useToast()

  async function onAdd() {
    try {
      await createApplication.mutateAsync({ candidate_id: rec.candidate.id, job_id: jobId })
      toast.success(`${rec.candidate.full_name} added to pipeline`)
      onApplied(rec.candidate.id)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to add to pipeline')
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <button
            onClick={() => navigate(`/candidates/${rec.candidate.id}`)}
            className="text-sm font-semibold text-slate-800 hover:text-brand-700 hover:underline"
          >
            {rec.candidate.full_name}
          </button>
          <p className="text-xs text-slate-500">
            {rec.candidate.current_title ?? 'No title'} {rec.candidate.location ? `· ${rec.candidate.location}` : ''}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <AiScoreBadge score={rec.final_score} />
          <Button size="sm" onClick={onAdd} loading={createApplication.isPending}>
            + Add to pipeline
          </Button>
        </div>
      </div>

      <p className="mt-2 text-sm text-slate-600">{rec.explanation}</p>

      <button
        onClick={() => setExpanded((e) => !e)}
        className="mt-2 text-xs font-medium text-brand-600 hover:text-brand-700"
      >
        {expanded ? 'Hide details' : 'Show match details'}
      </button>

      {expanded && (
        <div className="mt-3 space-y-3 border-t border-slate-100 pt-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <ScoreBar label="Final" value={rec.final_score} />
            <ScoreBar label="Keyword" value={rec.keyword_score} />
            <ScoreBar label="Semantic" value={rec.semantic_score} />
            <ScoreBar label="Skills" value={rec.skill_match_score} />
            <ScoreBar label="Experience" value={rec.experience_score} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <div className="text-xs font-medium text-slate-500">Matched skills</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {rec.matched_skills.length === 0 && <span className="text-xs text-slate-400">None</span>}
                {rec.matched_skills.map((s) => (
                  <span key={s} className="rounded bg-emerald-50 px-1.5 py-0.5 text-xs text-emerald-700">
                    {s}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <div className="text-xs font-medium text-slate-500">Missing skills</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {rec.missing_skills.length === 0 && <span className="text-xs text-slate-400">None</span>}
                {rec.missing_skills.map((s) => (
                  <span key={s} className="rounded bg-red-50 px-1.5 py-0.5 text-xs text-red-700">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export function RecommendationsTab({ jobId }: { jobId: string }) {
  const recommend = useRecommendations(jobId)
  const toast = useToast()
  const [applied, setApplied] = useState<Set<string>>(new Set())

  useEffect(() => {
    recommend.mutate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId])

  function refresh() {
    recommend.mutate(undefined, {
      onError: (err) => toast.error(err instanceof ApiError ? err.message : 'Failed to load recommendations'),
    })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
        <span>AI-generated recommendation — recruiter makes the final decision.</span>
        <Button size="sm" variant="secondary" onClick={refresh} loading={recommend.isPending}>
          Refresh
        </Button>
      </div>

      {recommend.isPending ? (
        <div className="space-y-3">
          <Skeleton className="h-28 rounded-lg" />
          <Skeleton className="h-28 rounded-lg" />
          <Skeleton className="h-28 rounded-lg" />
        </div>
      ) : recommend.isError ? (
        <EmptyState
          title="Couldn't load recommendations"
          description={recommend.error instanceof ApiError ? recommend.error.message : 'Please try again.'}
          action={
            <Button size="sm" onClick={refresh}>
              Try again
            </Button>
          }
        />
      ) : !recommend.data || recommend.data.recommendations.length === 0 ? (
        <EmptyState
          title="No recommendations yet"
          description="Add candidates to the talent pool, or add job requirements, then refresh."
        />
      ) : (
        <div className="space-y-3">
          {recommend.data.recommendations.map((rec) => (
            <RecommendationRow
              key={rec.candidate.id}
              rec={rec}
              jobId={jobId}
              onApplied={(id) => setApplied((prev) => new Set(prev).add(id))}
            />
          ))}
          {applied.size > 0 && (
            <p className="text-xs text-slate-400">
              {applied.size} candidate{applied.size === 1 ? '' : 's'} added to the pipeline — check the Pipeline tab.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
