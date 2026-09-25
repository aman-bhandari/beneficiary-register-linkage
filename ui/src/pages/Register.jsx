import React from 'react'
import { api } from '../api.js'
import { Heading, KindMark, Loading, Pager, Priority, Problem, Stamp, useLoad } from '../components.jsx'
import { CASE_TYPES, DECISIONS, SCHEMES, rs, title } from '../words.js'

const FILTERS = [
  ['kind', 'Kind', { exclusion: 'People left out', integrity: 'Payments to check' }],
  ['type', 'Finding', Object.fromEntries(Object.entries(CASE_TYPES).map(([k, v]) => [k, v.en]))],
  ['scheme', 'Scheme', Object.fromEntries(Object.entries(SCHEMES).map(([k, v]) => [k, v.en]))],
  ['priority', 'Priority', { high: 'High', medium: 'Medium', low: 'Low' }],
  ['status', 'Status', { open: 'Not yet decided', ...Object.fromEntries(Object.entries(DECISIONS).map(([k, v]) => [k, v.en])) }],
]

export default function Register({ role, query }) {
  const [f, setF] = React.useState(() => Object.fromEntries(FILTERS.map(([k]) => [k, query.get(k) || ''])))
  const [page, setPage] = React.useState(1)
  const { data, error, loading } = useLoad(() => api.cases({ ...f, page }), [role.key, JSON.stringify(f), page])
  const set = (k, v) => { setF((s) => ({ ...s, [k]: v })); setPage(1) }

  return (
    <div>
      <Heading hi="प्रकरण पंजिका" en="Case register">
        <p className="text-ink-soft mt-2 max-w-3xl">
          Every case in your posting, most urgent first. Names stay masked until you open a case and state why you
          need to see them.
        </p>
      </Heading>

      <form className="flex flex-wrap gap-3 items-end mb-4" onSubmit={(e) => e.preventDefault()}>
        {FILTERS.map(([k, label, opts]) => (
          <label key={k} className="text-[14px] text-ink-soft">
            {label}
            <select className="field mt-1 min-w-[10rem]" value={f[k]} onChange={(e) => set(k, e.target.value)}>
              <option value="">All</option>
              {Object.entries(opts).map(([v, t]) => <option key={v} value={v}>{t}</option>)}
            </select>
          </label>
        ))}
        {Object.values(f).some(Boolean) && <button className="btn-quiet" onClick={() => { setF(Object.fromEntries(FILTERS.map(([k]) => [k, '']))); setPage(1) }}>Clear filters</button>}
      </form>

      <Problem error={error} />
      {loading && !data && <Loading />}
      {data && (
        <>
          <p className="text-ink-soft text-[15px] mb-2">
            {data.total.toLocaleString('en-IN')} cases match. {data.refused_by_scope.toLocaleString('en-IN')} cases outside your posting were not read.
          </p>
          <div className="overflow-x-auto panel">
            <table className="ledger min-w-[860px]">
              <thead>
                <tr><th>Case</th><th>Finding</th><th>Person</th><th>Where</th><th>Priority</th><th className="num">A year</th><th>Decision</th></tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r.case_id}>
                    <td className="whitespace-nowrap"><a className="text-stamp font-medium underline underline-offset-2" href={`#/case/${r.case_id}`}>{r.case_id}</a></td>
                    <td className="max-w-[22rem]"><KindMark kind={r.kind} /> <span className="ml-1">{CASE_TYPES[r.type]?.en}</span>
                      {SCHEMES[r.scheme] && <div className="text-[14px] text-ink-faint">{SCHEMES[r.scheme].en}</div>}</td>
                    <td>
                      <div className="hi" lang="hi">{r.name_hi || '—'}</div>
                      <div className="text-[14px] text-ink-soft">{r.name_en}{r.age ? `, ${Math.round(r.age)}` : ''}{r.sex ? ` ${r.sex}` : ''}</div>
                    </td>
                    <td className="text-[15px]">{title(r.panchayat)}<div className="text-[14px] text-ink-faint">{title(r.block)}</div></td>
                    <td><Priority p={r.priority} /></td>
                    <td className="num">{r.type === 'two_pensions' ? '—' : rs(r.amount_rs)}</td>
                    <td className="py-1">{r.review ? <span className="text-stamp text-[14px] font-medium">{DECISIONS[r.review.decision]?.en}</span> : <span className="text-ink-faint text-[14px]">Open</span>}</td>
                  </tr>
                ))}
                {!data.rows.length && <tr><td colSpan="7" className="py-8 text-ink-soft">No case matches these filters. Clear a filter to widen the search.</td></tr>}
              </tbody>
            </table>
          </div>
          <Pager page={page} size={data.size} total={data.total} onPage={setPage} />
        </>
      )}
    </div>
  )
}
