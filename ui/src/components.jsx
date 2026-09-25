import React from 'react'
import { DECISIONS } from './words.js'

// A heading in both languages: Hindi set in the file face, English beneath it in the interface face.
export function Heading({ hi, en, level = 1, children }) {
  const H = `h${level}`
  const size = level === 1 ? 'text-[2rem] leading-tight' : level === 2 ? 'text-[1.45rem] leading-snug' : 'text-lg'
  return (
    <div className="mb-4">
      <H className={`hi ${size} text-ink`} lang="hi">{hi}</H>
      <div className={`${level === 1 ? 'text-lg' : 'text-[15px]'} text-ink-soft`}>{en}</div>
      {children}
    </div>
  )
}

export function Loading({ what = 'Loading' }) {
  return <p className="text-ink-faint py-10" role="status">{what}…</p>
}

export function Problem({ error }) {
  if (!error) return null
  const scope = error.status === 403
  return (
    <div className={`rounded-file border px-4 py-3 my-4 ${scope ? 'border-stamp/40 bg-stamp-soft' : 'border-red-ink/40 bg-red-soft'}`} role="alert">
      <p className="font-medium">{scope ? 'Outside what this posting may see' : 'This did not load'}</p>
      <p className="text-ink-soft">{error.message}</p>
    </div>
  )
}

// The decision stamp. `fresh` plays the one animation in the interface, when the officer has just stamped it.
export function Stamp({ decision, role, ts, fresh = false }) {
  const d = DECISIONS[decision]
  if (!d) return null
  return (
    <div className={`stamp-mark ${fresh ? 'fresh' : ''}`} aria-label={`Decision: ${d.en}`}>
      <span className="text-xl" lang="hi">{d.hi}</span>
      <span className="font-sans text-[13px] font-medium">{d.en}</span>
      <span className="font-sans text-[12px]">{ts ? ts.slice(0, 10) : ''}</span>
    </div>
  )
}

export function Priority({ p }) {
  const cls = p === 'high' ? 'text-ink font-semibold' : p === 'medium' ? 'text-ink-soft' : 'text-ink-faint'
  return <span className={cls}>{p === 'high' ? 'High' : p === 'medium' ? 'Medium' : 'Low'}</span>
}

export function KindMark({ kind }) {
  // left out = ochre, paid wrongly = red ink: the two colours carry meaning and nothing else uses them
  return kind === 'exclusion'
    ? <span className="tag bg-ochre-soft text-ochre">Left out</span>
    : <span className="tag bg-red-soft text-red-ink">Payment</span>
}

// A horizontal bar for a share, drawn in the ink of its meaning.
export function Bar({ value, max, tone = 'stamp', label }) {
  const pct = max ? Math.max(0, Math.min(100, (value / max) * 100)) : 0
  const colour = { stamp: 'bg-stamp', ochre: 'bg-ochre', red: 'bg-red-ink', ink: 'bg-ink-soft' }[tone]
  return (
    <div className="flex items-center gap-2" aria-label={label}>
      <div className="h-2 flex-1 rounded-sm bg-rule/60 overflow-hidden"><div className={`h-full ${colour}`} style={{ width: `${pct}%` }} /></div>
    </div>
  )
}

export function Met({ met }) {
  if (met === true) return <span className="tag bg-stamp-soft text-stamp" title="Criterion met">Met</span>
  if (met === false) return <span className="tag bg-red-soft text-red-ink" title="Criterion not met">Not met</span>
  return <span className="tag bg-ochre-soft text-ochre" title="Needs checking by an officer">Check</span>
}

export function Pager({ page, size, total, onPage }) {
  const pages = Math.max(1, Math.ceil(total / size))
  return (
    <div className="flex items-center gap-3 py-3 text-ink-soft">
      <button className="btn-quiet" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
      <span>Page {page} of {pages.toLocaleString('en-IN')}</span>
      <button className="btn-quiet" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
    </div>
  )
}

export function useLoad(fn, deps) {
  const [state, set] = React.useState({ data: null, error: null, loading: true })
  const reload = React.useCallback(() => {
    set((s) => ({ ...s, loading: true }))
    fn().then((data) => set({ data, error: null, loading: false })).catch((error) => set({ data: null, error, loading: false }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  React.useEffect(() => { reload() }, [reload])
  return { ...state, reload }
}
