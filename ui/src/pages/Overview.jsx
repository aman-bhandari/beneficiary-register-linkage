import React from 'react'
import { api } from '../api.js'
import { Heading, Loading, Problem, useLoad } from '../components.jsx'
import { CASE_TYPES, SCHEMES, num, rs } from '../words.js'

export default function Overview({ role }) {
  const { data, error, loading } = useLoad(() => api.overview(), [role.key])
  if (loading) return <Loading />
  if (error) return <Problem error={error} />

  const exc = data.counts.filter((c) => c.kind === 'exclusion')
  const int = data.counts.filter((c) => c.kind === 'integrity')
  const leftOut = exc.reduce((a, c) => a + (c.n || 0), 0)
  const money = int.filter((c) => c.type !== 'two_pensions').reduce((a, c) => a + (c.amount || 0), 0)
  const where = role.blocks ? `${role.blocks[0].toLowerCase().replace(/^\w/, (c) => c.toUpperCase())} block` : role.districts ? role.districts.join(' and ') : 'the two districts'

  return (
    <div>
      {/* the opening line is the finding that matters most: people entitled and not paid */}
      <section className="max-w-4xl mb-10">
        <p className="hi text-[2.1rem] sm:text-[2.6rem] leading-[1.2] text-ink" lang="hi">
          {where === 'the two districts' ? 'दोनों जनपदों' : 'इस क्षेत्र'} में <span className="text-ochre">{leftOut.toLocaleString('en-IN')}</span> लोग
          पेंशन के पात्र दिखते हैं, पर उन्हें कोई पेंशन नहीं मिल रही।
        </p>
        <p className="text-xl text-ink-soft mt-3 max-w-3xl">
          In {where}, {leftOut.toLocaleString('en-IN')} people appear to meet every published criterion for a pension and
          receive none. {int.reduce((a, c) => a + (c.n || 0), 0).toLocaleString('en-IN')} payments need checking, worth
          about {rs(money)} a year.
        </p>
        {role.cases && (
          <p className="mt-4 text-[15px] text-ink-soft">
            This posting returns {data.cases_in_scope.toLocaleString('en-IN')} of {data.cases_total.toLocaleString('en-IN')} cases.
            The query itself refused the other {data.cases_refused.toLocaleString('en-IN')}; they were never read.{' '}
            <a className="text-stamp underline underline-offset-2" href="#/cases?kind=exclusion&priority=high">Open the high-priority cases</a>
          </p>
        )}
      </section>

      <div className="grid lg:grid-cols-2 gap-x-12 gap-y-10">
        <section aria-labelledby="left-out">
          <Heading level={2} hi="जो छूट गए" en="People left out" />
          <table className="ledger" id="left-out">
            <thead><tr><th>Scheme</th><th className="num">People</th><th className="num">High priority</th></tr></thead>
            <tbody>
              {exc.map((c) => (
                <tr key={c.scheme}>
                  <td>
                    {role.cases ? <a className="text-ink underline decoration-rule underline-offset-4 hover:decoration-ochre" href={`#/cases?kind=exclusion&scheme=${c.scheme}`}>{SCHEMES[c.scheme]?.en}</a> : SCHEMES[c.scheme]?.en}
                    <span className="hi text-ink-faint ml-2" lang="hi">{SCHEMES[c.scheme]?.hi}</span>
                  </td>
                  <td className="num">{num(c.n)}</td><td className="num">{num(c.high)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[15px] text-ink-soft mt-3 max-w-prose">
            Each case lists the criteria met, the register each fact came from, and the published text of the rule.
            High priority means a priority ration card proves low income and the age or widowhood is well evidenced.
          </p>
        </section>

        <section aria-labelledby="payments">
          <Heading level={2} hi="भुगतान जिनकी जाँच हो" en="Payments to check" />
          <table className="ledger" id="payments">
            <thead><tr><th>Finding</th><th className="num">Cases</th><th className="num">A year</th></tr></thead>
            <tbody>
              {int.map((c) => (
                <tr key={c.type + c.scheme}>
                  <td>
                    {role.cases ? <a className="text-ink underline decoration-rule underline-offset-4 hover:decoration-red-ink" href={`#/cases?type=${c.type}`}>{CASE_TYPES[c.type]?.en}</a> : CASE_TYPES[c.type]?.en}
                    {c.scheme && SCHEMES[c.scheme] && <span className="text-ink-faint">, {SCHEMES[c.scheme].en.toLowerCase()}</span>}
                  </td>
                  <td className="num">{num(c.n)}</td>
                  <td className="num">{c.type === 'two_pensions' ? <span className="text-ink-faint">rule unclear</span> : rs(c.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-[15px] text-ink-soft mt-3 max-w-prose">
            Amounts use the published rate of ₹1,500 a month. For payments after death, it is the months paid since
            the registered date of death.
          </p>
        </section>
      </div>

      <section className="mt-12">
        <Heading level={2} hi="क्या जोड़ा गया" en="What was linked" />
        <table className="ledger max-w-4xl">
          <thead><tr><th>District</th><th className="num">Households</th><th className="num">Living people</th><th className="num">Register records</th><th className="num">Pensioners on the portal</th><th className="num">In this system</th></tr></thead>
          <tbody>
            {data.districts.map((d) => (
              <tr key={d.district}>
                <td className="font-medium">{d.district}</td>
                <td className="num">{d.households.toLocaleString('en-IN')}</td>
                <td className="num">{d.persons_alive.toLocaleString('en-IN')}</td>
                <td className="num">{Object.values(d.records).reduce((a, b) => a + b, 0).toLocaleString('en-IN')}</td>
                <td className="num">{d.calibration.portal.toLocaleString('en-IN')}</td>
                <td className="num">{d.calibration.enrolled.toLocaleString('en-IN')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="text-[15px] text-ink-soft mt-3 max-w-3xl">
          Pensioner counts per gram panchayat were read from ssp.uk.gov.in on 25 September 2026, and the synthetic
          rolls are sized to match them. The people and their records are generated; the geography and counts are real.
        </p>
      </section>
    </div>
  )
}
