import { useState } from 'react'
import {
  DndContext,
  type DragEndEvent,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
} from '@dnd-kit/core'
import { useDraggable } from '@dnd-kit/core'
import { CSS } from '@dnd-kit/utilities'
import { useJobCandidates, useJobStages } from '../../services/hooks/useJobs'
import { useUpdateApplicationStage } from '../../services/hooks/useApplications'
import { AiScoreBadge } from '../../components/ui/Badge'
import { Select } from '../../components/ui/Input'
import { EmptyState } from '../../components/ui/EmptyState'
import { Skeleton } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'
import { useNavigate } from 'react-router-dom'
import type { ApplicationOut } from '../../types'

function ApplicationCard({
  application,
  stages,
  onStageChange,
}: {
  application: ApplicationOut
  stages: { id: string; name: string }[]
  onStageChange: (stageId: string) => void
}) {
  const navigate = useNavigate()
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: application.id,
  })

  const style = transform
    ? { transform: CSS.Translate.toString(transform), zIndex: isDragging ? 20 : undefined }
    : undefined

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition ${
        isDragging ? 'opacity-70 shadow-lg' : 'hover:border-brand-300'
      }`}
    >
      <div {...attributes} {...listeners} className="cursor-grab touch-none active:cursor-grabbing">
        <div className="flex items-start justify-between gap-2">
          <button
            onClick={() => navigate(`/candidates/${application.candidate_id}`)}
            className="text-left text-sm font-medium text-slate-800 hover:text-brand-700 hover:underline"
          >
            {application.candidate?.full_name ?? 'Unknown candidate'}
          </button>
          <AiScoreBadge score={application.candidate?.ai_score} />
        </div>
        {application.candidate?.current_title && (
          <p className="mt-0.5 text-xs text-slate-500">{application.candidate.current_title}</p>
        )}
        {application.candidate?.location && (
          <p className="text-xs text-slate-400">{application.candidate.location}</p>
        )}
      </div>
      <div className="mt-2" onPointerDown={(e) => e.stopPropagation()}>
        <Select
          value={application.current_stage_id}
          onChange={(e) => onStageChange(e.target.value)}
          className="!py-1 text-xs"
          aria-label="Move to stage"
        >
          {stages.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </Select>
      </div>
    </div>
  )
}

function StageColumn({
  stage,
  applications,
  stages,
  onStageChange,
}: {
  stage: { id: string; name: string; is_terminal: boolean }
  applications: ApplicationOut[]
  stages: { id: string; name: string }[]
  onStageChange: (applicationId: string, stageId: string) => void
}) {
  const { setNodeRef, isOver } = useDroppable({ id: stage.id })

  return (
    <div
      ref={setNodeRef}
      className={`flex w-64 shrink-0 flex-col rounded-lg border bg-slate-50 ${
        isOver ? 'border-brand-400 bg-brand-50/40' : 'border-slate-200'
      }`}
    >
      <div className="flex items-center justify-between border-b border-slate-200 px-3 py-2">
        <span className="text-sm font-semibold text-slate-700">{stage.name}</span>
        <span className="rounded-full bg-white px-1.5 py-0.5 text-xs text-slate-500 ring-1 ring-slate-200">
          {applications.length}
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-2 p-2">
        {applications.map((app) => (
          <ApplicationCard
            key={app.id}
            application={app}
            stages={stages}
            onStageChange={(stageId) => onStageChange(app.id, stageId)}
          />
        ))}
        {applications.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-300 px-3 py-6 text-center text-xs text-slate-400">
            No candidates
          </div>
        )}
      </div>
    </div>
  )
}

export function KanbanBoard({ jobId }: { jobId: string }) {
  const { data: stages, isLoading: stagesLoading } = useJobStages(jobId)
  const { data: applications, isLoading: appsLoading, isError } = useJobCandidates(jobId)
  const updateStage = useUpdateApplicationStage(jobId)
  const toast = useToast()
  const [activeId, setActiveId] = useState<string | null>(null)

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))

  async function moveApplication(applicationId: string, stageId: string) {
    const current = applications?.find((a) => a.id === applicationId)
    if (!current || current.current_stage_id === stageId) return
    try {
      await updateStage.mutateAsync({ applicationId, stageId })
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to move candidate')
    }
  }

  function onDragEnd(event: DragEndEvent) {
    setActiveId(null)
    const { active, over } = event
    if (!over) return
    moveApplication(String(active.id), String(over.id))
  }

  if (stagesLoading || appsLoading) {
    return (
      <div className="flex gap-3 overflow-x-auto">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-80 w-64 shrink-0 rounded-lg" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <EmptyState
        title="Couldn't load the pipeline"
        description="The backend reported an error fetching applications for this job. Please try again shortly."
      />
    )
  }

  if (!stages || stages.length === 0) {
    return <EmptyState title="No pipeline stages configured" />
  }

  const sortedStages = [...stages].sort((a, b) => a.order - b.order)
  const apps = applications ?? []

  if (apps.length === 0) {
    return (
      <EmptyState
        title="No applicants yet"
        description="Add candidates to this job from the Talent Pool or the Find Candidates tab to start the pipeline."
      />
    )
  }

  return (
    <DndContext sensors={sensors} onDragStart={(e) => setActiveId(String(e.active.id))} onDragEnd={onDragEnd}>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {sortedStages.map((stage) => (
          <StageColumn
            key={stage.id}
            stage={stage}
            applications={apps.filter((a) => a.current_stage_id === stage.id)}
            stages={sortedStages}
            onStageChange={moveApplication}
          />
        ))}
      </div>
      {activeId && <p className="mt-2 text-xs text-slate-400">Drop on a column to move the candidate, or use the dropdown on each card.</p>}
    </DndContext>
  )
}
