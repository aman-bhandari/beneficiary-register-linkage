// Pension counts from the Social Welfare Department's public portal, ssp.uk.gov.in.
// Aggregate counts only: district -> area -> tehsil -> block -> gram panchayat. No individual records are read.
//   node ssp_counts.js --districts Almora            (district table for all 13 + drill-down for the named ones)
// Output: data/ref/ssp_district.csv, ssp_block_<district>.csv, ssp_panchayat_<district>.csv, ssp_meta_<district>.json
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const OUT = path.join(__dirname, '..', 'data', 'ref');
const HOME = 'https://ssp.uk.gov.in/';
const INSTALMENT_ROW = 4;                 // 5th instalment row: the latest complete one on 25 Sep 2026
const args = process.argv.slice(2);
const wanted = (args[args.indexOf('--districts') + 1] || 'Almora').split(',');

async function click(p, sel) {
  await Promise.all([p.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 90000 }), p.click(sel)]);
  await p.waitForSelector('table[id$="gvDetails"]', { timeout: 90000 });
  await p.waitForTimeout(500);
}
async function rows(p) {
  return p.$$eval('table[id$="gvDetails"] tr', trs => trs.map(tr => [...tr.querySelectorAll('th,td')].map(c => c.innerText.trim())));
}
async function toDistricts(p) {
  await p.goto(HOME, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await p.waitForTimeout(2000);
  await click(p, 'a[href*="LinkBtn_ClickAll"]');
  const links = await p.$$eval('a', as => as.map(a => a.getAttribute('href')).filter(h => h && h.includes('gvDetails') && h.includes('LinkBtn_Click')));
  await click(p, `a[href="${links[INSTALMENT_ROW]}"]`);
}
const ctl = i => `ctl${String(i + 2).padStart(2, '0')}`;   // GridView row i -> ctl02, ctl03, ...
function csv(file, header, data) {
  const esc = v => /[",\n]/.test(v) ? `"${String(v).replace(/"/g, '""')}"` : v;
  fs.writeFileSync(path.join(OUT, file), [header, ...data].map(r => r.map(esc).join(',')).join('\n') + '\n');
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage();
  await toDistricts(p);
  const dist = await rows(p);
  const dHead = dist[0];
  const dRows = dist.slice(1).filter(r => r.length > 5 && r[0] && !r[0].startsWith('Total'));
  csv('ssp_district.csv', dHead.slice(0, 19), dRows.map(r => r.slice(0, 19)));
  console.log(`districts: ${dRows.length}`);

  const blocks = [], gps = [];
  for (const dname of wanted) {
    const di = dRows.findIndex(r => r[0] === dname);
    if (di < 0) { console.log('no district', dname); continue; }
    await toDistricts(p); await click(p, `a[href*="${ctl(di)}$LinkBtn_Area"]`);
    const areas = (await rows(p)).slice(1).filter(r => r[0] && r.length > 5).map(r => r[0]);
    for (let ai = 0; ai < areas.length; ai++) {
      await toDistricts(p); await click(p, `a[href*="${ctl(di)}$LinkBtn_Area"]`);
      await click(p, `a[href*="${ctl(ai)}$LinkBtn_Click"]`);
      const tehsils = (await rows(p)).slice(1).filter(r => r[0] && r.length > 5).map(r => r[0]);
      for (let ti = 0; ti < tehsils.length; ti++) {
        await toDistricts(p); await click(p, `a[href*="${ctl(di)}$LinkBtn_Area"]`);
        await click(p, `a[href*="${ctl(ai)}$LinkBtn_Click"]`);
        await click(p, `a[href*="${ctl(ti)}$LinkBtn_Click"]`);
        const bRows = (await rows(p)).slice(1).filter(r => r[0] && r.length > 5);
        for (const r of bRows) blocks.push([dname, areas[ai], tehsils[ti], ...r.slice(0, 8)]);
        console.log(`${dname} / ${areas[ai]} / ${tehsils[ti]}: ${bRows.length} units`);
        if (areas[ai] !== 'Rural') continue;       // urban units have no panchayat level
        for (let bi = 0; bi < bRows.length; bi++) {
          if (bi > 0) {
            await toDistricts(p); await click(p, `a[href*="${ctl(di)}$LinkBtn_Area"]`);
            await click(p, `a[href*="${ctl(ai)}$LinkBtn_Click"]`);
            await click(p, `a[href*="${ctl(ti)}$LinkBtn_Click"]`);
          }
          await click(p, `a[href*="${ctl(bi)}$LinkBtn_Click"]`);
          const gRows = (await rows(p)).slice(1).filter(r => r[0] && r.length > 3);
          for (const r of gRows) gps.push([dname, tehsils[ti], bRows[bi][0], ...r.slice(0, 5)]);
          console.log(`   ${bRows[bi][0]}: ${gRows.length} panchayats`);
        }
      }
    }
  }
  const slug = wanted.join('_').toLowerCase().replace(/[^a-z_]+/g, '_');
  csv(`ssp_block_${slug}.csv`, ['district', 'area', 'tehsil', 'unit', 'old_age', 'widow', 'disability', 'total', 'old_age_lakh', 'widow_lakh', 'disability_lakh'], blocks);
  csv(`ssp_panchayat_${slug}.csv`, ['district', 'tehsil', 'block', 'panchayat', 'old_age', 'widow', 'disability', 'total'], gps);
  fs.writeFileSync(path.join(OUT, `ssp_meta_${slug}.json`), JSON.stringify({ source: HOME, fetched: new Date().toISOString(), financial_year: '2026-27', instalment: INSTALMENT_ROW + 1, districts_drilled: wanted }, null, 2));
  await b.close();
})();
