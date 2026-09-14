import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useDeleteJob, useJob, useScreenJob } from '../../services/hooks/useJobs'
import { Tabs } from '../../components/ui/Tabs'
import { Card, CardBody, CardHeader } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { EmptyState } from '../../components/ui/EmptyState'
import { Skeleton } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'
import { JobFormModal } from './JobFormModal'
import { KanbanBoard } from '../pipeline/KanbanBoard'
import { RecommendationsTab } from './RecommendationsTab'

const jobStatusTone: Record<string, 'green' | 'slate' | 'amber' | 'red'> = {
  OPEN: 'green',
  DRAFT: 'slate',
  PAUSED: 'amber',
  CLOSED: 'red',
}

const TABS = [
  { key: 'overview', label: 'Overview / Requirements' },
  { key: 'pipeline', label: 'Pipeline' },
  { key: 'recommendations', label: 'Find Candidates' },
]

function Section({ title, content }: { title: string; content: string | null }) {
  if (!content) return null
  return (
    <div>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-400">{title}</h4>
      <p className="mt-1 whitespace-pre-line text-sm text-slate-700">{content}</p>
    </div>
  )
}

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const [tab, setTab] = useState('overview')
  const [editOpen, setEditOpen] = useState(false)

  const { data: job, isLoading, isError } = useJob(id)
  const deleteJob = useDeleteJob()
  const screenJob = useScreenJob(id ?? '')

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 rounded-lg" />
        <Skeleton className="h-64 rounded-lg" />
      </div>
    )
  }

  if (isError || !job) {
    return <EmptyState title="Job not found" description="This job may have been deleted." />
  }

  async function onDelete() {
    if (!id || !job) return
    if (!confirm(`Delete job "${job.title}"? This cannot be undone.`)) return
    try {
      await deleteJob.mutateAsync(id)
      toast.success('Job deleted')
      navigate('/jobs')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to delete job')
    }
  }

  async function onScreenAll() {
    try {
      const results = await screenJob.mutateAsync(undefined)
      toast.success(`Screened ${results.length} applicant(s)`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Screening failed')
    }
  }

  return (
    <div className="space-y-5">
      <Link to="/jobs" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to Jobs
      </Link>

      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold text-slate-900">{job.title}</h1>
              <Badge tone={jobStatusTone[job.status] ?? 'slate'}>{job.status}</Badge>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              {[job.department, job.location, job.employment_type.replace('_', ' ')].filter(Boolean).join(' · ')}
            </p>
            <p className="mt-1 text-xs text-slate-400">{job.application_count} applicant(s)</p>
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={onScreenAll} loading={screenJob.isPending}>
              Screen all applicants
            </Button>
            <Button variant="secondary" onClick={() => setEditOpen(true)}>
              Edit
            </Button>
            <Button variant="danger" onClick={onDelete}>
              Delete
            </Button>
          </div>
        </div>
      </Card>

      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      {tab === 'overview' && (
        <Card>
          <CardHeader title="Overview" />
          <CardBody className="space-y-4">
            <Section title="Description" content={job.description} />
            <Section title="Responsibilities" content={job.responsibilities} />
            <Section title="Requirements" content={job.requirements} />
            <Section title="Preferred requirements" content={job.preferred_requirements} />
            {!job.description && !job.responsibilities && !job.requirements && !job.preferred_requirements && (
              <EmptyState title="No details added yet" description="Click Edit to add a description and requirements." />
            )}
          </CardBody>
        </Card>
      )}

      {tab === 'pipeline' && <KanbanBoard jobId={job.id} />}

      {tab === 'recommendations' && <RecommendationsTab jobId={job.id} />}

      <JobFormModal open={editOpen} onClose={() => setEditOpen(false)} job={job} />
    </div>
  )
}
