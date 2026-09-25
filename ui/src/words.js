// The interface's vocabulary, in Hindi and English. One name per thing, used everywhere.

export const CASE_TYPES = {
  eligible_not_enrolled: { hi: 'पात्र, पर पेंशन नहीं', en: 'Appears eligible, receives no pension', kind: 'exclusion' },
  paid_after_death: { hi: 'मृत्यु के बाद भुगतान', en: 'Paid after a registered death', kind: 'integrity' },
  duplicate_enrolment: { hi: 'एक योजना में दो बार', en: 'Enrolled twice in one scheme', kind: 'integrity' },
  income_above_limit: { hi: 'आय सीमा से अधिक', en: 'Income above the limit', kind: 'integrity' },
  age_disagreement: { hi: 'आयु में अंतर', en: 'Age disagrees across registers', kind: 'integrity' },
  shared_account: { hi: 'साझा बैंक खाता', en: 'Account shared by unrelated pensioners', kind: 'integrity' },
  two_pensions: { hi: 'दो पेंशन एक साथ', en: 'Two pensions at once', kind: 'integrity' },
  uncorroborated: { hi: 'किसी अन्य रिकॉर्ड में नहीं', en: 'Not known to any other register', kind: 'integrity' },
}

export const SCHEMES = {
  old_age: { hi: 'वृद्धावस्था पेंशन', en: 'Old-age pension' },
  widow: { hi: 'विधवा पेंशन', en: 'Widow pension' },
  disability: { hi: 'दिव्यांग पेंशन', en: 'Disability pension' },
}

export const REGISTERS = {
  pension: { hi: 'पेंशन पंजिका', en: 'Pension roll', dept: 'Social Welfare' },
  parivar: { hi: 'परिवार रजिस्टर', en: 'Parivar register', dept: 'Panchayati Raj' },
  ration: { hi: 'राशन कार्ड', en: 'Ration card', dept: 'Food & Civil Supplies' },
  mgnrega: { hi: 'मनरेगा जॉब कार्ड', en: 'MGNREGA job card', dept: 'Rural Development' },
  kisan: { hi: 'पीएम-किसान', en: 'PM-KISAN', dept: 'Agriculture' },
  death: { hi: 'मृत्यु पंजीकरण', en: 'Death register', dept: 'Health (Civil Registration)' },
  udid: { hi: 'दिव्यांगता प्रमाण (UDID)', en: 'Disability certificate (UDID)', dept: 'Social Justice' },
  treasury: { hi: 'कोषागार पेंशन', en: 'Treasury pension roll', dept: 'Finance' },
  pmay: { hi: 'प्रधानमंत्री आवास', en: 'PMAY housing', dept: 'Rural Development' },
}

export const PROGRAMMES = {
  old_age: 'Old-age pension', widow: 'Widow pension', disability: 'Disability pension',
  ration_priority: 'Priority ration card', mgnrega_active: 'MGNREGA work', pm_kisan: 'PM-KISAN',
  pmay_house: 'PMAY house', udid: 'Disability certificate', treasury: 'Treasury pension',
}

export const DECISIONS = {
  confirmed: { hi: 'पुष्टि', en: 'Confirmed' },
  not_a_problem: { hi: 'समस्या नहीं', en: 'Not a problem' },
  field_visit: { hi: 'स्थलीय सत्यापन', en: 'Field visit needed' },
}

export const FIELD_LABELS = {
  pension_id: 'Pension ID', scheme: 'Scheme', applicant_name: 'Name', father_husband_name: 'Father or husband',
  gender: 'Sex', dob: 'Birth date', category: 'Category', gram_panchayat: 'Panchayat', block: 'Block',
  bank_account: 'Bank account', aadhaar: 'Aadhaar', mobile: 'Mobile', sanction_year: 'Sanctioned', status: 'Status',
  family_id: 'Family ID', member_name: 'Name', relation: 'Relation', remark: 'Remark', card_no: 'Card no.',
  card_type: 'Card type', head_of_family: 'Head of family', member_age: 'Age', age_as_on: 'Age as on',
  relation_to_head: 'Relation to head', village: 'Village or ward', job_card_no: 'Job card', worker_name: 'Name',
  age: 'Age', registered: 'Registered', caste: 'Caste', account: 'Account', active: 'Worked recently',
  registration_no: 'Registration', farmer_name: 'Name', land_ha: 'Land (ha)', deceased_name: 'Name',
  age_at_death: 'Age at death', date_of_death: 'Date of death', udid_no: 'UDID', name: 'Name',
  father_guardian_name: 'Father or guardian', disability_type: 'Disability', percentage: 'Percent',
  ppo_no: 'PPO no.', pensioner_name: 'Name', monthly_pension: 'Monthly pension (Rs)', treasury: 'Treasury',
  beneficiary_id: 'Beneficiary ID', beneficiary_name: 'Name',
}

export const rs = (n) => n == null ? '—' : '₹' + Math.round(n).toLocaleString('en-IN')
export const num = (n) => n == null ? '<10' : Number(n).toLocaleString('en-IN')
export const title = (s) => (s || '').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())
REGISTERS.sainik = { hi: 'सैनिक कल्याण', en: 'Ex-servicemen register', dept: 'Sainik Kalyan' }
FIELD_LABELS.service_no = 'Service no.'
FIELD_LABELS.rank = 'Rank'
FIELD_LABELS.regiment = 'Unit'
PROGRAMMES.sainik = 'Defence pension'
