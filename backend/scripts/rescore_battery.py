"""Re-score the 50 saved battery resumes after ATS matcher fixes (no LLM calls)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from services.ats_engine import compute_ats_score

OUT = Path(__file__).resolve().parent / "ats_battery_out"


def main():
    rows = []
    for p in sorted(OUT.glob("resume_*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        old = d["ats"]["score"]
        ats = compute_ats_score(json.dumps(d["tailored_resume"]), d["jd"]["text"])
        delta = ats.score - old
        rows.append({
            "id": d["jd"]["id"],
            "role": d["jd"]["role"],
            "old": old,
            "new": ats.score,
            "delta": delta,
            "old_missing": d["ats"]["missing_keywords"],
            "new_missing": ats.missing_keywords,
        })
        print(f"#{d['jd']['id']:02d} {d['jd']['role'][:28]:28} {old:>3} -> {ats.score:>3} ({delta:+d})  miss {len(d['ats']['missing_keywords'])}->{len(ats.missing_keywords)}")

    old_avg = sum(r["old"] for r in rows) / len(rows)
    new_avg = sum(r["new"] for r in rows) / len(rows)
    print("\n=== RE-SCORE SUMMARY ===")
    print(f"n={len(rows)}  old_avg={old_avg:.1f}  new_avg={new_avg:.1f}  lift={new_avg-old_avg:+.1f}")
    print(f"improved={sum(1 for r in rows if r['delta']>0)}  same={sum(1 for r in rows if r['delta']==0)}  worse={sum(1 for r in rows if r['delta']<0)}")
    print(f"new min={min(r['new'] for r in rows)}  new max={max(r['new'] for r in rows)}")
    print("\nStill lowest:")
    for r in sorted(rows, key=lambda x: x["new"])[:8]:
        print(f"  {r['new']} {r['role']} missing={r['new_missing'][:8]}")

    (OUT / "rescore_after_fix.json").write_text(json.dumps({
        "old_avg": round(old_avg, 1),
        "new_avg": round(new_avg, 1),
        "lift": round(new_avg - old_avg, 1),
        "rows": rows,
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
