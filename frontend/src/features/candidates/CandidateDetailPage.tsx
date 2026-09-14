import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  useCandidate,
  useCandidateHistory,
  useCandidateScreening,
  useAddLabel,
  useDeleteCandidate,
  useRemoveLabel,
  useUpdateCandidate,
} from '../../services/hooks/useCandidates'
import { useAssessments } from '../../services/hooks/useAssessments'
import { useLabels } from '../../services/hooks/useLabels'
import { Tabs } from '../../components/ui/Tabs'
import { Card, CardBody, CardHeader } from '../../components/ui/Card'
import { AiScoreBadge, ColorBadge, RecommendationBadge, StatusBadge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Select } from '../../components/ui/Input'
import { Dropdown, DropdownItem } from '../../components/ui/Dropdown'
import { EmptyState } from '../../components/ui/EmptyState'
import { Skeleton, SkeletonCard } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/Toast'
import { ApiError, downloadFile } from '../../services/api'
import { AssessmentForm } from '../assessments/AssessmentForm'
import { MergeCandidatesDialog } from './MergeCandidatesDialog'
import type { CandidateStatus } from '../../types'

const STATUS_OPTIONS: CandidateStatus[] = ['NEW', 'ACTIVE', 'IN_PROCESS', 'HIRED', 'ARCHIVED']

const TABS = [
  { key: 'profile', label: 'Profile' },
  { key: 'experience', label: 'Experience' },
  { key: 'education', label: 'Education' },
  { key: 'skills', label: 'Skills' },
  { key: 'certifications', label: 'Certifications' },
  { key: 'languages', label: 'Languages' },
  { key: 'projects', label: 'Projects' },
  { key: 'screening', label: 'Screening Results' },
  { key: 'history', label: 'History' },
  { key: 'assessments', label: 'Assessments' },
  { key: 'cvs', label: 'CVs' },
]

function fmtDate(d: string | null | undefined) {
  if (!d) return 'Present'
  return new Date(d).toLocaleDateString(undefined, { year: 'numeric', month: 'short' })
}

