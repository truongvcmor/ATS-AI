import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useJobs } from '../../services/hooks/useJobs'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { EmptyState } from '../../components/ui/EmptyState'
import { SkeletonCard } from '../../components/ui/Skeleton'
import { JobFormModal } from './JobFormModal'

const jobStatusTone: Record<string, 'green' | 'slate' | 'amber' | 'red'> = {
  OPEN: 'green',
  DRAFT: 'slate',
  PAUSED: 'amber',
  CLOSED: 'red',
}

export function JobsListPage() {
  const { data: jobs, isLoading } = useJobs()
  const navigate = useNavigate()
  const [formOpen, setFormOpen] = useState(false)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">Jobs</h1>
          <p className="text-sm text-slate-500">Open requisitions and their hiring pipelines.</p>
        </div>
        <Button onClick={() => setFormOpen(true)}>+ New job</Button>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : !jobs || jobs.length === 0 ? (
        <EmptyState
          title="No jobs yet"
          description="Create your first job to start screening and building a pipeline."
          action={<Button onClick={() => setFormOpen(true)}>+ New job</Button>}
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {jobs.map((job) => (
            <Card
              key={job.id}
              className="cursor-pointer p-4 transition hover:border-brand-300 hover:shadow-md"
              onClick={() => navigate(`/jobs/${job.id}`)}
            >
              <div className="flex items-start justify-between gap-2">
                <h3 className="text-sm font-semibold text-slate-900">{job.title}</h3>
                <Badge tone={jobStatusTone[job.status] ?? 'slate'}>{job.status}</Badge>
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {[job.department, job.location].filter(Boolean).join(' · ') || 'No department/location set'}
              </p>
              <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                <span>{job.employment_type.replace('_', ' ')}</span>
                <span>{job.application_count} applicant{job.application_count === 1 ? '' : 's'}</span>
              </div>
            </Card>
          ))}
        </div>
      )}

      <JobFormModal open={formOpen} onClose={() => setFormOpen(false)} onSaved={(job) => navigate(`/jobs/${job.id}`)} />
    </div>
  )
}
