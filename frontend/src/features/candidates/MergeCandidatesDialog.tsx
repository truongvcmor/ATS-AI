import { useState } from 'react'
import { Dialog } from '../../components/ui/Dialog'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { useCandidates, useMergeCandidates } from '../../services/hooks/useCandidates'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'
import type { CandidateListItem } from '../../types'

export function MergeCandidatesDialog({
  open,
  onClose,
  targetId,
  targetName,
}: {
  open: boolean
  onClose: () => void
  targetId: string
  targetName: string
}) {
  const [q, setQ] = useState('')
  const [selected, setSelected] = useState<CandidateListItem | null>(null)
  const { data, isFetching } = useCandidates({ q, page: 1, page_size: 10 })
  const merge = useMergeCandidates(targetId)
  const toast = useToast()

  const candidates = (data?.items ?? []).filter((c) => c.id !== targetId)

  async function onMerge() {
    if (!selected) return
    try {
      await merge.mutateAsync(selected.id)
      toast.success(`Merged ${selected.full_name} into ${targetName}`)
      reset()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Merge failed')
    }
  }

  function reset() {
    setQ('')
    setSelected(null)
    onClose()
  }

  return (
    <Dialog open={open} onClose={reset} title="Merge duplicate candidate" size="md">
      <div className="space-y-4">
        <p className="text-sm text-slate-500">
          Search for a duplicate profile to merge into <strong>{targetName}</strong>. This combines CVs, history and
          skills; the source profile will be removed.
        </p>
        <Input
          placeholder="Search candidates by name..."
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setSelected(null)
          }}
        />
        <div className="max-h-56 overflow-y-auto rounded-lg border border-slate-200">
          {isFetching && <div className="px-3 py-3 text-sm text-slate-400">Searching...</div>}
          {!isFetching && q && candidates.length === 0 && (
            <div className="px-3 py-3 text-sm text-slate-400">No matching candidates</div>
          )}
          {!isFetching &&
            candidates.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelected(c)}
                className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-slate-50 ${
                  selected?.id === c.id ? 'bg-brand-50' : ''
                }`}
              >
                <span>
                  <span className="font-medium text-slate-800">{c.full_name}</span>
                  {c.current_title && <span className="text-slate-400"> — {c.current_title}</span>}
                </span>
                {selected?.id === c.id && <span className="text-brand-600">✓</span>}
              </button>
            ))}
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={reset}>
            Cancel
          </Button>
          <Button onClick={onMerge} disabled={!selected} loading={merge.isPending}>
            Merge into {targetName}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
