import type { InputHTMLAttributes, LabelHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { forwardRef } from 'react'

interface FieldWrapProps {
  label?: string
  hint?: string
  error?: string
  required?: boolean
}

function FieldWrap({
  label,
  hint,
  error,
  required,
  children,
  htmlFor,
}: FieldWrapProps & { children: ReactNode; htmlFor?: string }) {
  if (!label && !hint && !error) return <>{children}</>
  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={htmlFor} className="block text-sm font-medium text-slate-700">
          {label}
          {required && <span className="text-red-500"> *</span>}
        </label>
      )}
      {children}
      {hint && !error && <p className="text-xs text-slate-500">{hint}</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & FieldWrapProps>(
  ({ label, hint, error, required, className = '', id, ...props }, ref) => {
    return (
      <FieldWrap label={label} hint={hint} error={error} required={required} htmlFor={id}>
        <input
          ref={ref}
          id={id}
          className={`w-full rounded-lg border px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 ${
            error ? 'border-red-400' : 'border-slate-300'
          } ${className}`}
          {...props}
        />
      </FieldWrap>
    )
  },
)
Input.displayName = 'Input'

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement> & FieldWrapProps
>(({ label, hint, error, required, className = '', id, rows = 4, ...props }, ref) => {
  return (
    <FieldWrap label={label} hint={hint} error={error} required={required} htmlFor={id}>
      <textarea
        ref={ref}
        id={id}
        rows={rows}
        className={`w-full rounded-lg border px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 ${
          error ? 'border-red-400' : 'border-slate-300'
        } ${className}`}
        {...props}
      />
    </FieldWrap>
  )
})
Textarea.displayName = 'Textarea'

export const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement> & FieldWrapProps
>(({ label, hint, error, required, className = '', id, children, ...props }, ref) => {
  return (
    <FieldWrap label={label} hint={hint} error={error} required={required} htmlFor={id}>
      <select
        ref={ref}
        id={id}
        className={`w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500/40 focus:border-brand-500 ${
          error ? 'border-red-400' : 'border-slate-300'
        } ${className}`}
        {...props}
      >
        {children}
      </select>
    </FieldWrap>
  )
})
Select.displayName = 'Select'

export function FieldLabel(props: LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className="block text-sm font-medium text-slate-700" {...props} />
}