function fmtDateTime(d: string) {
  return new Date(d).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const [tab, setTab] = useState('profile')
  const [assessmentOpen, setAssessmentOpen] = useState(false)
  const [mergeOpen, setMergeOpen] = useState(false)

  const { data: candidate, isLoading, isError } = useCandidate(id)
  const { data: history } = useCandidateHistory(id)
  const { data: screenings } = useCandidateScreening(id)
  const { data: assessments } = useAssessments(id)
  const { data: allLabels } = useLabels()
  const updateCandidate = useUpdateCandidate(id ?? '')
  const deleteCandidate = useDeleteCandidate()
  const addLabel = useAddLabel(id ?? '')
  const removeLabel = useRemoveLabel(id ?? '')

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 rounded-lg" />
        <SkeletonCard />
      </div>
    )
  }

  if (isError || !candidate) {
    return <EmptyState title="Candidate not found" description="This candidate may have been deleted." />
  }

  async function onStatusChange(status: CandidateStatus) {
    try {
      await updateCandidate.mutateAsync({ status })
      toast.success('Status updated')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to update status')
    }
  }

  async function onDelete() {
    if (!id) return
    if (!confirm(`Delete ${candidate!.full_name}? This cannot be undone.`)) return
    try {
      await deleteCandidate.mutateAsync(id)
      toast.success('Candidate deleted')
      navigate('/talent-pool')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to delete candidate')
    }
  }

  async function onToggleLabel(labelId: string, active: boolean) {
    try {
      if (active) {
        await removeLabel.mutateAsync(labelId)
      } else {
        await addLabel.mutateAsync(labelId)
      }
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to update labels')
    }
  }

  async function onDownloadCv(cvId: string, fileName: string) {
    try {
      await downloadFile(`/candidates/${candidate!.id}/cvs/${cvId}/download`, fileName)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Download failed')
    }
  }

  const activeLabelIds = new Set(candidate.labels.map((l) => l.id))

  return (
    <div className="space-y-5">
      <Link to="/talent-pool" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        Back to Talent Pool
      </Link>

      <Card className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-brand-100 text-lg font-semibold text-brand-700">
              {candidate.full_name.slice(0, 1).toUpperCase()}
            </div>
            <div>
              <h1 className="text-xl font-semibold text-slate-900">{candidate.full_name}</h1>
              <p className="text-sm text-slate-500">
                {candidate.current_title ?? 'No title'} {candidate.location ? `· ${candidate.location}` : ''}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <StatusBadge status={candidate.status} />
                <AiScoreBadge score={candidate.ai_score} />
                {candidate.labels.map((l) => (
                  <ColorBadge key={l.id} name={l.name} color={l.color} />
                ))}
                <Dropdown
                  trigger={
                    <button className="rounded-full border border-dashed border-slate-300 px-2 py-0.5 text-xs text-slate-500 hover:border-slate-400">
                      + Label
                    </button>
                  }
                >
                  {() => (
                    <>
                      {(allLabels ?? []).length === 0 && (
                        <div className="px-3 py-1.5 text-xs text-slate-400">No labels yet</div>
                      )}
                      {(allLabels ?? []).map((l) => {
                        const active = activeLabelIds.has(l.id)
                        return (
                          <DropdownItem key={l.id} onClick={() => onToggleLabel(l.id, active)}>
                            <span className="flex items-center gap-2">
                              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: l.color }} />
                              {l.name}
                              {active && <span className="ml-auto text-brand-600">✓</span>}
                            </span>
                          </DropdownItem>
                        )
                      })}
                    </>
                  )}
                </Dropdown>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Select
              value={candidate.status}
              onChange={(e) => onStatusChange(e.target.value as CandidateStatus)}
              className="!w-auto"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s.replace('_', ' ')}
                </option>
              ))}
            </Select>
            <Button variant="secondary" onClick={() => setMergeOpen(true)}>
              Merge duplicate
            </Button>
            <Button onClick={() => setAssessmentOpen(true)}>+ Add Assessment</Button>
            <Dropdown
              align="right"
              trigger={
                <button className="rounded-lg border border-slate-300 p-2 text-slate-500 hover:bg-slate-50">
                  <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 6a2 2 0 100-4 2 2 0 000 4zm0 8a2 2 0 100-4 2 2 0 000 4zm0 8a2 2 0 100-4 2 2 0 000 4z" />
                  </svg>
                </button>
              }
            >
              {() => (
                <DropdownItem className="text-red-600" onClick={onDelete}>
                  Delete candidate
                </DropdownItem>
              )}
            </Dropdown>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 border-t border-slate-100 pt-4 text-sm sm:grid-cols-4">
          <div>
            <div className="text-xs text-slate-400">Email</div>
            <div className="text-slate-700">{candidate.email ?? '—'}</div>
          </div>
          <div>
            <div className="text-xs text-slate-400">Phone</div>
            <div className="text-slate-700">{candidate.phone ?? '—'}</div>
          </div>
          <div>
            <div className="text-xs text-slate-400">Experience</div>
            <div className="text-slate-700">
              {candidate.years_of_experience !== null ? `${candidate.years_of_experience} yrs` : '—'}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-400">Source</div>
            <div className="text-slate-700">{candidate.source}</div>
          </div>
        </div>
      </Card>

      <Tabs tabs={TABS} active={tab} onChange={setTab} />

      <div>
        {tab === 'profile' && (
          <Card>
            <CardHeader title="Summary" />
            <CardBody>
              <p className="whitespace-pre-line text-sm text-slate-700">
                {candidate.summary || 'No summary available.'}
              </p>
            </CardBody>
          </Card>
        )}

        {tab === 'experience' && (
          <Card>
            <CardHeader title="Experience" />
            <CardBody>
              {candidate.experiences.length === 0 ? (
                <EmptyState title="No experience recorded" />
              ) : (
                <ol className="space-y-4 border-l border-slate-200 pl-4">
                  {candidate.experiences.map((exp) => (
                    <li key={exp.id} className="relative">
                      <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-brand-500" />
                      <div className="text-sm font-semibold text-slate-800">{exp.position}</div>
                      <div className="text-sm text-slate-500">{exp.company}</div>
                      <div className="text-xs text-slate-400">
                        {fmtDate(exp.start_date)} – {exp.is_current ? 'Present' : fmtDate(exp.end_date)}
                      </div>
                      {exp.description && <p className="mt-1 text-sm text-slate-600">{exp.description}</p>}
                    </li>
                  ))}
                </ol>
              )}
            </CardBody>
          </Card>
        )}

        {tab === 'education' && (
          <Card>
            <CardHeader title="Education" />
            <CardBody>
              {candidate.educations.length === 0 ? (
                <EmptyState title="No education recorded" />
              ) : (
                <ul className="space-y-3">
                  {candidate.educations.map((ed) => (
                    <li key={ed.id} className="text-sm">
                      <div className="font-semibold text-slate-800">{ed.school}</div>
                      <div className="text-slate-500">
                        {[ed.degree, ed.major].filter(Boolean).join(', ') || '—'}
                      </div>
                      <div className="text-xs text-slate-400">
                        {fmtDate(ed.start_date)} – {fmtDate(ed.end_date)}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        )}

        {tab === 'skills' && (
          <Card>
            <CardHeader title="Skills" />
            <CardBody>
              {candidate.skills.length === 0 ? (
                <EmptyState title="No skills extracted" />
              ) : (
                <div className="flex flex-wrap gap-2">
                  {candidate.skills.map((s) => (
                    <span key={s} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        )}

        {tab === 'certifications' && (
          <Card>
            <CardHeader title="Certifications" />
            <CardBody>
              {candidate.certifications.length === 0 ? (
                <EmptyState title="No certifications recorded" />
              ) : (
                <ul className="space-y-2">
                  {candidate.certifications.map((c) => (
                    <li key={c.id} className="text-sm">
                      <span className="font-medium text-slate-800">{c.name}</span>
                      {c.issuer && <span className="text-slate-500"> — {c.issuer}</span>}
                      {c.issue_date && <span className="text-xs text-slate-400"> ({fmtDate(c.issue_date)})</span>}
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        )}

        {tab === 'languages' && (
          <Card>
            <CardHeader title="Languages" />
            <CardBody>
              {candidate.languages.length === 0 ? (
                <EmptyState title="No languages recorded" />
              ) : (
                <div className="flex flex-wrap gap-2">
                  {candidate.languages.map((l) => (
                    <span key={l.id} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700">
                      {l.name}
                      {l.proficiency ? ` · ${l.proficiency}` : ''}
                    </span>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        )}

        {tab === 'projects' && (
          <Card>
            <CardHeader title="Projects" />
            <CardBody>
              {candidate.projects.length === 0 ? (
                <EmptyState title="No projects recorded" />
              ) : (
                <ul className="space-y-3">
                  {candidate.projects.map((p) => (
                    <li key={p.id} className="text-sm">
                      <div className="font-semibold text-slate-800">{p.name}</div>
                      {p.description && <p className="text-slate-600">{p.description}</p>}
                      {p.technologies && <p className="text-xs text-slate-400">{p.technologies}</p>}
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        )}

        {tab === 'screening' && (
          <Card>
            <CardHeader
              title="Screening Results"
              subtitle="AI-generated recommendation — recruiter makes the final decision"
            />
            <CardBody>
              {!screenings || screenings.length === 0 ? (
                <EmptyState title="No screening results yet" description="Run 'Find Candidates' or 'Screen' from a job to generate one." />
              ) : (
                <div className="space-y-4">
                  {screenings.map((s) => (
                    <div key={s.id} className="rounded-lg border border-slate-200 p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <RecommendationBadge recommendation={s.recommendation} />
                          <span className="text-sm font-semibold text-slate-800">{Math.round(s.overall_score)}/100</span>
                        </div>
                        <span className="text-xs text-slate-400">{fmtDateTime(s.created_at)}</span>
                      </div>
                      {s.reasoning && <p className="mt-2 text-sm text-slate-600">{s.reasoning}</p>}
                      <div className="mt-3 grid gap-3 sm:grid-cols-2">
                        <div>
                          <div className="text-xs font-medium text-slate-500">Matched requirements</div>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {s.matched_requirements.map((r) => (
                              <span key={r} className="rounded bg-emerald-50 px-1.5 py-0.5 text-xs text-emerald-700">
                                {r}
                              </span>
                            ))}
                            {s.matched_requirements.length === 0 && <span className="text-xs text-slate-400">None</span>}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs font-medium text-slate-500">Missing requirements</div>
                          <div className="mt-1 flex flex-wrap gap-1">
                            {s.missing_requirements.map((r) => (
                              <span key={r} className="rounded bg-red-50 px-1.5 py-0.5 text-xs text-red-700">
                                {r}
                              </span>
                            ))}
                            {s.missing_requirements.length === 0 && <span className="text-xs text-slate-400">None</span>}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        )}

        {tab === 'history' && (
          <Card>
            <CardHeader title="History" subtitle="Full activity timeline for this candidate" />
            <CardBody>
              {!history || history.length === 0 ? (
                <EmptyState title="No activity yet" />
              ) : (
                <ol className="space-y-4 border-l border-slate-200 pl-4">
                  {history.map((h) => (
                    <li key={h.id} className="relative">
                      <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-slate-400" />
                      <div className="text-sm text-slate-700">{h.description}</div>
                      <div className="text-xs text-slate-400">{fmtDateTime(h.created_at)}</div>
                    </li>
                  ))}
                </ol>
              )}
            </CardBody>
          </Card>
        )}

        {tab === 'assessments' && (
          <Card>
            <CardHeader
              title="Assessments"
              subtitle="Interviewer feedback and hiring recommendations"
              action={<Button size="sm" onClick={() => setAssessmentOpen(true)}>+ Add</Button>}
            />
            <CardBody>
              {!assessments || assessments.length === 0 ? (
                <EmptyState title="No assessments yet" description="Add feedback after an interview." />
              ) : (
                <div className="space-y-4">
                  {assessments.map((a) => (
                    <div key={a.id} className="rounded-lg border border-slate-200 p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-sm font-semibold text-slate-800">{a.interview_type}</span>
                          <span className="text-sm text-slate-400"> · {a.interviewer}</span>
                        </div>
                        <RecommendationBadge recommendation={a.recommendation} />
                      </div>
                      {a.score !== null && (
                        <div className="mt-1 text-xs text-slate-500">Score: {a.score}/10</div>
                      )}
                      {a.strengths && <p className="mt-2 text-sm text-slate-600"><strong>Strengths:</strong> {a.strengths}</p>}
                      {a.weaknesses && <p className="mt-1 text-sm text-slate-600"><strong>Weaknesses:</strong> {a.weaknesses}</p>}
                      {a.comments && <p className="mt-1 text-sm text-slate-600">{a.comments}</p>}
                      <div className="mt-2 text-xs text-slate-400">{fmtDateTime(a.created_at)}</div>
                    </div>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>
        )}

        {tab === 'cvs' && (
          <Card>
            <CardHeader title="CVs" />
            <CardBody>
              {candidate.cvs.length === 0 ? (
                <EmptyState title="No CVs uploaded" />
              ) : (
                <ul className="divide-y divide-slate-100">
                  {candidate.cvs.map((cv) => (
                    <li key={cv.id} className="flex items-center justify-between py-2.5">
                      <div>
                        <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                          {cv.file_name}
                          {cv.is_primary && <span className="text-xs text-brand-600">(primary)</span>}
                          {cv.extraction_method === 'ocr' && <ColorBadge name="Scanned · OCR" color="#a855f7" />}
                        </div>
                        <div className="text-xs text-slate-400">{fmtDateTime(cv.uploaded_at)}</div>
                      </div>
                      <Button size="sm" variant="secondary" onClick={() => onDownloadCv(cv.id, cv.file_name)}>
                        Download
                      </Button>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        )}
      </div>

      <AssessmentForm open={assessmentOpen} onClose={() => setAssessmentOpen(false)} candidateId={candidate.id} />
      <MergeCandidatesDialog
        open={mergeOpen}
        onClose={() => setMergeOpen(false)}
        targetId={candidate.id}
        targetName={candidate.full_name}
      />
    </div>
  )
}
