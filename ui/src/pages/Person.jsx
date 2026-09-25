import React from 'react'
import { api } from '../api.js'
import { Heading, Loading, Problem, useLoad } from '../components.jsx'
import { REGISTERS, SCHEMES, title } from '../words.js'
import { Enclosures, Links } from './CaseFile.jsx'

// One person across every department: what they receive, and what each register says about them.
export default function Person({ role, id }) {
  const { data, error, loading } = useLoad(() => api.person(id), [role.key, id])
  if (loading) return <Loading />
  if (error) return <Problem error={error} />
  const p = data.person
  const receives = [
    ...(p.pensions ? p.pensions.split(',').map((s) => SCHEMES[s]?.en) : []),
    p.ration_type && `${p.ration_type} ration card`, p.mgnrega_active && 'MGNREGA work', p.land_ha && 'PM-KISAN',
    p.pmay_year && `PMAY house (${p.pmay_year})`, p.treasury_pension && 'Treasury pension',
  ].filter(Boolean)
  return (
    <div>
      <Heading hi="एक व्यक्ति, सभी विभाग" en="One person across departments" />
      <p className="hi text-2xl" lang="hi">{p.name_hi || p.name_en}</p>
      <p className="text-ink-soft">{p.name_en}, about {Math.round(p.age)} years. {title(p.panchayat)}, {title(p.block)}, {p.district}.
        {!p.alive && <span className="text-red-ink"> Death registered {p.date_of_death}.</span>}</p>
      <p className="mt-3"><span className="font-medium">Receives:</span> {receives.length ? receives.join(', ') : 'nothing on any register linked here'}.</p>
      {p.widow_evidence && <p className="mt-1 text-ink-soft">{p.widow_evidence}</p>}
      <div className="mt-8 grid xl:grid-cols-2 gap-8">
        <section><Enclosures records={data.records} /></section>
        <section><Links links={data.links} records={data.records} /></section>
      </div>
    </div>
  )
}
