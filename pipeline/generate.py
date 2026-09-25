"""Synthetic population and department registers for a district, at 1:1 scale.

Nothing here is real personal data. What is real: the geography (tehsils, blocks and gram panchayats as listed on
ssp.uk.gov.in), the number of pensioners per panchayat and scheme on that portal on the fetch date, each
district's Census 2011 size, sex ratio and community mix, and the eligibility rules and pension amounts the Social
Welfare Department publishes.

The district is generated one tehsil at a time so memory stays flat however large the district is.

Output (data/gen/<district>/): persons.parquet (the truth), one parquet per department register in that
department's own layout, truth_records.parquet (record -> person, plus any planted anomaly), summary.json.

    python pipeline/generate.py --district Almora [--scale 1.0] [--seed 2026]
"""
from __future__ import annotations

import argparse
import json
import random
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from names import COMMUNITIES, DISTRICT_COMMUNITIES

ROOT = Path(__file__).resolve().parent.parent
REF = ROOT / "data" / "ref"
TODAY = date(2026, 9, 25)
POOR_INCOME = 4000                      # Rs per month, ssp.uk.gov.in FAQ

# Census 2011 district facts (District Census Handbook figures as quoted on Wikipedia, read 25 Sep 2026).
# Household mix and poverty rates are modelling assumptions, documented in docs/DATA.md.
DISTRICTS = {
    "Almora": dict(code="ALM", population=622_506, urban_share=0.10,
                   households=dict(alone=0.10, elder_couple=0.12, nuclear=0.44, joint=0.34),
                   kids=[0, 1, 1, 2, 2, 2, 3, 3, 4], bpl=dict(default=0.33, sc=0.47)),
    "Udham Singh Nagar": dict(code="USN", population=1_648_902, urban_share=0.356,
                              households=dict(alone=0.045, elder_couple=0.075, nuclear=0.50, joint=0.38),
                              kids=[0, 1, 2, 2, 2, 3, 3, 4, 5],
                              bpl=dict(default=0.36, sc=0.52, st=0.55, muslim=0.46, sikh=0.20, bengali=0.42)),
}

# Planted anomalies, as a share of the pension roll. Sizes are assumptions, stated in docs/DATA.md.
PLANT = dict(died_still_paid=0.012, duplicate_same_scheme=0.004, two_pensions=0.003,
             treasury_income=0.008, age_inflated=0.005, ghost=0.002, ring_share=0.0005)

REL_HI = {"head": "मुखिया", "wife": "पत्नी", "husband": "पति", "son": "पुत्र", "daughter": "पुत्री",
          "daughter_in_law": "पुत्रवधू", "grandson": "पौत्र", "granddaughter": "पौत्री", "mother": "माता", "father": "पिता"}
REL_EN = {"head": "SELF", "wife": "WIFE", "husband": "HUSBAND", "son": "SON", "daughter": "DAUGHTER",
          "daughter_in_law": "DAUGHTER IN LAW", "grandson": "GRANDSON", "granddaughter": "GRANDDAUGHTER",
          "mother": "MOTHER", "father": "FATHER"}
SCHEME_HI = {"old_age": "वृद्धावस्था पेंशन", "widow": "विधवा पेंशन", "disability": "दिव्यांग पेंशन"}
CATEGORY_HI = {"sc": "अनुसूचित जाति", "st": "अनुसूचित जनजाति", "obc_general": "अन्य पिछड़ा वर्ग", "general": "सामान्य"}


def slug(district: str) -> str:
    return district.lower().replace(" ", "_")


def load_units(district: str) -> pd.DataFrame:
    gp = pd.read_csv(REF / f"ssp_panchayat_{slug(district)}.csv")
    gp["area"] = "Rural"
    blk = pd.read_csv(REF / f"ssp_block_{slug(district)}.csv")
    urb = blk[blk.area == "Urban"].rename(columns={"unit": "panchayat"}).copy()
    urb["block"] = urb["panchayat"]
    keep = ["district", "tehsil", "block", "panchayat", "area", "old_age", "widow", "disability"]
    units = pd.concat([gp[keep], urb[keep]])
    for c in ("old_age", "widow", "disability"):
        units[c] = pd.to_numeric(units[c], errors="coerce").fillna(0).astype(int)
    units = units[units[["old_age", "widow", "disability"]].sum(axis=1) > 0].reset_index(drop=True)
    units["unit_id"] = np.arange(len(units))
    return units


def age_on(birth: date, d: date = TODAY) -> int:
    return d.year - birth.year - ((d.month, d.day) < (birth.month, birth.day))


