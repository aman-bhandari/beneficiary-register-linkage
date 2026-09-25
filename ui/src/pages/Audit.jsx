import React from 'react'
import { api } from '../api.js'
import { Heading, Loading, Problem, useLoad } from '../components.jsx'

const ACTIONS = { overview: 'Viewed overview', list_cases: 'Listed cases', open_case: 'Opened a case', unmask: 'Showed names',
  review: 'Recorded a decision', open_person: 'Opened a person', refused: 'Refused', planning: 'Viewed planning',
  overlap: 'Viewed overlaps', upload: 'Checked a department file', verify_audit: 'Verified this log' }

export default function Audit({ role }) {
  const [action, setAction] = React.useState('')
  const log = useLoad(() => api.audit({ action, limit: 200 }), [role.key, action])
  const [check, setCheck] = React.useState(null)
  const [busy, setBusy] = React.useState(false)
  const verify = async () => { setBusy(true); try { setCheck(await api.verify()) } catch (e) { setCheck({ error: e.message }) } finally { setBusy(false) } }

  return (
    <div>
      <Heading hi="पहुँच अभिलेख" en="Access log">
        <p className="text-ink-soft mt-2 max-w-3xl">
          Every opened case, every name shown and every decision is written here and cannot be changed. Each entry
          carries a fingerprint of the one before it, so an edited or deleted entry breaks the chain from that point on.
          {!role.audit && ' You see your own entries.'}
        </p>
      </Heading>
      <div className="flex flex-wrap items-end gap-4 mb-6">
        <button className="btn-stamp" onClick={verify} disabled={busy}>Verify the chain</button>
        {check && !check.error && (check.ok
          ? <p className="text-stamp font-medium">Intact: all {check.entries_checked.toLocaleString('en-IN')} entries check out.</p>
          : <p className="text-red-ink font-medium">Broken at entry {check.broken_at}: {check.reason}.</p>)}
        {check?.error && <p className="text-red-ink">{check.error}</p>}
        <label className="text-[14px] text-ink-soft ml-auto">Show
          <select className="field mt-1" value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">Everything</option>
            {Object.entries(ACTIONS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
      </div>
      <Problem error={log.error} />
      {log.loading && <Loading />}
      {log.data && (
        <div className="overflow-x-auto panel">
          <table className="ledger min-w-[820px] text-[15px]">
            <thead><tr><th className="num">Entry</th><th>When</th><th>Posting</th><th>What</th><th>On</th><th>Fingerprint</th></tr></thead>
            <tbody>
              {log.data.events.map((e) => (
                <tr key={e.seq}>
                  <td className="num">{e.seq}</td>
                  <td className="whitespace-nowrap">{e.ts.replace('T', ' ')}</td>
                  <td>{e.role}</td>
                  <td>{ACTIONS[e.action] || e.action}{e.detail?.reason && <div className="text-ink-soft">Reason: {e.detail.reason}</div>}
                    {e.detail?.decision && <div className="text-ink-soft">{e.detail.decision.replace('_', ' ')}{e.detail.note ? `: ${e.detail.note}` : ''}</div>}</td>
                  <td>{e.object ? (e.object.includes('-') && role.cases ? <a className="text-stamp underline" href={`#/case/${e.object}`}>{e.object}</a> : e.object) : '—'}</td>
                  <td className="text-ink-faint text-[13px]" title={e.hash}>{e.hash.slice(0, 12)}…</td>
                </tr>
              ))}
              {!log.data.events.length && <tr><td colSpan="6" className="py-6 text-ink-soft">Nothing recorded yet for this posting.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
