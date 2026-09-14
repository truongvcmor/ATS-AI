import type { DragEvent } from 'react'
import { useCallback, useRef, useState } from 'react'
import { useQueries } from '@tanstack/react-query'
import { Dialog } from '../../components/ui/Dialog'
import { Button } from '../../components/ui/Button'
import {
  processingJobQueryOptions,
  useProcessingJob,
  useRetryProcessing,
  useUploadCvs,
} from '../../services/hooks/useCandidates'
import type { ProcessingStatus } from '../../types'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'

const ACCEPTED_EXT = ['.pdf', '.docx', '.png', '.jpg', '.jpeg']

const STEP_ORDER: ProcessingStatus[] = ['UPLOADING', 'PARSING', 'PROCESSING', 'INDEXING', 'COMPLETED']

function StatusPill({ status }: { status: ProcessingStatus }) {
  const stepIndex = STEP_ORDER.indexOf(status)
  const isFailed = status === 'FAILED'
  const isDone = status === 'COMPLETED'

  return (
    <div className="flex items-center gap-2">
      {!isFailed && !isDone && (
        <svg className="h-3.5 w-3.5 animate-spin text-brand-500" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
        </svg>
      )}
      {isDone && (
        <svg className="h-3.5 w-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      )}
      {isFailed && (
        <svg className="h-3.5 w-3.5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      )}
      <span
        className={`text-xs font-medium ${
          isFailed ? 'text-red-600' : isDone ? 'text-emerald-600' : 'text-slate-500'
        }`}
      >
        {stepIndex >= 0
          ? { UPLOADING: 'Uploading', PARSING: 'Parsing', PROCESSING: 'Processing', INDEXING: 'Indexing', COMPLETED: 'Completed' }[
              status as 'UPLOADING' | 'PARSING' | 'PROCESSING' | 'INDEXING' | 'COMPLETED'
            ]
          : 'Failed'}
      </span>
    </div>
  )
}

function ProcessingRow({ jobId, fileName }: { jobId: string; fileName: string }) {
  const { data } = useProcessingJob(jobId, true)
  const retry = useRetryProcessing()
  const toast = useToast()

  const status = data?.status ?? 'UPLOADING'

  async function onRetry() {
    try {
      await retry.mutateAsync(jobId)
      toast.success(`Retrying ${fileName}`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Retry failed')
    }
  }

  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-2.5 last:border-0">
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium text-slate-700">{fileName}</div>
        {status === 'FAILED' && data?.error_message && (
          <div className="truncate text-xs text-red-500">{data.error_message}</div>
        )}
        {data?.duplicate_of_candidate_id && (
          <div className="truncate text-xs text-amber-600">Possible duplicate — merged with existing candidate</div>
        )}
      </div>
      <StatusPill status={status} />
      {status === 'FAILED' && (
        <Button size="sm" variant="secondary" onClick={onRetry} loading={retry.isPending}>
          Retry
        </Button>
      )}
    </div>
  )
}

export function UploadCvModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [pending, setPending] = useState<{ jobId: string; fileName: string }[]>([])
  const [dragActive, setDragActive] = useState(false)
  const upload = useUploadCvs()
  const toast = useToast()
  const inputRef = useRef<HTMLInputElement>(null)

  const jobIds = pending.map((p) => p.jobId)
  const jobQueries = useQueries({
    queries: jobIds.map((id) => processingJobQueryOptions(id, true)),
  })
  const completedCount = jobQueries.filter((q) => q.data?.status === 'COMPLETED').length
  const failedCount = jobQueries.filter((q) => q.data?.status === 'FAILED').length

  const handleFiles = useCallback(
    async (fileList: FileList | null) => {
      if (!fileList || fileList.length === 0) return
      const files = Array.from(fileList).filter((f) =>
        ACCEPTED_EXT.some((ext) => f.name.toLowerCase().endsWith(ext)),
      )
      const rejected = fileList.length - files.length
      if (rejected > 0) {
        toast.error(`${rejected} file(s) skipped — only .pdf, .docx, .png, and .jpg are accepted`)
      }
      if (files.length === 0) return
      try {
        const res = await upload.mutateAsync(files)
        setPending((prev) => [...prev, ...res.jobs.map((j) => ({ jobId: j.id, fileName: j.file_name }))])
      } catch (err) {
        toast.error(err instanceof ApiError ? err.message : 'Upload failed')
      }
    },
    [upload, toast],
  )

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragActive(false)
    handleFiles(e.dataTransfer.files)
  }

  function reset() {
    setPending([])
    onClose()
  }

  return (
    <Dialog open={open} onClose={reset} title="Upload CVs" size="lg">
      <div className="space-y-4">
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragActive(true)
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors ${
            dragActive ? 'border-brand-500 bg-brand-50' : 'border-slate-300 hover:border-slate-400'
          }`}
        >
          <svg className="mb-2 h-8 w-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M12 12v9m0-9l-3 3m3-3l3 3"
            />
          </svg>
          <p className="text-sm font-medium text-slate-700">Drag & drop CVs here, or click to browse</p>
          <p className="mt-1 text-xs text-slate-400">
            Accepts .pdf, .docx, .png, .jpg — multiple files supported. Scanned/photographed CVs are read
            automatically via OCR.
          </p>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.png,.jpg,.jpeg"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>

        {pending.length > 0 && (
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-sm font-medium text-slate-700">
                {pending.length} uploaded — {completedCount} completed, {failedCount} failed
              </span>
            </div>
            <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-200">
              {pending.map((p) => (
                <ProcessingRow key={p.jobId} jobId={p.jobId} fileName={p.fileName} />
              ))}
            </div>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={reset}>
            {pending.length > 0 ? 'Done' : 'Cancel'}
          </Button>
        </div>
      </div>
    </Dialog>
  )
}