# ---------------------------------------------------------------------------------------------------------------
# people and households
# ---------------------------------------------------------------------------------------------------------------
class World:
    """Holds one tehsil's people. Identifiers are unique across the whole district run."""

    def __init__(self, seed: int, cfg: dict, pid_start: int, hid_start: int, used_aadhaar: set):
        self.r = random.Random(seed)
        self.np = np.random.default_rng(seed)
        self.cfg = cfg
        self.people: list[dict] = []
        self.households: dict[int, dict] = {}
        self.pid0, self.next_hid = pid_start, hid_start
        self.used_aadhaar = used_aadhaar
        self.hh_names: dict = {}

    def aadhaar(self) -> str:
        while True:
            a = str(self.r.randint(2, 9)) + str(self.r.randint(10**10, 10**11 - 1))
            if a not in self.used_aadhaar:
                self.used_aadhaar.add(a)
                return a

    def mobile(self) -> str:
        return str(self.r.choice([6, 7, 8, 9])) + str(self.r.randint(10**8, 10**9 - 1))

    def account(self) -> str:
        return str(self.r.randint(10**10, 10**15 - 1))

    def get(self, pid: int) -> dict:
        return self.people[pid - self.pid0]

    def person(self, hid, unit, sex, age_years, comm, surname, rel, alive=True, died=None, maiden=None):
        r = self.r
        c = COMMUNITIES[comm]
        pool = c["male"] if sex == "M" else c["female"]
        anchor = died if died is not None else TODAY
        birth = anchor - timedelta(days=int(age_years * 365.25 + r.randint(0, 364)))
        middle = -1
        if sex == "M" and c.get("male_middle") and (c.get("male_middle_always") or r.random() < 0.75):
            middle = r.randrange(len(c["male_middle"]))
        taken = self.hh_names.setdefault((hid, sex), set())
        first = r.randrange(len(pool))
        for _ in range(20):                                             # families do not reuse a name
            if pool[first][0] not in taken:
                break
            first = r.randrange(len(pool))
        taken.add(pool[first][0])
        p = dict(pid=self.pid0 + len(self.people), hid=hid, unit_id=unit, sex=sex, birth=birth, alive=alive,
                 died=died, comm=comm, first=first, middle=middle, surname=surname, maiden=maiden,
                 second=r.randrange(len(c["female_second"])) if sex == "F" and c.get("female_second") else -1,
                 rel=rel, married=False, widowed=False, spouse=-1, father=-1, disability=0, aadhaar=None,
                 account=None, mobile=None, treasury_pension=0, defence_pension=False, landholder=False, schemes=[])
        age_now = age_on(birth) if alive else age_years
        if r.random() < (0.93 if age_now >= 75 else 0.985):
            p["aadhaar"] = self.aadhaar()
        if age_now >= 18 and r.random() < 0.82:
            p["account"] = self.account()
        prev = 0.018 if age_now < 40 else 0.04 if age_now < 60 else 0.10      # disability rises steeply with age
        if r.random() < prev:
            p["disability"] = int(min(100, max(20, self.np.normal(58, 20))))
        self.people.append(p)
        return p

    def surname(self, comm):
        return (comm, self.r.randrange(len(COMMUNITIES[comm]["surnames"])))

    def couple(self, hid, unit, comm, age_h, age_w, h_alive=True, w_alive=True, h_died=None, w_died=None):
        surname = self.surname(comm)
        h = self.person(hid, unit, "M", age_h, comm, surname, "head", alive=h_alive, died=h_died)
        w = self.person(hid, unit, "F", age_w, comm, surname, "wife", alive=w_alive, died=w_died,
                        maiden=self.surname(comm))
        h["married"] = w["married"] = True
        h["spouse"], w["spouse"] = w["pid"], h["pid"]
        if not h_alive:
            w["widowed"], w["rel"] = True, "head"
        if not w_alive:
            h["widowed"] = True
        return h, w

    def children(self, hid, unit, comm, surname, father, mother_age, n, rel=("son", "daughter")):
        for _ in range(n):
            sex = "M" if self.r.random() < 0.5 else "F"
            c = self.person(hid, unit, sex, self.r.randint(0, max(0, int(mother_age) - 19)), comm, surname,
                            rel[0] if sex == "M" else rel[1])
            c["father"] = father["pid"]

    def died_ago(self, years):
        return TODAY - timedelta(days=int(years * 365))

    def household(self, unit, comm):
        r, cfg = self.r, self.cfg
        hid = self.next_hid
        self.next_hid += 1
        start = len(self.people)
        kinds, weights = zip(*cfg["households"].items())
        kind = r.choices(kinds, weights)[0]
        if kind == "alone":
            age = r.randint(62, 94)
            ago = r.uniform(0.2, 14)
            if r.random() < 0.72:
                self.couple(hid, unit, comm, age + r.randint(1, 8), age, h_alive=False, h_died=self.died_ago(ago))
            else:
                self.couple(hid, unit, comm, age, age - r.randint(1, 7), w_alive=False, w_died=self.died_ago(ago))
        elif kind == "elder_couple":
            age = r.randint(60, 90)
            self.couple(hid, unit, comm, age, age - r.randint(1, 8))
        elif kind == "nuclear":
            ah = r.randint(24, 59)
            aw = max(19, ah - r.randint(1, 7))
            widow = r.random() < 0.05
            h, w = self.couple(hid, unit, comm, ah, aw, h_alive=not widow,
                               h_died=self.died_ago(r.uniform(0.2, 9)) if widow else None)
            self.children(hid, unit, comm, h["surname"], h, aw, r.choice(cfg["kids"]))
        else:
            ag = r.randint(58, 92)
            gw_age = ag - r.randint(1, 8)
            g = r.random()
            if g < 0.36:
                gh, gw = self.couple(hid, unit, comm, ag, gw_age, h_alive=False, h_died=self.died_ago(r.uniform(0.2, 12)))
            elif g < 0.46:
                gh, gw = self.couple(hid, unit, comm, ag, gw_age, w_alive=False, w_died=self.died_ago(r.uniform(0.2, 12)))
            else:
                gh, gw = self.couple(hid, unit, comm, ag, gw_age)
            gh["rel"], gw["rel"] = "father", "mother"
            sa = max(20, min(gw_age - 18, r.randint(24, 50)))
            son = self.person(hid, unit, "M", sa, comm, gh["surname"], "head")
            son["father"] = gh["pid"]
            dil = self.person(hid, unit, "F", max(19, sa - r.randint(1, 6)), comm, gh["surname"], "daughter_in_law",
                              maiden=self.surname(comm))
            son["married"] = dil["married"] = True
            son["spouse"], dil["spouse"] = dil["pid"], son["pid"]
            self.children(hid, unit, comm, son["surname"], son, age_on(dil["birth"]), r.choice(cfg["kids"][:-2]),
                          rel=("grandson", "granddaughter"))
        members = self.people[start:]
        cat = COMMUNITIES[comm]["category"]
        bpl_rate = cfg["bpl"].get(comm, cfg["bpl"].get(cat, cfg["bpl"]["default"]))
        bpl = r.random() < bpl_rate
        income = 0 if bpl else int(np.exp(self.np.normal(8.35, 0.75)))    # median ~Rs 4,200 a month above BPL
        phone = self.mobile()
        for m in members:
            own = m["alive"] and age_on(m["birth"]) >= 16 and r.random() < 0.55
            m["mobile"] = self.mobile() if own else phone                # else the family phone, often a son's
        for m in members:                                                # retired state employees / ex-servicemen
            if m["alive"] and m["sex"] == "M" and age_on(m["birth"]) >= 60 and r.random() < 0.09:
                if r.random() < 0.6:
                    m["treasury_pension"] = max(9000, int(self.np.normal(21000, 7000)))
                else:
                    m["defence_pension"] = True
                income += 20000
        land = round(max(0.02, self.np.gamma(1.2, 0.35 if cfg["code"] == "ALM" else 0.9)), 2) if r.random() < 0.6 else 0.0
        self.households[hid] = dict(hid=hid, unit_id=unit, comm=comm, bpl=bpl, income=income, phone=phone,
                                    landholding=land, members=[m["pid"] for m in members])
        if land:
            holders = [m for m in members if m["alive"] and m["rel"] in ("head", "father") and m["sex"] == "M"] or \
                      [m for m in members if m["alive"] and m["rel"] in ("head", "mother")]
            if holders:
                holders[0]["landholder"] = True
        return members


