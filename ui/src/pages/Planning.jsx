import React from 'react'
import { api } from '../api.js'
import { Bar, Heading, Loading, Problem, useLoad } from '../components.jsx'
import { CASE_TYPES, PROGRAMMES, num, rs, title } from '../words.js'

export default function Planning({ role }) {
  const districts = role.districts || ['Almora', 'Udham Singh Nagar']
  const [district, setDistrict] = React.useState(districts[0])
  const plan = useLoad(() => api.planning(district), [role.key, district])
  const ov = useLoad(() => api.overlap(district), [role.key, district])

  return (
    <div>
      <Heading hi="नियोजन" en="Planning by block">
        <p className="text-ink-soft mt-2 max-w-3xl">
          Where people are left out, where payments leak, and which schemes the same people draw on.
          {role.min_cell ? ` Figures under ${role.min_cell} are withheld so no count can point to a person.` : ''}
        </p>
      </Heading>
      {districts.length > 1 && (
        <div className="flex gap-2 mb-6" role="tablist">
          {districts.map((d) => (
            <button key={d} role="tab" aria-selected={d === district} onClick={() => setDistrict(d)}
                    className={d === district ? 'btn-stamp' : 'btn-quiet'}>{d}</button>
          ))}
        </div>
      )}
      <Problem error={plan.error} />
      {plan.loading && <Loading />}
      {plan.data && <Blocks data={plan.data} />}
      <Problem error={ov.error} />
      {ov.data && <Overlap data={ov.data} />}
    </div>
  )
}

function Blocks({ data }) {
  const max = Math.max(...data.blocks.map((b) => b.aged_60_priority_card || 0), 1)
  const totalLeak = data.totals.filter((t) => t.kind === 'integrity' && t.type !== 'two_pensions').reduce((a, t) => a + t.amount, 0)
  return (
    <section className="mb-12">
      <p className="hi text-2xl mb-1" lang="hi">संदिग्ध भुगतान: {rs(totalLeak)} प्रति वर्ष</p>
      <p className="text-ink-soft mb-5">Payments to check add up to about {rs(totalLeak)} a year at ₹{data.monthly_rate.toLocaleString('en-IN')} a month. Payments after death count the months since the death.</p>
      <div className="overflow-x-auto panel">
        <table className="ledger min-w-[900px]">
          <thead>
            <tr>
              <th>Block</th><th className="num">Living people</th><th className="num">Aged 60+ with a priority ration card</th>
              <th className="w-44"></th><th className="num">Old-age pensioners linked</th><th className="num">On the portal</th>
              <th className="num">Left out</th><th className="num">Payments to check</th><th className="num">A year</th>
            </tr>
          </thead>
          <tbody>
            {data.blocks.map((b) => (
              <tr key={b.district + b.block}>
                <td className="font-medium">{title(b.block)}</td>
                <td className="num">{num(b.people)}</td>
                <td className="num">{num(b.aged_60_priority_card)}</td>
                <td><Bar value={b.aged_60_priority_card || 0} max={max} tone="ochre" label="aged 60 and over with a priority card" /></td>
                <td className="num">{num(b.old_age_pensioners)}</td>
                <td className="num">{b.portal ? Number(b.portal.old_age).toLocaleString('en-IN') : '—'}</td>
                <td className="num text-ochre font-medium">{num(b.left_out)}</td>
                <td className="num text-red-ink">{num(b.integrity)}</td>
                <td className="num">{rs(b.leakage_rs)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[15px] text-ink-soft mt-3 max-w-3xl">
        "On the portal" is the Social Welfare Department's own count for the block. "Linked" counts people whose pension
        record was matched to at least one other register, so the gap between the two is people known to one department only.
      </p>
      <h3 className="font-medium text-lg mt-8 mb-2">All findings</h3>
      <table className="ledger max-w-2xl">
        <thead><tr><th>Finding</th><th className="num">Cases</th><th className="num">A year</th></tr></thead>
        <tbody>{data.totals.map((t) => <tr key={t.type}><td>{CASE_TYPES[t.type]?.en}</td><td className="num">{num(t.n)}</td><td className="num">{t.type === 'two_pensions' ? '—' : rs(t.amount)}</td></tr>)}</tbody>
      </table>
    </section>
  )
}

function Overlap({ data }) {
  const p = data.programmes
  const vals = Object.values(data.cells).filter((v) => v != null)
  const max = Math.max(...vals, 1)
  return (
    <section>
      <Heading level={2} hi="योजनाओं का आपसी मेल" en="Who draws on which schemes">
        <p className="text-ink-soft mt-1 max-w-3xl">People counted in both the row and the column programme. The diagonal is each programme's total. Darker means more people.</p>
      </Heading>
      <div className="overflow-x-auto">
        <table className="border-collapse text-[14px]">
          <thead>
            <tr><th></th>{p.map((c) => <th key={c} className="px-2 pb-2 font-medium text-ink-soft align-bottom text-left" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>{PROGRAMMES[c]}</th>)}</tr>
          </thead>
          <tbody>
            {p.map((r) => (
              <tr key={r}>
                <th className="text-left pr-3 font-medium text-ink-soft whitespace-nowrap">{PROGRAMMES[r]}</th>
                {p.map((c) => {
                  const v = data.cells[`${r}|${c}`]
                  const a = v == null ? 0 : Math.sqrt(v / max)
                  return (
                    <td key={c} className="w-[68px] h-10 text-center border border-paper tabular-nums"
                        style={{ background: v == null ? '#E4E9E2' : `rgba(78,58,142,${0.06 + 0.88 * a})`, color: a > 0.5 ? '#fff' : '#1C2B3A' }}
                        title={`${PROGRAMMES[r]} and ${PROGRAMMES[c]}: ${v == null ? 'withheld' : v.toLocaleString('en-IN')}`}>
                      {v == null ? '<' + data.min_cell : v >= 10000 ? `${Math.round(v / 1000)}k` : v.toLocaleString('en-IN')}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
