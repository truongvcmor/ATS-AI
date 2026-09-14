import type { FormEvent } from 'react'
import { useState } from 'react'
import { useCreateLabel, useDeleteLabel, useLabels, useUpdateLabel } from '../../services/hooks/useLabels'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { SkeletonCard } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'
import type { Label } from '../../types'

const PRESET_COLORS = [
  '#6366f1',
  '#22c55e',
  '#f59e0b',
  '#ef4444',
  '#0ea5e9',
  '#a855f7',
  '#14b8a6',
  '#64748b',
]

function ColorPicker({ value, onChange }: { value: string; onChange: (c: string) => void }) {
  return (
    <div className="flex flex-wrap gap-2">
      {PRESET_COLORS.map((c) => (
        <button
          key={c}
          type="button"
          onClick={() => onChange(c)}
          className={`h-7 w-7 rounded-full ring-offset-2 transition ${value === c ? 'ring-2 ring-slate-900' : ''}`}
          style={{ backgroundColor: c }}
          aria-label={c}
        />
      ))}
      <input
        type="color"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-7 w-7 cursor-pointer rounded-full border border-slate-200"
        aria-label="Custom color"
      />
    </div>
  )
}

function LabelRow({ label }: { label: Label }) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(label.name)
  const [color, setColor] = useState(label.color)
  const update = useUpdateLabel()
  const del = useDeleteLabel()
  const toast = useToast()

  async function save() {
    try {
      await update.mutateAsync({ id: label.id, name, color })
      toast.success('Label updated')
      setEditing(false)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to update label')
    }
  }

  async function remove() {
    if (!confirm(`Delete label "${label.name}"? This removes it from all candidates.`)) return
    try {
      await del.mutateAsync(label.id)
      toast.success('Label deleted')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to delete label')
    }
  }

  if (editing) {
    return (
      <Card className="p-4 space-y-3">
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Label name" />
        <ColorPicker value={color} onChange={setColor} />
        <div className="flex gap-2">
          <Button size="sm" onClick={save} loading={update.isPending}>
            Save
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setEditing(false)}>
            Cancel
          </Button>
        </div>
      </Card>
    )
  }

  return (
    <Card className="flex items-center justify-between gap-4 p-4">
      <div className="flex items-center gap-3">
        <span className="h-4 w-4 rounded-full" style={{ backgroundColor: label.color }} />
        <div>
          <div className="text-sm font-medium text-slate-800">{label.name}</div>
          <div className="text-xs text-slate-500">{label.candidate_count} candidate(s)</div>
        </div>
      </div>
      <div className="flex gap-1.5">
        <Button size="sm" variant="ghost" onClick={() => setEditing(true)}>
          Rename
        </Button>
        <Button size="sm" variant="ghost" className="text-red-600 hover:bg-red-50" onClick={remove} loading={del.isPending}>
          Delete
        </Button>
      </div>
    </Card>
  )
}

export function LabelsPage() {
  const { data: labels, isLoading } = useLabels()
  const create = useCreateLabel()
  const toast = useToast()
  const [newName, setNewName] = useState('')
  const [newColor, setNewColor] = useState(PRESET_COLORS[0])

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return
    try {
      await create.mutateAsync({ name: newName.trim(), color: newColor })
      setNewName('')
      toast.success('Label created')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to create label')
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">Labels</h1>
        <p className="text-sm text-slate-500">
          Organize candidates with custom labels — apply them from any candidate profile.
        </p>
      </div>

      <Card className="p-4">
        <form onSubmit={onCreate} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <Input
              label="New label"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. AI Engineer"
            />
          </div>
          <div>
            <span className="mb-1 block text-sm font-medium text-slate-700">Color</span>
            <ColorPicker value={newColor} onChange={setNewColor} />
          </div>
          <Button type="submit" loading={create.isPending}>
            + Add label
          </Button>
        </form>
      </Card>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : !labels || labels.length === 0 ? (
        <EmptyState title="No labels yet" description="Create your first label above to start tagging candidates." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {labels.map((l) => (
            <LabelRow key={l.id} label={l} />
          ))}
        </div>
      )}
    </div>
  )
}