def eligible(p, hh) -> set:
    """True eligibility under the rules on ssp.uk.gov.in (FAQ and amounts page, read 25 Sep 2026)."""
    out = set()
    if not p["alive"] or hh is None:
        return out
    poor = hh["bpl"] or hh["income"] <= POOR_INCOME
    a = age_on(p["birth"])
    if a >= 60 and poor and not p["treasury_pension"] and not p["defence_pension"]:
        out.add("old_age")
    if p["sex"] == "F" and p["widowed"] and 18 <= a < 60 and poor:
        out.add("widow")
    if p["disability"] >= 40 and poor:
        out.add("disability")
    return out


# ---------------------------------------------------------------------------------------------------------------
# enrolment, calibrated per panchayat to the live portal counts
# ---------------------------------------------------------------------------------------------------------------
def enrol(units: pd.DataFrame, w: World) -> list[tuple]:
    r = w.r
    by_unit = defaultdict(list)
    for p in w.people:
        if p["alive"] and p["hid"] >= 0:
            by_unit[p["unit_id"]].append(p)
    hh_size = {h: len(v["members"]) for h, v in w.households.items()}
    fit = []
    for u in units.itertuples():
        pool = by_unit.get(u.unit_id, [])
        taken = set()
        for scheme, count in (("widow", u.widow), ("disability", u.disability), ("old_age", u.old_age)):
            el = [p for p in pool if scheme in eligible(p, w.households[p["hid"]]) and p["pid"] not in taken]
            if scheme == "widow":
                # widows keep the widow pension after 60 in practice: the portal pays far more widows than there are
                # poor widows aged 18-60, so poor widows over 60 make up the rest of the roll
                el += [p for p in pool if p["sex"] == "F" and p["widowed"] and age_on(p["birth"]) >= 60
                       and "old_age" in eligible(p, w.households[p["hid"]]) and p["pid"] not in taken]
            # who is left out is not random: people living alone or without Aadhaar are missed more often
            el.sort(key=lambda p: r.random() + (0.5 if p["aadhaar"] is None else 0) + (0.3 if hh_size[p["hid"]] == 1 else 0))
            n = min(count, len(el))
            for p in el[:n]:
                p["schemes"].append(scheme)
                taken.add(p["pid"])
            short = count - n
            if short > 0:
                # the portal pays more people here than meet every published criterion: fill with people who
                # nearly qualify (usually on income). Real rolls contain such cases; they are recorded in the truth
                near = [p for p in pool if p["pid"] not in taken and (
                    (scheme == "old_age" and age_on(p["birth"]) >= 60 and not p["treasury_pension"]) or
                    (scheme == "widow" and p["sex"] == "F" and p["widowed"]) or
                    (scheme == "disability" and p["disability"] >= 40))]
                r.shuffle(near)
                for p in near[:short]:
                    p["schemes"].append(scheme)
                    p["enrolled_ineligible"] = scheme
                    taken.add(p["pid"])
                short -= min(short, len(near))
            fit.append((u.unit_id, scheme, int(count), int(count - short)))
    return fit


