// Interface check: every page for every role at phone and desktop widths.
//   ~/.claude/browser/run.sh ui/check/ui_check.cjs [base-url]
// Fails on: a console error, a page that does not render its heading, horizontal overflow, a tab shown to a role
// that cannot use it, or a case reachable by a role outside its posting. Screenshots go to ui/check/shots/.
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

const BASE = process.argv[2] || 'http://127.0.0.1:8003'
const SHOTS = path.join(__dirname, 'shots')
fs.mkdirSync(SHOTS, { recursive: true })
const ROLES = ['planner', 'dswo_almora', 'aswo_hawalbag', 'dswo_usn', 'dso_almora', 'auditor']
const PAGES = { '': 'Overview', cases: 'Cases', planning: 'Planning', upload: 'Add a file', audit: 'Access log', method: 'Method' }
const CAN = {
  planner: ['', 'planning', 'method'], dso_almora: ['', 'planning', 'method'], auditor: ['', 'planning', 'audit', 'method'],
  dswo_almora: Object.keys(PAGES), aswo_hawalbag: Object.keys(PAGES), dswo_usn: Object.keys(PAGES),
}
const WIDTHS = { phone: { width: 390, height: 844 }, desktop: { width: 1366, height: 900 } }

const failures = []
const fail = (m) => { failures.push(m); console.log('FAIL', m) }

async function openAs(page, role, hash) {
  await page.goto(BASE + '/', { waitUntil: 'domcontentloaded' })
  await page.evaluate((r) => localStorage.setItem('ekatra.role', r), role)
  await page.goto(BASE + '/' + hash, { waitUntil: 'domcontentloaded' })
  await page.reload({ waitUntil: 'networkidle' })          // a hash-only change does not reload the app
  await page.waitForTimeout(400)
}

;(async () => {
  const b = await chromium.launch()
  for (const [wname, vp] of Object.entries(WIDTHS)) {
    const ctx = await b.newContext({ viewport: vp })
    const page = await ctx.newPage()
    const errors = []
    page.on('console', (m) => { if (m.type() === 'error' && !/status of 40[13]/.test(m.text())) errors.push(m.text()) })
    page.on('pageerror', (e) => errors.push(String(e)))
    for (const role of ROLES) {
      await openAs(page, role, '#/')
      const tabs = await page.$$eval('nav[aria-label="Sections"] a', (as) => as.map((a) => a.getAttribute('href').replace('#/', '')))
      const expected = CAN[role]
      if (JSON.stringify(tabs.sort()) !== JSON.stringify([...expected].sort())) fail(`${wname} ${role}: tabs ${tabs} expected ${expected}`)
      for (const p of expected) {
        await openAs(page, role, '#/' + p)
        const h = await page.$('main h1')
        if (!h) fail(`${wname} ${role} ${p || 'overview'}: no heading`)
        const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
        if (overflow > 1) fail(`${wname} ${role} ${p || 'overview'}: page scrolls sideways by ${overflow}px`)
        if (await page.$('[role="alert"]')) fail(`${wname} ${role} ${p || 'overview'}: shows an error: ${await page.$eval('[role="alert"]', (e) => e.innerText)}`)
        await page.screenshot({ path: path.join(SHOTS, `${wname}-${role}-${p || 'overview'}.png`), fullPage: p !== 'audit' })
      }
    }
    // a case file end to end, as the Almora district officer: open, unmask with a reason, stamp a decision
    await openAs(page, 'dswo_almora', '#/cases?kind=exclusion&priority=high')
    const first = await page.$('table.ledger tbody a')
    if (!first) fail(`${wname}: no case in the register`)
    else {
      const id = (await first.innerText()).trim()
      await first.click()
      await page.waitForSelector('main h1')
      await page.waitForTimeout(500)
      await page.screenshot({ path: path.join(SHOTS, `${wname}-case-masked.png`), fullPage: true })
      if (!(await page.innerText('main')).includes('•')) fail(`${wname}: case ${id} shows names before unmasking`)
      if (wname === 'desktop') {
        await page.fill('input[placeholder^="e.g."]', 'Field visit to verify eligibility on 30 September')
        const beforeTrace = await page.innerText('main')
        if (/\d{9,}/.test(beforeTrace.replace(/[\s,₹]/g, ' ').split(' ').filter((w) => /^\d+$/.test(w)).join(' '))) fail('a long document number is visible before unmasking')
        await page.click('button:has-text("Show names")')
        await page.waitForTimeout(1200)
        if (!(await page.innerText('main')).includes('Names are shown on this case')) fail('unmasking with a reason did not reveal names')
        await page.click('button:has-text("Field visit needed")')
        await page.waitForSelector('.stamp-mark', { timeout: 5000 }).catch(() => fail('no decision stamp after deciding'))
        await page.waitForTimeout(600)
        await page.screenshot({ path: path.join(SHOTS, `${wname}-case-decided.png`), fullPage: true })
      }
      // the block officer of Hawalbagh must not be able to open a case from another block by URL
      const other = await page.evaluate(async () => {
        const r = await fetch('/api/cases?block=DHAULADEVI&size=1', { headers: { 'X-Role': 'dswo_almora' } })
        return (await r.json()).rows[0]?.case_id
      })
      await openAs(page, 'aswo_hawalbag', `#/case/${other}`)
      if (!(await page.innerText('main')).includes('Outside what this posting may see')) fail(`${wname}: block officer could open ${other}`)
    }
    if (errors.length) fail(`${wname}: console errors: ${[...new Set(errors)].slice(0, 5).join(' | ')}`)
    await ctx.close()
  }
  await b.close()
  console.log(failures.length ? `${failures.length} failure(s)` : 'ALL CHECKS PASSED')
  process.exit(failures.length ? 1 : 0)
})()
