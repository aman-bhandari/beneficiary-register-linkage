import React from 'react'
import { api } from '../api.js'
import { Heading, Problem } from '../components.jsx'

export default function Upload({ role }) {
  const [res, setRes] = React.useState(null)
  const [error, setError] = React.useState(null)
  const [busy, setBusy] = React.useState(false)
  const submit = async (e) => {
    e.preventDefault(); setError(null); setRes(null); setBusy(true)
    try { setRes(await api.upload(new FormData(e.target))) } catch (err) { setError(err) } finally { setBusy(false) }
  }
  return (
    <div className="max-w-5xl">
      <Heading hi="विभाग की फ़ाइल जोड़ें" en="Check a department file">
        <p className="text-ink-soft mt-2 max-w-3xl">
          Load a CSV from any department to see how its columns map and how many of its people are already known.
          This is a preview: nothing is written to the registers, and the check is recorded in the access log.
        </p>
      </Heading>
      <form onSubmit={submit} className="panel p-4 grid sm:grid-cols-[1fr_1fr_auto] gap-4 items-end">
        <label className="text-[15px]">Department
          <input name="department" className="field mt-1" required defaultValue="Women Empowerment and Child Development" />
        </label>
        <label className="text-[15px]">CSV file
          <input name="file" type="file" accept=".csv,text/csv" required className="field mt-1 py-1.5" />
        </label>
        <button className="btn-stamp" disabled={busy}>{busy ? 'Checking…' : 'Check the file'}</button>
      </form>
      <p className="text-[14px] text-ink-faint mt-2">A sample file is in the repository: <code>data/samples/nanda_gaura_sample.csv</code>.</p>
      <Problem error={error} />
      {res && (
        <section className="mt-8">
          <p className="hi text-2xl" lang="hi">{res.rows.toLocaleString('en-IN')} में से {res.matched.toLocaleString('en-IN')} लोग पहले से ज्ञात हैं।</p>
          <p className="text-ink-soft">{res.matched.toLocaleString('en-IN')} of {res.rows.toLocaleString('en-IN')} rows ({(res.match_rate * 100).toFixed(1)}%) match someone already linked within your posting.</p>
          <h3 className="font-medium text-lg mt-6 mb-2">Columns understood</h3>
          <table className="ledger max-w-xl"><tbody>
            {Object.entries(res.mapping).map(([k, v]) => <tr key={k}><td className="text-ink-soft">{k.replace('_', ' ')}</td><td>{v}</td></tr>)}
          </tbody></table>
          <h3 className="font-medium text-lg mt-6 mb-2">First rows, as read</h3>
          <div className="overflow-x-auto panel">
            <table className="ledger min-w-[700px] text-[15px]">
              <thead><tr><th className="num">Row</th><th>Name</th><th>Read as</th><th className="num">Birth year</th><th>Place key</th><th>Known person</th></tr></thead>
              <tbody>{res.sample.map((s) => (
                <tr key={s.row}><td className="num">{s.row}</td><td>{s.name}</td><td>{s.first} {s.surname}</td><td className="num">{s.birth_year ?? '—'}</td><td>{s.place_key || '—'}</td>
                  <td>{s.linked_to ? <a className="text-stamp underline" href={`#/person/${s.linked_to}`}>{s.linked_to}</a> : <span className="text-ink-faint">new</span>}</td></tr>
              ))}</tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