# ---------------------------------------------------------------------------------------------------------------
# records: how each department writes a person down
# ---------------------------------------------------------------------------------------------------------------
class Writer:
    def __init__(self, w: World):
        self.w, self.r = w, w.r

    def roman(self, variants):
        return variants[0] if self.r.random() < 0.62 or len(variants) == 1 else self.r.choice(variants[1:])

    def typo(self, s):
        if len(s) < 4:
            return s
        i = self.r.randrange(1, len(s) - 1)
        op = self.r.random()
        if op < 0.4:
            return s[:i] + s[i + 1:]
        if op < 0.7:
            return s[:i] + s[i] + s[i:]
        return s[:i - 1] + s[i] + s[i - 1] + s[i + 1:]

    def name(self, p, script, *, drop_middle=0.3, drop_suffix=0.4, drop_surname=0.08, initials=0.0, typo=0.03,
             maiden=False):
        """A person's name as one department writes it. Conventions follow the person's community."""
        r = self.r
        c = COMMUNITIES[p["comm"]]
        pick = (lambda pair: pair[0]) if script == "dev" else (lambda pair: self.roman(pair[1]))
        first = (c["male"] if p["sex"] == "M" else c["female"])[p["first"]]
        sc, si = p["maiden"] if (maiden and p.get("maiden")) else p["surname"]
        sur = COMMUNITIES[sc]["surnames"][si]
        parts = []
        if p["sex"] == "M" and c.get("male_prefix") and r.random() < 0.6:
            parts.append(pick(c["male_prefix"]))                        # Mohd / Md / मोहम्मद
        fn = pick(first)
        if script == "rom" and p["sex"] == "M" and r.random() < initials:
            fn = " ".join(t[0] for t in fn.split())
        parts.append(fn)
        if p["middle"] >= 0 and (c.get("male_middle_always") or r.random() >= drop_middle):
            parts.append(pick(c["male_middle"][p["middle"]]))
        if p["sex"] == "F":
            if p["second"] >= 0:
                parts.append(pick(c["female_second"][p["second"]]))     # Khatoon / Begum / Parveen
            elif c.get("female_suffix") and (c.get("female_suffix_always") or (p["married"] and r.random() >= drop_suffix)):
                parts.append(pick(c["female_suffix"]))                  # Devi / Kaur / Rani
        surname_drop = drop_surname + (0.35 if p["comm"] == "sikh" else 0) + (0.3 if p["second"] >= 0 else 0)
        if r.random() >= surname_drop:
            parts.append(pick(sur))
        out = " ".join(parts)
        if r.random() < typo:
            out = self.typo(out)
        return out.upper() if script == "rom" and r.random() < 0.5 else out

    def relation_name(self, p, script, prefer_father=0.0):
        """Father's name for men and unmarried women; husband's for married women, unless the form asks for father."""
        rel = None
        if p["sex"] == "F" and p["spouse"] >= 0 and self.r.random() >= prefer_father:
            rel = self.w.get(p["spouse"])
        elif p["father"] >= 0:
            rel = self.w.get(p["father"])
        return self.name(rel, script, drop_suffix=1.0, drop_surname=0.35) if rel else None

    def dob(self, p, heap_old=0.45, heap_young=0.12, swap=0.02):
        b = p["birth"]
        a = age_on(b) if p["alive"] else 70
        if self.r.random() < (heap_old if a >= 50 else heap_young):
            return date(b.year + self.r.choice([0, 0, 0, -1, 1, -2, 2]), 1, 1)    # "01-01-YYYY": an estimate
        if self.r.random() < swap and b.day <= 12:
            return date(b.year, b.day, b.month)
        return b

    def age(self, p, at_year):
        """Age as written by a department with no birth date: often rounded to a multiple of five."""
        a = at_year - p["birth"].year
        if a >= 40 and self.r.random() < 0.35:
            return int(round(a / 5.0) * 5)
        if self.r.random() < 0.12:
            return max(0, a + self.r.choice([-3, -2, 2, 3, 5]))
        return a

    def aadhaar(self, p, seeded):
        a = p["aadhaar"]
        if a is None or self.r.random() >= seeded:
            return None
        if self.r.random() < 0.006:                                     # two digits transposed at data entry
            i = self.r.randrange(0, 11)
            a = a[:i] + a[i + 1] + a[i] + a[i + 2:]
        return a

    def place(self, name):
        """Panchayat names are re-typed by every department: vowels doubled, h dropped, case changed."""
        if not isinstance(name, str) or self.r.random() >= 0.22:
            return name
        s = name.title()
        op = self.r.random()
        if op < 0.3:
            return s.replace("aa", "a").replace("ee", "i") if ("aa" in s.lower() or "ee" in s.lower()) else s + "a"
        if op < 0.6:
            return s.replace("h", "", 1) if "h" in s[1:] else s
        if op < 0.8:
            return s.replace("i", "ee", 1)
        return s.upper()


