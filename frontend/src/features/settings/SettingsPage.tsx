import { useEffect, useState } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { Card, CardBody, CardHeader } from '../../components/ui/Card'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Input, Select } from '../../components/ui/Input'
import { SkeletonCard } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/Toast'
import { ApiError } from '../../services/api'
import { useAISettings, useTestAIProvider, useUpdateAISettings } from '../../services/hooks/useSettings'
import type { AISettingsUpdate, LlmProviderChoice, OcrProviderChoice, SettingsSource } from '../../types'

const EMBEDDING_DIMS: Record<string, number> = {
  'text-embedding-3-small': 1536,
  'text-embedding-3-large': 3072,
  'text-embedding-ada-002': 1536,
  'text-embedding-004': 768,
}

function SourceBadge({ source }: { source: SettingsSource }) {
  if (source === 'database') return <Badge tone="green">Custom (saved here)</Badge>
  if (source === 'env') return <Badge tone="blue">From .env</Badge>
  return <Badge tone="slate">Not configured</Badge>
}

function ProviderKeyField({
  title,
  provider,
  configured,
  masked,
  source,
  modelValue,
  onModelChange,
  keysValue,
  onKeysChange,
  onClear,
}: {
  title: string
  provider: 'openai' | 'gemini'
  configured: boolean
  masked: string[]
  source: SettingsSource
  modelValue: string
  onModelChange: (v: string) => void
  keysValue: string
  onKeysChange: (v: string) => void
  onClear: () => void
}) {
  const test = useTestAIProvider()
  const toast = useToast()
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null)

  async function onTest() {
    setResult(null)
    try {
      const res = await test.mutateAsync({ provider, api_key: keysValue.trim() || undefined, model: modelValue || undefined })
      setResult(res)
      if (!res.ok) toast.error(`${title}: ${res.message}`)
      else toast.success(`${title}: connection OK (${res.latency_ms}ms)`)
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Test failed'
      setResult({ ok: false, message })
      toast.error(message)
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-200 p-4">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-slate-800">{title}</h4>
        <SourceBadge source={source} />
      </div>

      {configured && masked.length > 0 && (
        <p className="text-xs text-slate-500">
          Active key(s): <span className="font-mono">{masked.join(', ')}</span>
        </p>
      )}

      <Input
        label="Model"
        value={modelValue}
        onChange={(e) => onModelChange(e.target.value)}
        placeholder={provider === 'openai' ? 'gpt-4o-mini' : 'gemini-1.5-flash'}
      />

      <Input
        label="API key(s)"
        type="password"
        autoComplete="off"
        value={keysValue}
        onChange={(e) => onKeysChange(e.target.value)}
        placeholder={configured ? 'Leave blank to keep the current key' : 'sk-... (comma-separate for multiple)'}
        hint="Multiple keys rotate automatically with failover if one hits a rate limit or error."
      />

      <div className="flex items-center gap-2">
        <Button type="button" size="sm" variant="secondary" onClick={onTest} loading={test.isPending}>
          Test connection
        </Button>
        {configured && (
          <Button type="button" size="sm" variant="ghost" className="text-red-600 hover:bg-red-50" onClick={onClear}>
            Clear stored key
          </Button>
        )}
      </div>

      {result && (
        <p className={`text-xs ${result.ok ? 'text-emerald-600' : 'text-red-600'}`}>
          {result.ok ? '✓' : '✗'} {result.message}
        </p>
      )}
    </div>
  )
}

