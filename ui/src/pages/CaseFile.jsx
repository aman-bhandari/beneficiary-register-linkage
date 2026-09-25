import React from 'react'
import { api } from '../api.js'
import { Heading, KindMark, Loading, Met, Priority, Problem, Stamp, useLoad } from '../components.jsx'
import { CASE_TYPES, DECISIONS, FIELD_LABELS, REGISTERS, SCHEMES, rs, title } from '../words.js'

export default function CaseFile({ role, id }) {
  const { data, error, loading, reload } = useLoad(() => api.case(id), [role.key, id])
  const [fresh, setFresh] = React.useState(false)
  if (loading && !data) return <Loading what="Opening the case" />
  if (error) return <><a href="#/cases" className="text-stamp underline">Back to the register</a><Problem error={error} /></>
  const c = data.case
  const p = data.person
  const t = CASE_TYPES[c.type] || {}

  return (
    <article>
      <a href="#/cases" className="text-stamp underline underline-offset-2 text-[15px]">Case register</a>
      <header className="mt-3 mb-8 flex flex-wrap items-start gap-x-10 gap-y-4">
        <div className="max-w-3xl">
          <div className="flex items-center gap-3 text-ink-soft text-[15px]">
            <KindMark kind={c.kind} /><span>Case {c.case_id}</span><Priority p={c.priority} />
          </div>
          <h1 className="hi text-[1.9rem] leading-tight mt-2" lang="hi">{t.hi}</h1>
          <p className="text-xl text-ink mt-1">{c.title}</p>
          <p className="text-ink-soft mt-2">
            <span className="hi text-lg text-ink" lang="hi">{p.name_hi || p.name_en}</span>
            {p.name_hi && p.name_en ? <span> ({p.name_en})</span> : null}
            {p.age ? `, about ${Math.round(p.age)} years` : ''}{p.sex ? `, ${p.sex === 'F' ? 'woman' : 'man'}` : ''}.
            {' '}{title(p.panchayat)}, {title(p.block)} block, {p.district}.
          </p>
        </div>
        <div className="ml-auto text-right">
          {c.type !== 'two_pensions' && <>
            <div className="hi text-3xl text-ink">{rs(c.amount_rs)}</div>
            <div className="text-[14px] text-ink-soft">{c.kind === 'exclusion' ? 'owed a year if eligible' : c.type === 'paid_after_death' ? 'paid since the death' : 'paid a year'}</div>
          </>}
          {data.review && <div className="mt-3"><Stamp {...data.review} fresh={fresh} /></div>}
        </div>
      </header>

      <div className="grid xl:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] gap-8">
        {/* left: the noting sheet */}
        <section aria-labelledby="noting">
          <Heading level={2} hi="टिप्पणी" en="Why this case was raised" />
          <ol className="space-y-4" id="noting">
            {c.trace.map((tr, i) => (
              <li key={i} className="panel p-4">
                <div className="flex items-start justify-between gap-3">
                  <p className="font-medium">{tr.criterion}</p><Met met={tr.met} />
                </div>
                <p className="mt-1 text-ink-soft">{tr.evidence}</p>
                {tr.quote && (
                  <blockquote className="mt-3 border-l-[3px] border-stamp/60 pl-3">
                    <p className="hi text-[1.05rem] leading-relaxed" lang="hi">{tr.quote}</p>
                    {tr.source && <a className="text-[14px] text-stamp underline underline-offset-2 break-all" href={tr.source} target="_blank" rel="noreferrer">{tr.source.replace('https://', '')}</a>}
                  </blockquote>
                )}
                {!tr.quote && tr.source && <p className="text-[14px] text-ink-faint mt-2">Source: {tr.source}</p>}
              </li>
            ))}
          </ol>
          {c.kind === 'exclusion' && (
            <p className="text-[15px] text-ink-soft mt-4 max-w-prose">
              No register shows this person's full income. A defence pension or private earnings would make them
              ineligible, so confirm income at the visit before any application is filed.
            </p>
          )}

          <Decide role={role} c={c} review={data.review} onDone={() => { setFresh(true); reload() }} />
          {role.unmask && !data.unmasked && <Unmask id={c.case_id} onDone={reload} />}
          {data.unmasked && <p className="mt-6 text-[15px] text-stamp">Names are shown on this case for your posting. The reason you gave is in the access log.</p>}
          <History events={data.history} />
        </section>

        {/* right: the enclosures from each department */}
        <section aria-labelledby="enclosures">
          <Heading level={2} hi="संलग्न अभिलेख" en="Records from each department" />
          <Enclosures records={data.records} highlight={c.record_id} />
          <Links links={data.links} records={data.records} />
        </section>
      </div>
    </article>
  )
}

function Decide({ role, c, review, onDone }) {
  const [note, setNote] = React.useState('')
  const [busy, setBusy] = React.useState(false)
  const [error, setError] = React.useState(null)
  if (!role.review) return null
  const act = async (d) => {
    setBusy(true); setError(null)
    try { await api.review(c.case_id, d, note); setNote(''); onDone() } catch (e) { setError(e) } finally { setBusy(false) }
  }
  return (
    <div className="mt-8 panel p-4">
      <h3 className="font-medium text-lg">{review ? 'Change the decision' : 'Record a decision'}</h3>
      <p className="text-[15px] text-ink-soft">The decision goes on the file and in the access log. It does not change any benefit.</p>
      <label className="block mt-3 text-[15px]">Note for the file
        <textarea className="field mt-1 h-20" value={note} onChange={(e) => setNote(e.target.value)} placeholder="What you checked, and with whom" />
      </label>
      <div className="flex flex-wrap gap-2 mt-3">
        {Object.entries(DECISIONS).map(([k, d]) => (
          <button key={k} className={k === 'confirmed' ? 'btn-stamp' : 'btn-quiet'} disabled={busy} onClick={() => act(k)}>
            <span className="hi" lang="hi">{d.hi}</span> {d.en}
          </button>
        ))}
      </div>
      <Problem error={error} />
    </div>
  )
}