def fmt(d):
    return d.strftime("%d-%m-%Y") if d else None


def build_registers(units: pd.DataFrame, w: World, district: str, code: str, tag: str):
    r, wr = w.r, Writer(w)
    people = w.people
    U = {u.unit_id: u for u in units.itertuples()}
    truth: list[tuple] = []
    regs: dict[str, list] = defaultdict(list)

    def add(reg, rec, pid, plant=None):
        rec["record_id"] = f"{reg}:{tag}:{len(regs[reg])}"
        regs[reg].append(rec)
        truth.append((rec["record_id"], reg, pid, plant))

    # --- Social Welfare pension roll (eSPAN). Hindi names, birth dates, Aadhaar seeding in progress --------------
    pensioners = [p for p in people if p["schemes"]]
    roll = sum(len(p["schemes"]) for p in pensioners)

    def pension_record(p, scheme, account=None, dob=None, name=None, aadhaar="auto"):
        u = U[p["unit_id"]]
        claimed = (dob or p["birth"]).year
        yr = r.randint(min(2026, max(2008, claimed + 60)), 2026) if scheme == "old_age" else r.randint(2008, 2026)
        return dict(pension_id=f"{code}/{scheme[:3].upper()}/{yr}/{r.randint(1, 99999):05d}", scheme=SCHEME_HI[scheme],
                    applicant_name=name or wr.name(p, "dev", drop_surname=0.04),
                    father_husband_name=wr.relation_name(p, "dev"), gender={"M": "पुरुष", "F": "महिला"}[p["sex"]],
                    dob=fmt(dob or wr.dob(p)), category=CATEGORY_HI[COMMUNITIES[p["comm"]]["category"]],
                    district=district, block=u.block, gram_panchayat=u.panchayat,
                    bank_account=account or p["account"] or w.account(),
                    aadhaar=wr.aadhaar(p, 0.88) if aadhaar == "auto" else aadhaar,
                    mobile=p["mobile"], sanction_year=yr, status="Active")

    # account rings: unrelated pensioners whose payments were redirected into one account
    ring_of: dict[int, str] = {}
    old_pens = [p for p in pensioners if p["schemes"] == ["old_age"]]
    rural_blocks = sorted({U[p["unit_id"]].block for p in old_pens if U[p["unit_id"]].area == "Rural"})
    for _ in range(max(1, round(PLANT["ring_share"] * roll / 9)) if rural_blocks else 0):
        acct, blk = w.account(), r.choice(rural_blocks)
        members = [p for p in old_pens if U[p["unit_id"]].block == blk and p["pid"] not in ring_of]
        for p in r.sample(members, min(len(members), r.randint(6, 12))):
            ring_of[p["pid"]] = acct
    for p in pensioners:
        for s in p["schemes"]:
            if p["pid"] in ring_of:
                add("pension", pension_record(p, s, account=ring_of[p["pid"]]), p["pid"], "account_ring")
            else:
                add("pension", pension_record(p, s), p["pid"], "enrolled_ineligible" if p.get("enrolled_ineligible") == s else None)

    n = lambda share: int(round(share * roll))
    dead_old = [p for p in people if not p["alive"] and p["died"] and (TODAY - p["died"]).days < 3 * 365
                and age_on(p["birth"], p["died"]) >= 62 and p["hid"] >= 0]
    for p in r.sample(dead_old, min(len(dead_old), n(PLANT["died_still_paid"]))):
        scheme = "widow" if p["sex"] == "F" and p["widowed"] and r.random() < 0.4 else "old_age"
        add("pension", pension_record(p, scheme), p["pid"], "died_still_paid")
    for p in r.sample(pensioners, min(len(pensioners), n(PLANT["duplicate_same_scheme"]))):
        add("pension", pension_record(p, p["schemes"][0], account=w.account(),
                                      name=wr.name(p, "dev", drop_middle=0.8, typo=0.5), aadhaar=None),
            p["pid"], "duplicate_same_scheme")
    widows_old = [p for p in pensioners if p["schemes"] == ["old_age"] and p["sex"] == "F" and p["widowed"]]
    for p in r.sample(widows_old, min(len(widows_old), n(PLANT["two_pensions"]))):
        add("pension", pension_record(p, "widow"), p["pid"], "two_pensions")
    retirees = [p for p in people if p["alive"] and p["treasury_pension"] > POOR_INCOME and not p["schemes"]]
    for p in r.sample(retirees, min(len(retirees), n(PLANT["treasury_income"]))):
        add("pension", pension_record(p, "old_age"), p["pid"], "treasury_income")
    young = [p for p in people if p["alive"] and 52 <= age_on(p["birth"]) <= 58 and not p["schemes"] and p["hid"] >= 0]
    for p in r.sample(young, min(len(young), n(PLANT["age_inflated"]))):
        add("pension", pension_record(p, "old_age", dob=date(p["birth"].year - r.randint(5, 9), 1, 1)), p["pid"], "age_inflated")
    comms, cw = zip(*DISTRICT_COMMUNITIES[district].items())
    unit_ids = list(U)
    for _ in range(n(PLANT["ghost"])):
        comm = r.choices(comms, cw)[0]
        sex = r.choice("MF")
        g = w.person(-1, r.choice(unit_ids), sex, r.randint(62, 85), comm, w.surname(comm), "head")
        g["married"], g["ghost"] = sex == "F", True
        add("pension", pension_record(g, "old_age" if sex == "M" else r.choice(["old_age", "widow"])), g["pid"], "ghost")

    # --- Parivar (family) register, Panchayati Raj. Hindi, rural, deaths often not struck off ------------------
    for hid, hh in w.households.items():
        if U[hh["unit_id"]].area != "Rural" or r.random() > 0.94:
            continue
        u = U[hh["unit_id"]]
        fam = f"PR/{code}/{hh['unit_id']:04d}/{hid:07d}"
        for pid in hh["members"]:
            p = w.get(pid)
            if not p["alive"] and (TODAY - p["died"]).days > 6 * 365:
                continue
            struck = (not p["alive"]) and r.random() < 0.45
            add("parivar", dict(family_id=fam, member_name=wr.name(p, "dev", drop_middle=0.5),
                                relation=REL_HI.get(p["rel"], "सदस्य"), gender={"M": "पु", "F": "म"}[p["sex"]],
                                dob=fmt(wr.dob(p, heap_old=0.55, heap_young=0.25)),
                                father_husband_name=wr.relation_name(p, "dev", prefer_father=0.2),
                                gram_panchayat=u.panchayat, block=u.block, remark="मृत" if struck else None,
                                aadhaar=wr.aadhaar(p, 0.40)), pid)

    # --- Ration cards, Food & Civil Supplies. English, ages not birth dates, senior woman as head ---------------
    for hid, hh in w.households.items():
        if r.random() > 0.88:
            continue
        u = U[hh["unit_id"]]
        upd = r.randint(2019, 2025)
        members = [w.get(pid) for pid in hh["members"]]
        alive_then = [p for p in members if p["alive"] or (p["died"] and p["died"].year >= upd)]
        if not alive_then:
            continue
        ctype = ("AAY" if r.random() < 0.13 else "PHH") if hh["bpl"] else ("SFY" if hh["income"] < 15000 else "NPHH")
        women = [p for p in alive_then if p["sex"] == "F" and age_on(p["birth"]) >= 18]
        head = min(women, key=lambda p: p["birth"]) if women else alive_then[0]
        card, head_name = str(r.randint(10**11, 10**12 - 1)), wr.name(head, "rom")
        for p in alive_then:
            if not p["alive"] and r.random() >= 0.5:                    # half of deaths never reach the card
                continue
            add("ration", dict(card_no=card, card_type=ctype, head_of_family=head_name,
                               member_name=wr.name(p, "rom", drop_middle=0.45), member_age=wr.age(p, upd),
                               age_as_on=upd, gender=p["sex"],
                               relation_to_head="SELF" if p is head else REL_EN.get(p["rel"], "OTHER"),
                               aadhaar=wr.aadhaar(p, 0.93), mobile=hh["phone"], village=wr.place(u.panchayat),
                               block=u.block, district=district), p["pid"])

    # --- MGNREGA job cards, Rural Development. English, age at registration -------------------------------------
    for hid, hh in w.households.items():
        u = U[hh["unit_id"]]
        if u.area != "Rural" or r.random() > 0.66:
            continue
        reg = r.randint(2008, 2023)
        members = [w.get(pid) for pid in hh["members"]]
        head = next((p for p in members if p["rel"] == "head" and p["alive"]), members[0])
        jc = f"UK-{code}-{u.block[:3].upper()}-{r.randint(1, 999):03d}/{hid % 1000}"
        head_name = wr.name(head, "rom")
        for p in members:
            if reg - p["birth"].year < 18 or not p["alive"] or r.random() > 0.8:
                continue
            add("mgnrega", dict(job_card_no=jc, head_name=head_name, worker_name=wr.name(p, "rom"),
                                father_husband_name=wr.relation_name(p, "rom"), gender=p["sex"], age=wr.age(p, reg),
                                registered=reg, caste={"sc": "SC", "st": "ST"}.get(COMMUNITIES[p["comm"]]["category"], "OTH"),
                                account=p["account"], aadhaar=wr.aadhaar(p, 0.85), village=wr.place(u.panchayat),
                                block=u.block, active=r.random() < 0.55), p["pid"])

    for p in people:
        if p.get("ghost"):
            continue
        u = U[p["unit_id"]]
        # --- PM-KISAN, Agriculture. Name as in the land record; Aadhaar-seeded by design ----------------------
        if p["landholder"] and p["alive"] and r.random() < 0.85:
            add("kisan", dict(registration_no=f"UK{r.randint(10**9, 10**10 - 1)}",
                              farmer_name=wr.name(p, "rom", drop_middle=0.2, initials=0.08),
                              father_husband_name=wr.relation_name(p, "rom", prefer_father=0.5), gender=p["sex"],
                              dob=fmt(wr.dob(p, heap_old=0.5)) if r.random() < 0.5 else None,
                              aadhaar=wr.aadhaar(p, 0.99), account=p["account"] or w.account(),
                              land_ha=w.households[p["hid"]]["landholding"], village=wr.place(u.panchayat),
                              block=u.block), p["pid"])
        # --- Death register (Civil Registration System). Hindi or English, age at death, rarely Aadhaar ------
        if not p["alive"] and (TODAY - p["died"]).days <= 6 * 365 and r.random() < 0.92:
            script = "dev" if r.random() < 0.6 else "rom"
            add("death", dict(registration_no=f"D-{p['died'].year}-{r.randint(1, 99999):05d}",
                              deceased_name=wr.name(p, script), gender=p["sex"], age_at_death=wr.age(p, p["died"].year),
                              date_of_death=fmt(p["died"]), father_husband_name=wr.relation_name(p, script),
                              village=wr.place(u.panchayat), block=u.block, aadhaar=wr.aadhaar(p, 0.35)), p["pid"])
        # --- UDID disability register. English, birth dates, certified percentage ---------------------------
        if p["alive"] and p["disability"] >= 20 and r.random() < 0.65:
            add("udid", dict(udid_no=f"UK{r.randint(10**15, 10**16 - 1)}", name=wr.name(p, "rom", maiden=r.random() < 0.3),
                             father_guardian_name=wr.relation_name(p, "rom", prefer_father=0.4), gender=p["sex"],
                             dob=fmt(wr.dob(p, heap_old=0.2, heap_young=0.05)),
                             disability_type=r.choice(["Locomotor", "Low Vision", "Blindness", "Hearing Impairment",
                                                       "Intellectual Disability", "Multiple Disabilities"]),
                             percentage=p["disability"], aadhaar=wr.aadhaar(p, 0.85), mobile=p["mobile"],
                             block=u.block, village=wr.place(u.panchayat)), p["pid"])
        # --- Treasury pension roll, Finance. Retired state employees; exact birth dates ----------------------
        if p["alive"] and p["treasury_pension"]:
            add("treasury", dict(ppo_no=f"UK/{code}/{r.randint(10**5, 10**6 - 1)}",
                                 pensioner_name=wr.name(p, "rom", drop_middle=0.1), dob=fmt(p["birth"]), gender=p["sex"],
                                 monthly_pension=p["treasury_pension"], treasury=district,
                                 account=p["account"] or w.account(), aadhaar=wr.aadhaar(p, 0.97)), p["pid"])

    # --- PMAY-G housing, Rural Development. Household heads sanctioned a house ------------------------------------
    for hid, hh in w.households.items():
        u = U[hh["unit_id"]]
        if u.area != "Rural" or not hh["bpl"] or r.random() > 0.12:
            continue
        head = next((w.get(pid) for pid in hh["members"] if w.get(pid)["alive"] and w.get(pid)["rel"] in ("head", "father", "mother")), None)
        if head:
            add("pmay", dict(beneficiary_id=f"UK{r.randint(10**6, 10**7 - 1)}", beneficiary_name=wr.name(head, "rom"),
                             father_husband_name=wr.relation_name(head, "rom"), gender=head["sex"],
                             sanction_year=r.randint(2016, 2025), account=head["account"],
                             aadhaar=wr.aadhaar(head, 0.9), village=wr.place(u.panchayat), block=u.block), head["pid"])
    return regs, truth


