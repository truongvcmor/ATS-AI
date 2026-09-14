import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCandidates } from '../../services/hooks/useCandidates'
import { useLabels } from '../../services/hooks/useLabels'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/ui/Input'
import { AiScoreBadge, ColorBadge, StatusBadge } from '../../components/ui/Badge'
import { Table, Tbody, Td, Th, Thead, Tr } from '../../components/ui/Table'
import { SkeletonTable } from '../../components/ui/Skeleton'
import { EmptyState } from '../../components/ui/EmptyState'
import { UploadCvModal } from '../candidates/UploadCvModal'
import type { SortBy } from '../../types'

const SORT_OPTIONS: { value: SortBy; label: string }[] = [
  { value: 'relevance', label: 'Relevance' },
  { value: 'ai_score', label: 'AI Score' },
  { value: 'experience', label: 'Experience' },
  { value: 'recently_added', label: 'Recently added' },
  { value: 'recently_updated', label: 'Recently updated' },
]

function timeAgo(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}d ago`
  return new Date(iso).toLocaleDateString()
}

export function TalentPoolPage() {
  const navigate = useNavigate()
  const { data: labels } = useLabels()

  const [q, setQ] = useState('')
  const [semantic, setSemantic] = useState(false)
  const [skillsInput, setSkillsInput] = useState('')
  const [minExperience, setMinExperience] = useState('')
  const [location, setLocation] = useState('')
  const [labelFilter, setLabelFilter] = useState('')
  const [minAiScore, setMinAiScore] = useState('')
  const [sortBy, setSortBy] = useState<SortBy>('recently_added')
  const [page, setPage] = useState(1)
  const [uploadOpen, setUploadOpen] = useState(false)
  const pageSize = 20

  const skills = useMemo(
    () =>
      skillsInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
    [skillsInput],
  )

  const { data, isLoading, isFetching, isError } = useCandidates({
    q: q || undefined,
    semantic: semantic || undefined,
    skills: skills.length ? skills : undefined,
    min_experience: minExperience ? Number(minExperience) : undefined,
    locations: location ? [location] : undefined,
    labels: labelFilter ? [labelFilter] : undefined,
    min_ai_score: minAiScore ? Number(minAiScore) : undefined,
    sort_by: sortBy,
    page,
    page_size: pageSize,
  })

  const hasFilters = Boolean(q || skills.length || minExperience || location || labelFilter || minAiScore)
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  function resetFilters() {
    setQ('')
    setSkillsInput('')
    setMinExperience('')
    setLocation('')
    setLabelFilter('')
    setMinAiScore('')
    setPage(1)
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">Talent Pool</h1>
          <p className="text-sm text-slate-500">{total} candidate{total === 1 ? '' : 's'} in your reusable pool</p>
        </div>
        <Button onClick={() => setUploadOpen(true)}>+ Upload CV</Button>
      </div>

      <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
        <div>
          <div className="flex gap-2">
            <div className="flex-1">
              <Input
                value={q}
                onChange={(e) => {
                  setQ(e.target.value)
                  setPage(1)
                }}
                placeholder='Search: "Python AND FastAPI", "Python OR Java", "-PHP", or natural language with semantic search'
              />
            </div>
            <label className="flex items-center gap-1.5 whitespace-nowrap rounded-lg border border-slate-300 px-3 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={semantic}
                onChange={(e) => {
                  setSemantic(e.target.checked)
                  setPage(1)
                }}
                className="rounded border-slate-300 text-brand-600 focus:ring-brand-500"
              />
              Semantic
            </label>
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Boolean operators supported: <code className="rounded bg-slate-100 px-1">AND</code>,{' '}
            <code className="rounded bg-slate-100 px-1">OR</code>,{' '}
            <code className="rounded bg-slate-100 px-1">-exclude</code>. Toggle Semantic for natural-language search.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          <Input
            placeholder="Skills (comma sep.)"
            value={skillsInput}
            onChange={(e) => {
              setSkillsInput(e.target.value)
              setPage(1)
            }}
          />
          <Input
            type="number"
            min={0}
            placeholder="Min experience"
            value={minExperience}
            onChange={(e) => {
              setMinExperience(e.target.value)
              setPage(1)
            }}
          />
          <Input
            placeholder="Location"
            value={location}
            onChange={(e) => {
              setLocation(e.target.value)
              setPage(1)
            }}
          />
          <Select
            value={labelFilter}
            onChange={(e) => {
              setLabelFilter(e.target.value)
              setPage(1)
            }}
          >
            <option value="">All labels</option>
            {labels?.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name}
              </option>
            ))}
          </Select>
          <Input
            type="number"
            min={0}
            max={100}
            placeholder="Min AI score"
            value={minAiScore}
            onChange={(e) => {
              setMinAiScore(e.target.value)
              setPage(1)
            }}
          />
          <Select value={sortBy} onChange={(e) => setSortBy(e.target.value as SortBy)}>
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                Sort: {o.label}
              </option>
            ))}
          </Select>
        </div>

        {hasFilters && (
          <div className="flex justify-end">
            <button onClick={resetFilters} className="text-xs font-medium text-slate-500 hover:text-slate-700">
              Clear filters
            </button>
          </div>
        )}
      </div>

      {isLoading ? (
        <SkeletonTable rows={8} />
      ) : isError ? (
        <EmptyState title="Failed to load candidates" description="Please try again." />
      ) : !data || data.items.length === 0 ? (
        hasFilters ? (
          <EmptyState title="No candidates match these filters" description="Try broadening your search or filters." />
        ) : (
          <EmptyState
            title="No candidates yet"
            description="Upload your first CV to start building your talent pool."
            action={<Button onClick={() => setUploadOpen(true)}>+ Upload CV</Button>}
          />
        )
      ) : (
        <>
          <div className={isFetching ? 'opacity-60 transition-opacity' : ''}>
            <Table>
              <Thead>
                <tr>
                  <Th>Name</Th>
                  <Th>Title</Th>
                  <Th>Experience</Th>
                  <Th>Skills</Th>
                  <Th>Location</Th>
                  <Th>AI Score</Th>
                  <Th>Labels</Th>
                  <Th>Last Activity</Th>
                  <Th>Status</Th>
                </tr>
              </Thead>
              <Tbody>
                {data.items.map((c) => (
                  <Tr key={c.id} onClick={() => navigate(`/candidates/${c.id}`)}>
                    <Td className="font-medium text-slate-900">{c.full_name}</Td>
                    <Td>{c.current_title ?? '—'}</Td>
                    <Td>{c.years_of_experience !== null ? `${c.years_of_experience} yrs` : '—'}</Td>
                    <Td className="max-w-[220px]">
                      <div className="flex flex-wrap gap-1">
                        {c.skills.slice(0, 3).map((s) => (
                          <span key={s} className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
                            {s}
                          </span>
                        ))}
                        {c.skills.length > 3 && (
                          <span className="text-xs text-slate-400">+{c.skills.length - 3}</span>
                        )}
                      </div>
                    </Td>
                    <Td>{c.location ?? '—'}</Td>
                    <Td>
                      <AiScoreBadge score={c.ai_score} />
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-1">
                        {c.labels.map((l) => (
                          <ColorBadge key={l.id} name={l.name} color={l.color} />
                        ))}
                      </div>
                    </Td>
                    <Td className="whitespace-nowrap text-xs text-slate-400">{timeAgo(c.updated_at)}</Td>
                    <Td>
                      <StatusBadge status={c.status} />
                    </Td>
                  </Tr>
                ))}
              </Tbody>
            </Table>
          </div>

          <div className="flex items-center justify-between text-sm text-slate-500">
            <span>
              Page {data.page} of {totalPages} ({total} total)
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}

      <UploadCvModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </div>
  )
}