function Unmask({ id, onDone }) {
  const [reason, setReason] = React.useState('')
  const [error, setError] = React.useState(null)
  const go = async (e) => {
    e.preventDefault(); setError(null)
    try { await api.unmask(id, reason); onDone() } catch (err) { setError(err) }
  }
  return (
    <form className="mt-6 panel p-4" onSubmit={go}>
      <h3 className="font-medium text-lg">Show names on this case</h3>
      <p className="text-[15px] text-ink-soft">Say why you need them. The reason is kept permanently with your posting. Aadhaar and bank numbers stay masked.</p>
      <label className="block mt-3 text-[15px]">Reason
        <input className="field mt-1" value={reason} onChange={(e) => setReason(e.target.value)} minLength={15} required placeholder="e.g. Field visit to Bhaisiyachhana on 30 September" />
      </label>
      <button className="btn-quiet mt-3" disabled={reason.trim().length < 15}>Show names</button>
      <Problem error={error} />
    </form>
  )
}

function History({ events }) {
  if (!events?.length) return null
  return (
    <div className="mt-8">
      <h3 className="font-medium text-lg mb-2">What has happened on this case</h3>
      <table className="ledger text-[15px]">
        <tbody>
          {events.map((e) => (
            <tr key={e.seq}>
              <td className="whitespace-nowrap text-ink-soft">{e.ts.replace('T', ' ')}</td>
              <td>{e.role}</td>
              <td>{{ open_case: 'Opened', unmask: 'Showed names', review: 'Decided', refused: 'Refused' }[e.action] || e.action}
                {e.detail?.reason && <span className="text-ink-soft">: {e.detail.reason}</span>}
                {e.detail?.decision && <span className="text-ink-soft">: {DECISIONS[e.detail.decision]?.en}{e.detail.note ? `. ${e.detail.note}` : ''}</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Enclosures({ records, highlight }) {
  return (
    <div className="space-y-4">
      {records.map((r) => {
        const reg = REGISTERS[r.register] || {}
        const hit = r.record_id === highlight
        return (
          <div key={r.record_id} className={`panel ${hit ? 'border-stamp ring-1 ring-stamp/40' : ''}`}>
            <div className="flex flex-wrap items-baseline justify-between gap-2 px-4 pt-3">
              <p className="font-medium">{reg.en} <span className="hi text-ink-faint font-normal" lang="hi">{reg.hi}</span></p>
              <p className="text-[14px] text-ink-faint">{reg.dept}{hit ? ', the record this case is about' : ''}</p>
            </div>
            <dl className="grid grid-cols-[minmax(8rem,auto)_1fr] gap-x-4 px-4 pb-3 pt-2 text-[15px]">
              {Object.entries(r.fields).filter(([, v]) => v !== null && v !== '').map(([k, v]) => (
                <React.Fragment key={k}>
                  <dt className="text-ink-soft py-0.5">{FIELD_LABELS[k] || k}</dt>
                  <dd className={`py-0.5 ${/[ऀ-ॿ]/.test(v) ? 'hi' : ''}`}>{String(v)}</dd>
                </React.Fragment>
              ))}
            </dl>
          </div>
        )
      })}
    </div>
  )
}

export function Links({ links, records }) {
  if (!links?.length) return <p className="mt-6 text-ink-soft">This person has one record only; no linking was needed.</p>
  const reg = Object.fromEntries(records.map((r) => [r.record_id, REGISTERS[r.register]?.en || r.register]))
  return (
    <div className="mt-8">
      <h3 className="font-medium text-lg">Why these records are one person</h3>
      <p className="text-[15px] text-ink-soft max-w-prose mb-3">
        Each pair was scored field by field. A positive weight is evidence for a match; a negative weight is evidence
        against. Pairs joined by household were on two documents that already share other matched members.
      </p>
      <ul className="space-y-3">
        {links.slice(0, 8).map((l, i) => (
          <li key={i} className="panel p-3">
            <p className="text-[15px]"><span className="font-medium">{reg[l.record_l]}</span> and <span className="font-medium">{reg[l.record_r]}</span>
              {l.match_weight != null
                ? <span className="text-ink-soft">: total weight {l.match_weight > 0 ? '+' : ''}{l.match_weight}, probability {(l.match_probability * 100).toFixed(l.match_probability > 0.999 ? 2 : 1)}%</span>
                : <span className="text-ink-soft">: {l.via}</span>}</p>
            {l.fields?.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {l.fields.map((f, j) => (
                  <span key={j} className={`tag ${f.weight > 0 ? 'bg-stamp-soft text-stamp' : f.weight < 0 ? 'bg-red-soft text-red-ink' : 'bg-sheet text-ink-soft'}`}>
                    {f.field}: {f.level?.replace('All other comparisons', 'disagrees').replace('Exact match on ', 'same ')} {f.weight != null ? `(${f.weight > 0 ? '+' : ''}${f.weight})` : ''}
                  </span>
                ))}
              </div>
            )}
          </li>
        ))}
      </ul>
      {links.length > 8 && <p className="text-[14px] text-ink-faint mt-2">{links.length - 8} more pairs hold this person together.</p>}
    </div>
  )
}