def persons_rows(w: World, district: str) -> list[dict]:
    out = []
    for p in w.people:
        hh = w.households.get(p["hid"])
        out.append(dict(pid=p["pid"], hid=p["hid"], district=district, unit_id=p["unit_id"], sex=p["sex"],
                        birth=p["birth"], alive=p["alive"], died=p["died"], community=p["comm"],
                        category=COMMUNITIES[p["comm"]]["category"], married=p["married"], widowed=p["widowed"],
                        spouse=p["spouse"], disability=p["disability"], has_aadhaar=p["aadhaar"] is not None,
                        treasury_pension=p["treasury_pension"], defence_pension=p["defence_pension"],
                        ghost=p.get("ghost", False), schemes=",".join(p["schemes"]),
                        enrolled_ineligible=p.get("enrolled_ineligible"),
                        eligible=",".join(sorted(eligible(p, hh))), bpl=hh["bpl"] if hh else None,
                        income=hh["income"] if hh else None, household_size=len(hh["members"]) if hh else None))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--district", default="Almora")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    cfg = DISTRICTS[a.district]
    out = ROOT / "data" / "gen" / slug(a.district)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    units = load_units(a.district)
    units.to_parquet(out / "units.parquet")
    weight = units[["old_age", "widow", "disability"]].sum(axis=1).astype(float)
    rural = units.area == "Rural"
    pop = cfg["population"] * a.scale
    target = np.where(rural, pop * (1 - cfg["urban_share"]) * weight / weight[rural].sum(),
                      pop * cfg["urban_share"] * weight / max(1.0, weight[~rural].sum()))
    units["target"] = target
    comms, cw = zip(*DISTRICT_COMMUNITIES[a.district].items())

    used_aadhaar: set = set()
    pid, hid = 0, 0
    frames: dict[str, list] = defaultdict(list)
    fit_all, persons = [], []
    for ti, (tehsil, tu) in enumerate(units.groupby("tehsil", sort=True)):
        w = World(a.seed * 1000 + ti, cfg, pid, hid, used_aadhaar)
        for u in tu.itertuples():
            n = 0
            while n < u.target:
                n += sum(1 for m in w.household(int(u.unit_id), w.r.choices(comms, cw)[0]) if m["alive"])
        fit_all += enrol(tu, w)
        regs, truth = build_registers(tu, w, a.district, cfg["code"], f"{cfg['code']}{ti:02d}")
        for k, v in regs.items():
            frames[k].append(pd.DataFrame(v))
        frames["truth_records"].append(pd.DataFrame(truth, columns=["record_id", "register", "pid", "plant"]))
        persons.append(pd.DataFrame(persons_rows(w, a.district)))
        pid, hid = pid + len(w.people), w.next_hid
        print(f"  {tehsil}: {len(w.households):,} households, {sum(p['alive'] for p in w.people):,} living, "
              f"{sum(len(v) for v in regs.values()):,} records  [{time.time() - t0:.0f}s]", flush=True)
        del w, regs, truth

    for k, v in frames.items():
        pd.concat(v, ignore_index=True).to_parquet(out / f"{k}.parquet")
    pers = pd.concat(persons, ignore_index=True)
    pers.to_parquet(out / "persons.parquet")
    fit = pd.DataFrame(fit_all, columns=["unit_id", "scheme", "portal", "enrolled"])
    truth = pd.concat(frames["truth_records"])
    summary = dict(district=a.district, seed=a.seed, scale=a.scale, units=len(units), households=hid,
                   persons_alive=int(pers.alive.sum()), persons_dead=int((~pers.alive).sum()),
                   calibration=dict(portal=int(fit.portal.sum()), enrolled=int(fit.enrolled.sum()),
                                    by_scheme=fit.groupby("scheme")[["portal", "enrolled"]].sum().to_dict("index")),
                   enrolled_ineligible=int(pers.enrolled_ineligible.notna().sum()),
                   records={k: int(sum(len(x) for x in v)) for k, v in frames.items() if k != "truth_records"},
                   planted=truth.plant.value_counts().to_dict(), seconds=round(time.time() - t0))
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str, ensure_ascii=False))
    print(json.dumps(summary, indent=2, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
