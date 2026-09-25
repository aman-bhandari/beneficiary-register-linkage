"""Run every evaluation and write eval/results.json: the numbers the Method page shows and RESULTS.md quotes.
Only figures leave this script; the planted truth never reaches the warehouse.

    python eval/report.py
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import findings_eval
import linkage_eval

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    t = time.time()
    districts = [p.name.replace("_", " ").title() for p in sorted((ROOT / "data" / "gen").iterdir()) if (p / "cases.parquet").exists()]
    out = {"generated": time.strftime("%Y-%m-%d %H:%M"), "linkage": [], "findings": []}
    for d in districts:
        recs, persons = linkage_eval.load(d)
        p1, _ = linkage_eval.load(d, "clusters_pass1.parquet")
        out["linkage"].append(dict(district=d, overall=linkage_eval.evaluate(recs), pass1=linkage_eval.evaluate(p1),
                                   groups=linkage_eval.by_group(recs, persons), register_pairs=linkage_eval.by_register(recs)))
        out["findings"].append(findings_eval.evaluate(d))
    (ROOT / "eval" / "results.json").write_text(json.dumps(out, indent=1, default=str))
    for l, f in zip(out["linkage"], out["findings"]):
        o = l["overall"]
        print(f"{l['district']}: linkage precision {o['precision']:.1%} recall {o['recall']:.1%} "
              f"(first pass {l['pass1']['precision']:.1%} / {l['pass1']['recall']:.1%})")
        for x in f["integrity"]:
            print(f"   {x['type']:22s} planted {x['planted']:5d} found {x['recall']:.1%} right {x['precision']:.1%}")
        for x in f["exclusion"]:
            print(f"   left out {x['scheme']:10s} truly {x['truly_left_out']:6d} raised {x['flagged']:6d} right {x['precision']:.1%} high {x['high_priority_precision']}")
    print(f"written eval/results.json in {time.time() - t:.0f}s")
