import React from 'react'
import { api, getRole, setRole } from './api.js'
import { Loading, Problem, useLoad } from './components.jsx'
import Overview from './pages/Overview.jsx'
import Register from './pages/Register.jsx'
import CaseFile from './pages/CaseFile.jsx'
import Person from './pages/Person.jsx'
import Planning from './pages/Planning.jsx'
import Method from './pages/Method.jsx'
import Audit from './pages/Audit.jsx'
import Upload from './pages/Upload.jsx'

function useRoute() {
  const [hash, setHash] = React.useState(window.location.hash || '#/')
  React.useEffect(() => {
    const on = () => { setHash(window.location.hash || '#/'); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  const [, page = '', arg] = hash.split('/')
  const [path, query = ''] = page.split('?')
  return { page: path, arg: arg && decodeURIComponent(arg.split('?')[0]), query: new URLSearchParams(query || (arg || '').split('?')[1] || '') }
}

// what each posting's navigation offers: a tab it cannot use is not shown at all
function tabs(role) {
  const t = [{ href: '#/', hi: 'सारांश', en: 'Overview' }]
  if (role.cases) t.push({ href: '#/cases', hi: 'प्रकरण', en: 'Cases' })
  t.push({ href: '#/planning', hi: 'नियोजन', en: 'Planning' })
  if (role.cases) t.push({ href: '#/upload', hi: 'फ़ाइल जोड़ें', en: 'Add a file' })
  if (role.audit || role.cases) t.push({ href: '#/audit', hi: 'अभिलेख', en: 'Access log' })
  t.push({ href: '#/method', hi: 'पद्धति', en: 'Method' })
  return t
}

function Seal({ role }) {
  return (
    <div className="seal text-stamp w-14 h-14 grid place-items-center shrink-0" aria-hidden="true">
      <span className="hi text-lg leading-none">{role.title_hi.slice(0, 1)}</span>
    </div>
  )
}

export default function App() {
  const route = useRoute()
  const [roleKey, setRoleKey] = React.useState(getRole())
  const roles = useLoad(() => api.roles(), [])
  const role = roles.data?.find((r) => r.key === roleKey)

  const change = (k) => { setRole(k); setRoleKey(k); window.location.hash = '#/' }

  if (roles.error) return <div className="max-w-3xl mx-auto p-8"><Problem error={roles.error} /><p>Start the service with <code>./run.sh serve</code>.</p></div>
  if (!role) return <Loading what="Opening" />

  const here = '#/' + route.page
  return (
    <div className="min-h-screen">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:m-2 focus:p-2 focus:bg-paper">Skip to content</a>
      <header className="bg-paper border-b border-rule">
        <div className="max-w-[1240px] mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center gap-x-6 gap-y-3">
          <a href="#/" className="flex items-baseline gap-2 no-underline">
            <span className="hi text-2xl text-stamp" lang="hi">एकत्र</span>
            <span className="text-ink font-semibold">Ekatra</span>
          </a>
          <p className="text-ink-soft text-[15px] hidden md:block max-w-md leading-snug">
            Beneficiary records linked across departments, for officers to verify
          </p>
          <div className="ml-auto flex items-center gap-3">
            <Seal role={role} />
            <label className="block">
              <span className="block text-[13px] text-ink-faint">Acting as</span>
              <select className="field py-1.5 pr-8 font-medium max-w-[19rem]" value={roleKey} onChange={(e) => change(e.target.value)}>
                {roles.data.map((r) => <option key={r.key} value={r.key}>{r.title}</option>)}
              </select>
            </label>
          </div>
        </div>
        <nav className="max-w-[1240px] mx-auto px-4 sm:px-6 flex gap-1 overflow-x-auto" aria-label="Sections">
          {tabs(role).map((t) => {
            const active = t.href === here || (t.href === '#/cases' && here === '#/case')
            return (
              <a key={t.href} href={t.href} aria-current={active ? 'page' : undefined}
                 className={`px-3 pt-2 pb-2.5 border-b-[3px] whitespace-nowrap no-underline ${active ? 'border-stamp text-ink' : 'border-transparent text-ink-soft hover:text-ink'}`}>
                <span className="hi mr-1.5" lang="hi">{t.hi}</span><span className="text-[15px]">{t.en}</span>
              </a>
            )
          })}
        </nav>
      </header>

      <div className="bg-stamp-soft/60 border-b border-rule">
        <p className="max-w-[1240px] mx-auto px-4 sm:px-6 py-2 text-[15px] text-ink-soft">
          <span className="text-ink font-medium">{role.office}.</span> {role.note} Every figure comes from a synthetic
          population; no real citizen is in this system.
        </p>
      </div>

      <main id="main" className="max-w-[1240px] mx-auto px-4 sm:px-6 py-8" key={roleKey}>
        {route.page === '' && <Overview role={role} />}
        {route.page === 'cases' && <Register role={role} query={route.query} />}
        {route.page === 'case' && <CaseFile role={role} id={route.arg} />}
        {route.page === 'person' && <Person role={role} id={route.arg} />}
        {route.page === 'planning' && <Planning role={role} />}
        {route.page === 'method' && <Method role={role} />}
        {route.page === 'audit' && <Audit role={role} />}
        {route.page === 'upload' && <Upload role={role} />}
      </main>

      <footer className="max-w-[1240px] mx-auto px-4 sm:px-6 pb-10 text-[14px] text-ink-faint">
        Ekatra raises cases for officer verification. It does not enrol, stop or change any benefit.
        Independent prototype, not a Government of Uttarakhand system.
      </footer>
    </div>
  )
}