function AISettingsCard() {
  const { data, isLoading, error } = useAISettings()
  const update = useUpdateAISettings()
  const toast = useToast()

  const [llmProvider, setLlmProvider] = useState<LlmProviderChoice>('mock')
  const [embeddingProvider, setEmbeddingProvider] = useState<LlmProviderChoice>('mock')
  const [ocrProvider, setOcrProvider] = useState<OcrProviderChoice>('auto')
  const [openaiModel, setOpenaiModel] = useState('')
  const [geminiModel, setGeminiModel] = useState('')
  const [embeddingModel, setEmbeddingModel] = useState('')
  const [geminiEmbeddingModel, setGeminiEmbeddingModel] = useState('')
  const [openaiKeys, setOpenaiKeys] = useState('')
  const [geminiKeys, setGeminiKeys] = useState('')
  const [clearOpenai, setClearOpenai] = useState(false)
  const [clearGemini, setClearGemini] = useState(false)

  useEffect(() => {
    if (!data) return
    setLlmProvider(data.llm_provider)
    setEmbeddingProvider(data.embedding_provider)
    setOcrProvider(data.ocr_provider)
    setOpenaiModel(data.openai_model)
    setGeminiModel(data.gemini_model)
    setEmbeddingModel(data.embedding_model)
    setGeminiEmbeddingModel(data.gemini_embedding_model)
  }, [data])

  if (isLoading) return <SkeletonCard />
  if (error) return null // non-admins get a 403 here — the card simply doesn't render, see below
  if (!data) return null

  const expectedDim = EMBEDDING_DIMS[embeddingModel] ?? EMBEDDING_DIMS[geminiEmbeddingModel]
  const dimMismatch =
    embeddingProvider !== 'mock' &&
    ((embeddingProvider === 'openai' && EMBEDDING_DIMS[embeddingModel] !== data.embedding_dim) ||
      (embeddingProvider === 'gemini' && EMBEDDING_DIMS[geminiEmbeddingModel] !== data.embedding_dim) ||
      (embeddingProvider === 'auto' && expectedDim !== undefined && expectedDim !== data.embedding_dim))

  async function onSave() {
    const payload: AISettingsUpdate = {
      llm_provider: llmProvider,
      embedding_provider: embeddingProvider,
      ocr_provider: ocrProvider,
      openai_model: openaiModel,
      gemini_model: geminiModel,
      embedding_model: embeddingModel,
      gemini_embedding_model: geminiEmbeddingModel,
    }
    if (clearOpenai) payload.openai_api_keys = ''
    else if (openaiKeys.trim()) payload.openai_api_keys = openaiKeys.trim()
    if (clearGemini) payload.gemini_api_keys = ''
    else if (geminiKeys.trim()) payload.gemini_api_keys = geminiKeys.trim()

    try {
      await update.mutateAsync(payload)
      setOpenaiKeys('')
      setGeminiKeys('')
      setClearOpenai(false)
      setClearGemini(false)
      toast.success('AI settings saved — takes effect immediately, no restart needed')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Failed to save settings')
    }
  }

  return (
    <Card>
      <CardHeader
        title="AI providers"
        subtitle="Switch between OpenAI, Gemini, or the built-in free mock/rule-based engines — changes apply immediately."
      />
      <CardBody className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-3">
          <Select label="CV parsing & screening (LLM)" value={llmProvider} onChange={(e) => setLlmProvider(e.target.value as LlmProviderChoice)}>
            <option value="mock">Mock (free, offline)</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Gemini</option>
            <option value="auto">Auto (rotate all configured)</option>
          </Select>
          <Select
            label="Embeddings (semantic search)"
            value={embeddingProvider}
            onChange={(e) => setEmbeddingProvider(e.target.value as LlmProviderChoice)}
          >
            <option value="mock">Mock (free, offline)</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Gemini</option>
            <option value="auto">Auto (pick whichever is configured)</option>
          </Select>
          <Select label="CV scanning (OCR)" value={ocrProvider} onChange={(e) => setOcrProvider(e.target.value as OcrProviderChoice)}>
            <option value="auto">Auto (Tesseract, then AI vision as fallback)</option>
            <option value="tesseract">Tesseract only (free, offline)</option>
            <option value="llm_vision">AI vision only (needs a key above)</option>
          </Select>
        </div>

        {dimMismatch && (
          <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            ⚠️ This embedding model outputs a different vector size than the database column is set up for
            (currently {data.embedding_dim} dimensions). Semantic search will error until an admin runs a migration
            to resize the <code>embeddings.vector</code> column to match.
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          <ProviderKeyField
            title="OpenAI"
            provider="openai"
            configured={data.openai_configured}
            masked={data.openai_keys_masked}
            source={data.openai_source}
            modelValue={openaiModel}
            onModelChange={setOpenaiModel}
            keysValue={openaiKeys}
            onKeysChange={(v) => {
              setOpenaiKeys(v)
              setClearOpenai(false)
            }}
            onClear={() => {
              setClearOpenai(true)
              setOpenaiKeys('')
            }}
          />
          <ProviderKeyField
            title="Gemini"
            provider="gemini"
            configured={data.gemini_configured}
            masked={data.gemini_keys_masked}
            source={data.gemini_source}
            modelValue={geminiModel}
            onModelChange={setGeminiModel}
            keysValue={geminiKeys}
            onKeysChange={(v) => {
              setGeminiKeys(v)
              setClearGemini(false)
            }}
            onClear={() => {
              setClearGemini(true)
              setGeminiKeys('')
            }}
          />
        </div>

        {(clearOpenai || clearGemini) && (
          <p className="text-xs text-amber-700">
            The stored key for {[clearOpenai && 'OpenAI', clearGemini && 'Gemini'].filter(Boolean).join(' and ')} will
            be removed when you save (reverting to .env, if any).
          </p>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Embedding model (OpenAI)" value={embeddingModel} onChange={(e) => setEmbeddingModel(e.target.value)} />
          <Input
            label="Embedding model (Gemini)"
            value={geminiEmbeddingModel}
            onChange={(e) => setGeminiEmbeddingModel(e.target.value)}
          />
        </div>

        <div className="flex items-center justify-between border-t border-slate-100 pt-4">
          <p className="text-xs text-slate-400">
            {data.updated_at ? `Last changed ${new Date(data.updated_at).toLocaleString()}${data.updated_by ? ` by ${data.updated_by}` : ''}` : 'No changes saved yet — using .env defaults.'}
          </p>
          <Button onClick={onSave} loading={update.isPending}>
            Save changes
          </Button>
        </div>
      </CardBody>
    </Card>
  )
}

export function SettingsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'ADMIN'

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500">Account and workspace preferences.</p>
      </div>

      <Card>
        <CardHeader title="Your account" />
        <CardBody className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Name</span>
            <span className="font-medium text-slate-800">{user?.full_name}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Email</span>
            <span className="font-medium text-slate-800">{user?.email}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-slate-500">Role</span>
            <Badge tone="indigo">{user?.role}</Badge>
          </div>
        </CardBody>
      </Card>

      {isAdmin ? (
        <AISettingsCard />
      ) : (
        <Card>
          <CardHeader title="AI providers" subtitle="Admin access required" />
          <CardBody>
            <p className="text-sm text-slate-500">
              Ask an Admin to configure AI providers (OpenAI, Gemini, or the free built-in engines) from this page.
            </p>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardHeader title="About" subtitle="ATS AI — Talent Pool MVP" />
        <CardBody>
          <p className="text-sm text-slate-500">
            More workspace settings (notifications, integrations, team management) will land here in a future
            iteration.
          </p>
        </CardBody>
      </Card>
    </div>
  )
}
