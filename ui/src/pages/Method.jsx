import React from 'react'
import { api } from '../api.js'
import { Bar, Heading, Loading, Problem, useLoad } from '../components.jsx'
import { CASE_TYPES, SCHEMES } from '../words.js'

const pct = (v) => v == null ? '—' : `${(v * 100).toFixed(1)}%`

export default function Method({ role }) {
  const { data, error, loading } = useLoad(() => api.method(), [role.key])
  if (loading) return <Loading />
  if (error) return <Problem error={error} />
  const acc = data.accuracy || {}
  return (
    <div className="max-w-5xl">
      <Heading hi="पद्धति और सटीकता" en="How it works, and how often it is right" />
      <section className="max-w-3xl space-y-3 text-[17px] leading-relaxed">
        <p>
          Nine department registers are read in their own layouts and scripts: the Social Welfare pension roll, the
          Parivar register, ration cards, MGNREGA job cards, PM-KISAN, the death register, disability certificates,
          the Treasury pension roll, housing, and the ex-servicemen register. Names written in Hindi and in English are
          reduced to the same sound-based key, so भगवती देवी बिष्ट and BHAGAWATI BIST can be compared.
        </p>
        <p>
          A probabilistic model scores every candidate pair field by field and learns the weights from the data. A
          second pass uses households: when a ration card and a Parivar household already share two matched members,
          a same-named person of similar age on both is the same person. Two records with different Aadhaar numbers,
          or birth years more than ten years apart, are never joined.
        </p>
        <p>
          Rules are applied to what the linked registers prove, never to a guess. A case is raised only on strong
          evidence of low income: a priority ration card. People with only a State Food Scheme card are counted as a
          survey list, not raised as cases.
        </p>
      </section>

      {(acc.linkage || []).length > 0 && (
        <section className="mt-10">
          <Heading level={2} hi="रिकॉर्ड मिलान की सटीकता" en="Record linkage accuracy" >
            <p className="text-ink-soft mt-1 max-w-3xl">Measured against the planted truth of the synthetic population. Correct means a pair joined as one person really is one person; found means a true pair was joined.</p>
          </Heading>
          {acc.linkage.map((d) => (
            <div key={d.district} className="mb-8">
              <h3 className="font-medium text-lg mb-2">{d.district}: {d.overall.records.toLocaleString('en-IN')} records</h3>
              <table className="ledger">
                <thead><tr><th>Group</th><th className="num">Pairs</th><th className="num">Correct</th><th className="w-40"></th><th className="num">Found</th><th className="w-40"></th></tr></thead>
                <tbody>
                  {d.groups.map((g) => (
                    <tr key={g.group}>
                      <td>{g.group === 'everyone' ? <span className="font-medium">Everyone</span> : g.group}</td>
                      <td className="num">{g.true_pairs.toLocaleString('en-IN')}</td>
                      <td className="num">{pct(g.precision)}</td><td>{g.precision != null && <Bar value={g.precision} max={1} tone="stamp" label="correct" />}</td>
                      <td className="num">{pct(g.recall)}</td><td><Bar value={g.recall} max={1} tone="ink" label="found" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </section>
      )}

      {(acc.findings || []).length > 0 && (
        <section className="mt-6">
          <Heading level={2} hi="निष्कर्षों की सटीकता" en="Findings accuracy" />
          {acc.findings.map((d) => (
            <div key={d.district} className="mb-8 grid lg:grid-cols-2 gap-8">
              <div>
                <h3 className="font-medium text-lg mb-2">{d.district}: payments to check</h3>
                <table className="ledger">
                  <thead><tr><th>Finding</th><th className="num">Planted</th><th className="num">Found</th><th className="num">Right when raised</th></tr></thead>
                  <tbody>{d.integrity.map((x) => <tr key={x.type}><td>{CASE_TYPES[x.type]?.en}</td><td className="num">{x.planted}</td><td className="num">{pct(x.recall)}</td><td className="num">{pct(x.precision)}</td></tr>)}</tbody>
                </table>
              </div>
              <div>
                <h3 className="font-medium text-lg mb-2">{d.district}: people left out</h3>
                <table className="ledger">
                  <thead><tr><th>Scheme</th><th className="num">Truly left out</th><th className="num">Raised</th><th className="num">Right when raised</th><th className="num">High priority right</th></tr></thead>
                  <tbody>{d.exclusion.map((x) => <tr key={x.scheme}><td>{SCHEMES[x.scheme]?.en}</td><td className="num">{x.truly_left_out.toLocaleString('en-IN')}</td><td className="num">{x.flagged.toLocaleString('en-IN')}</td><td className="num">{pct(x.precision)}</td><td className="num">{pct(x.high_priority_precision)}</td></tr>)}</tbody>
                </table>
              </div>
            </div>
          ))}
        </section>
      )}

      <section className="mt-6">
        <Heading level={2} hi="नियम और स्रोत" en="Rules and where they come from" />
        {Object.entries(data.rules.schemes).map(([k, s]) => (
          <div key={k} className="mb-6">
            <h3 className="font-medium text-lg">{s.name_en} <span className="hi text-ink-faint font-normal" lang="hi">{s.name_hi}</span></h3>
            <ul className="mt-2 space-y-2">
              {s.criteria.map((c) => (
                <li key={c.id} className="border-l-[3px] border-stamp/50 pl-3">
                  <p>{c.en}{c.checked === 'advisory' && <span className="text-ochre"> (shown to the officer, not applied automatically)</span>}</p>
                  <p className="hi text-ink-soft" lang="hi">{c.quote}</p>
                </li>
              ))}
            </ul>
          </div>
        ))}
        <ul className="text-[15px] text-ink-soft space-y-1">
          {Object.values(data.rules.sources).map((s) => <li key={s.url}><a className="text-stamp underline underline-offset-2 break-all" href={s.url} target="_blank" rel="noreferrer">{s.title}</a>, read {s.read}</li>)}
        </ul>
        <h3 className="font-medium text-lg mt-6">Questions for the department</h3>
        <ul className="list-disc pl-5 text-ink-soft max-w-3xl space-y-1 mt-1">{data.rules.policy_notes.map((n, i) => <li key={i}>{n}</li>)}</ul>
      </section>
    </div>
  )
}
